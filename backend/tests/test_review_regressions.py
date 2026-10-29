"""Regression cases found during the independent review; no external requests."""

import importlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from langchain_core.documents import Document

from src.ingestion.chunking import DocumentChunker, split_markdown_sections
from src.ingestion.loaders import DocumentLoader, markdown_metadata
from tests.conftest import write

graph = importlib.import_module("src.agent.graph")


@pytest.mark.parametrize("rebuild", [False, True])
def test_partial_parse_failure_keeps_both_previous_files(
    make_pipeline, docs_dir, tmp_path, monkeypatch, rebuild
):
    write(docs_dir / "A.md", "# A\n\nOriginal A.")
    write(docs_dir / "B.md", "# B\n\nOriginal B.")
    make_pipeline().run()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and p.parent != docs_dir}
    write(docs_dir / "A.md", "# A\n\nUpdated A.")
    write(docs_dir / "B.md", "# B\n\nUpdated B.")
    original = DocumentLoader.load_file
    monkeypatch.setattr(
        DocumentLoader, "load_file",
        lambda self, path, root=None: [] if path.name == "B.md" else original(self, path, root),
    )
    with pytest.raises(RuntimeError, match="previous index"):
        make_pipeline().run(rebuild=rebuild)
    assert all(p.read_bytes() == data for p, data in before.items())


def test_empty_mount_fails_without_erasing_index(make_pipeline, docs_dir, tmp_path):
    path = write(docs_dir / "A.md", "# A\n\nAlpha.")
    make_pipeline().run()
    manifest_before = (tmp_path / "manifest.json").read_bytes()
    path.unlink()
    with pytest.raises(RuntimeError, match="No supported files"):
        make_pipeline().run()
    assert (tmp_path / "manifest.json").read_bytes() == manifest_before


def test_legacy_random_ids_are_migrated_even_when_counts_match(make_pipeline, docs_dir):
    path = write(docs_dir / "A.md", "# A\n\nAlpha.")
    pipeline = make_pipeline()
    pipeline.run()
    store = pipeline.vectorstore
    docs = list(store._vectorstore.docstore._dict.values())
    for doc in docs:
        doc.metadata.pop("chunk_id", None)
    store.create_from_documents(docs)
    store.save()
    result = make_pipeline().run()
    assert result["files_processed"] == 1
    loaded = make_pipeline().vectorstore
    assert loaded.load()
    assert list(loaded._vectorstore.docstore._dict) == [f"{path.absolute()}#0"]


def test_foreign_platform_manifest_keys_are_removed(make_pipeline, docs_dir, tmp_path):
    write(docs_dir / "A.md", "# A\n\nAlpha.")
    make_pipeline().run()
    file = tmp_path / "manifest.json"
    manifest = json.loads(file.read_text(encoding="utf-8"))
    entry = next(iter(manifest["documents"].values())).copy()
    foreign = "/app/data/docs/A.md" if Path("C:/").is_absolute() else r"D:\docs\A.md"
    entry["filepath"] = foreign
    manifest["documents"] = {foreign: entry}
    file.write_text(json.dumps(manifest), encoding="utf-8")
    make_pipeline().run()
    assert foreign not in json.loads(file.read_text(encoding="utf-8"))["documents"]


def test_skipped_heading_levels_do_not_become_false_parents():
    text = "## Three\n\nA.\n\n### Child\n\nB.\n\n## Two\n\nC.\n"
    assert [p for p, _ in split_markdown_sections(text)] == [
        ["Three"], ["Three", "Child"], ["Two"],
    ]


def test_long_code_fence_cannot_be_closed_by_shorter_fence():
    text = "# Root\n\n````markdown\n```\n# Example only\n```\n````\n\n## Real\n"
    assert [p for p, _ in split_markdown_sections(text)] == [["Root"], ["Root", "Real"]]


def test_metadata_inside_code_is_not_a_page_declaration():
    metadata = markdown_metadata("Guide", "```md\n# Fake title\nAudience: developers.\n"
                                 "- Reported version: `99`\n- Code ownership: fake.\n"
                                 "Review date: 2099-01-01\n```\n# Real title\n\nText.")
    assert metadata["title"] == "Real title"
    assert not {"audience", "plugin_version", "code_ownership", "review_date"} & metadata.keys()


def test_table_continuations_repeat_column_headers():
    text = "# Root\n\n## Values\n\n| Setting | Meaning |\n| --- | --- |\n"
    text += "".join(f"| option{i} | explanation {i} |\n" for i in range(100))
    chunks = DocumentChunker(chunk_size=350, chunk_overlap=30).chunk_document(
        Document(page_content=text, metadata={"file_type": "markdown", "wiki_page": "Guide"})
    )
    tables = [c for c in chunks if "| option" in c.page_content]
    assert len(tables) > 3
    assert all("| Setting | Meaning |\n| --- | --- |" in c.page_content for c in tables)


def test_pdf_legacy_metadata_without_file_type_does_not_invent_url():
    output = graph.format_search_results([
        (Document(page_content="Plans", metadata={"file_name": "Plans.pdf", "page_number": 2}), 0.2),
    ], 5)
    assert '"Plans.pdf", page 2' in output
    assert "wiki/Plans" not in output


def test_bound_tool_has_strict_responses_schema():
    schema = graph.llm.kwargs["tools"][0]["function"]
    assert schema.get("strict") is True
    assert schema["parameters"]["additionalProperties"] is False
    assert set(schema["parameters"]["required"]) == {"query", "scope"}
    assert "default" not in schema["parameters"]["properties"]["scope"]


def test_failed_atomic_replace_keeps_previous_snapshot(make_pipeline, docs_dir, tmp_path, monkeypatch):
    from src.ingestion import vectorstore

    write(docs_dir / "A.md", "# A\n\nOriginal.")
    make_pipeline().run()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and p.parent != docs_dir}
    write(docs_dir / "A.md", "# A\n\nReplacement.")
    original_replace = os.replace

    def fail_commit(source, destination):
        if Path(destination).name in {"index.faiss", "index.snapshot"}:
            raise PermissionError("destination is open without delete sharing")
        return original_replace(source, destination)

    monkeypatch.setattr(vectorstore.os, "replace", fail_commit)
    with pytest.raises(RuntimeError, match="could not be saved"):
        make_pipeline().run()
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not list((tmp_path / "faiss").glob(".saving-*"))
    store = make_pipeline().vectorstore
    assert store.load()
    assert "Original" in next(iter(store._vectorstore.docstore._dict.values())).page_content


@pytest.mark.skipif(os.name != "nt", reason="Windows file sharing semantics")
def test_windows_open_snapshot_prevents_replace_without_damage(make_pipeline, docs_dir):
    write(docs_dir / "A.md", "# A\n\nOriginal.")
    pipeline = make_pipeline()
    pipeline.run()
    before = pipeline.vectorstore.snapshot_file.read_bytes()
    with pipeline.vectorstore.snapshot_file.open("rb"):
        assert not pipeline.vectorstore.save()
    assert pipeline.vectorstore.snapshot_file.read_bytes() == before


def test_legacy_pair_is_read_and_migrated_on_update(make_pipeline, docs_dir):
    write(docs_dir / "A.md", "# A\n\nLegacy content.")
    pipeline = make_pipeline()
    pipeline.run()
    store = pipeline.vectorstore
    store._vectorstore.save_local(str(store.index_path))
    store.snapshot_file.unlink()
    assert make_pipeline().vectorstore.load()
    write(docs_dir / "A.md", "# A\n\nUpdated content.")
    pipeline = make_pipeline()
    pipeline.run()
    assert pipeline.vectorstore.snapshot_file.exists()


def test_manifest_replace_failure_preserves_previous_json(make_pipeline, docs_dir, tmp_path, monkeypatch):
    write(docs_dir / "A.md", "# A\n\nOriginal.")
    make_pipeline().run()
    before = (tmp_path / "manifest.json").read_bytes()
    write(docs_dir / "A.md", "# A\n\nReplacement.")
    original_replace = os.replace

    def fail_manifest(source, destination):
        if Path(destination).name == "manifest.json":
            raise PermissionError("manifest is locked")
        return original_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_manifest)
    with pytest.raises(RuntimeError, match="Manifest could not be saved"):
        make_pipeline().run()
    assert (tmp_path / "manifest.json").read_bytes() == before
    assert not list(tmp_path.glob("manifest.json.*.tmp"))


def test_uppercase_extensions_are_discovered(make_pipeline, docs_dir):
    write(docs_dir / "A.MD", "# A\n\nCase-insensitive extension.")
    assert make_pipeline().run()["files_processed"] == 1


def test_zero_overlap_is_respected():
    assert DocumentChunker(chunk_size=100, chunk_overlap=0).splitter._chunk_overlap == 0


def test_unknown_legacy_source_does_not_invent_url():
    assert "https://" not in graph._citation({})


def test_identical_legacy_content_keeps_each_real_citation():
    result = graph.format_search_results([
        (Document(page_content="same", metadata={"file_name": "A.md"}), 0.1),
        (Document(page_content="same", metadata={"file_name": "B.md"}), 0.1),
    ], 5)
    assert "wiki/A" in result and "wiki/B" in result


def test_embedding_failure_keeps_disk_state(make_pipeline, docs_dir, tmp_path, monkeypatch, embeddings):
    write(docs_dir / "A.md", "# A\n\nOriginal.")
    make_pipeline().run()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and p.parent != docs_dir}
    write(docs_dir / "A.md", "# A\n\nReplacement.")

    def failed_embedding(_texts):
        raise RuntimeError("simulated embedding failure")

    monkeypatch.setattr(embeddings, "embed_documents", failed_embedding)
    with pytest.raises(RuntimeError, match="embedding failure"):
        make_pipeline().run(rebuild=True)
    assert all(p.read_bytes() == data for p, data in before.items())


def test_snapshot_rejects_inconsistent_mapping(make_pipeline, docs_dir):
    write(docs_dir / "A.md", "# A\n\nAlpha.")
    pipeline = make_pipeline()
    pipeline.run()
    pipeline.vectorstore._vectorstore.index_to_docstore_id[0] = "missing-doc"
    assert pipeline.vectorstore.save()
    assert not make_pipeline().vectorstore.load()


@pytest.mark.skipif(os.name != "nt", reason="Windows ingestion wrappers")
@pytest.mark.parametrize("script", ["ingest.bat", "ingest.ps1"])
def test_windows_wrappers_report_command_failure(tmp_path, script):
    # where.exe rejects the Docker arguments. No Docker daemon or services are used.
    system32 = Path(os.environ["SYSTEMROOT"]) / "System32"
    shutil.copyfile(system32 / "where.exe", tmp_path / "docker.exe")
    root = Path(__file__).parents[2]
    command = ([str(system32 / "cmd.exe"), "/d", "/c", str(root / script)]
               if script.endswith(".bat") else
               [str(system32 / "WindowsPowerShell/v1.0/powershell.exe"), "-NoProfile",
                "-ExecutionPolicy", "Bypass", "-File", str(root / script)])
    env = {**os.environ, "PATH": str(tmp_path)}
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True)
    assert result.returncode != 0
    assert b"Ingestion failed" in result.stdout
    assert b"Done!" not in result.stdout

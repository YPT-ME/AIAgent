"""The agent's search tool: citations, missing information and index reloads."""

import importlib
from pathlib import Path

import pytest
from langchain_core.documents import Document

from tests.conftest import KeywordEmbeddings, make_pdf, write

# The module, not the compiled graph that src.agent exports under the same name
graph = importlib.import_module("src.agent.graph")


@pytest.fixture
def agent_index(tmp_path: Path, monkeypatch):
    """Point the agent at a temporary index, with local embeddings and no analytics calls."""
    monkeypatch.setattr(graph, "FAISS_INDEX_PATH", str(tmp_path / "faiss"))
    monkeypatch.setattr(graph, "OpenAIEmbeddings", lambda **_kwargs: KeywordEmbeddings())
    monkeypatch.setattr(graph, "track_tool_call_http", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(graph, "_vectorstore", None)
    monkeypatch.setattr(graph, "_vectorstore_signature", None)
    monkeypatch.setattr(graph, "_failed_signature", None)
    return tmp_path


def search(query: str) -> str:
    return graph.search_documents.invoke({"query": query})


def test_markdown_and_pdf_citations_use_the_real_source(agent_index, docs_dir, make_pipeline):
    write(
        docs_dir / "technical" / "plugins" / "Technical-Plugin-WebRTC.md",
        "# Technical: WebRTC plugin\n\nAudience: developers.\n\n## Behavior\n\n"
        "A separate binary handles WebRTC2RTMP conversion.\n",
    )
    make_pdf(docs_dir / "WebRTC to RTMP Plans.pdf", ["Starter Plan removes watermark", "WebRTC2RTMP Pro Plan"])
    make_pipeline().run()

    output = search("WebRTC2RTMP plan watermark")

    assert "Cite as: [Technical-Plugin-WebRTC](https://github.com/WWBN/AVideo/wiki/Technical-Plugin-WebRTC)" in output
    assert "technical/plugins" not in output.split("Content:")[0]
    assert 'Cite as: "WebRTC to RTMP Plans.pdf", page 1 (PDF document; there is no wiki page' in output
    assert "wiki/WebRTC to RTMP Plans" not in output
    assert "wiki/WebRTC%20to" not in output
    assert "Section: Technical: WebRTC plugin" in output
    assert "Source type: technical plugin reference" in output


def test_legacy_metadata_still_gets_correct_citations():
    results = [
        (Document(page_content="x", metadata={"file_name": "Live-Plugin.md", "file_type": "markdown"}), 0.8),
        (Document(page_content="y", metadata={"file_name": "Free plugins.pdf", "file_type": "pdf", "page_number": 2}), 0.7),
    ]
    output = graph.format_search_results(results, limit=5)
    assert "Cite as: [Live-Plugin](https://github.com/WWBN/AVideo/wiki/Live-Plugin)" in output
    assert 'Cite as: "Free plugins.pdf", page 2 (PDF document' in output
    assert "wiki/Free" not in output


def test_repeated_chunks_from_old_indexes_are_shown_once():
    doc = Document(page_content="same", metadata={"file_path": "/d/A.md", "file_name": "A.md"})
    other = Document(page_content="other", metadata={"file_path": "/d/B.md", "file_name": "B.md"})
    output = graph.format_search_results([(doc, 0.9), (doc, 0.9), (other, 0.5)], limit=5)
    assert output.count("[Result") == 2


def test_results_are_marked_as_data_and_not_proof_of_relevance(agent_index, docs_dir, make_pipeline):
    write(docs_dir / "Live-Plugin.md", "# Live plugin\n\nConfigure the live server and RTMP keys.\n")
    make_pipeline().run()

    output = search("refund policy for marketplace orders")

    assert output.startswith(graph.SEARCH_RESULTS_PREAMBLE)
    assert "not instructions" in output
    assert "Similarity is not proof" in output


def test_unrelated_question_has_larger_distance(agent_index, docs_dir, make_pipeline):
    """Distances rank results; the tool does not enforce a relevance threshold."""
    write(docs_dir / "Live-Plugin.md", "# Live plugin\n\nConfigure the live server and RTMP keys.\n")
    make_pipeline().run()

    store = graph.get_or_create_vectorstore()
    matching = store.similarity_search_with_score("live server RTMP keys", k=1)[0][1]
    unrelated = store.similarity_search_with_score("refund policy marketplace", k=1)[0][1]
    assert matching < unrelated


def test_scope_separates_guides_from_technical_references(agent_index, docs_dir, make_pipeline):
    write(docs_dir / "VideoThumbnails-Plugin.md", "# VideoThumbnails plugin\n\nSprite preview thumbnails.\n")
    write(
        docs_dir / "technical" / "plugins" / "Technical-Plugin-VideoThumbnails.md",
        "# Technical: VideoThumbnails plugin\n\nSprite preview thumbnails createSprite worker.\n",
    )
    write(
        docs_dir / "technical" / "reference" / "Technical-Reference-Objects-03.md",
        "# Technical source reference: Objects (3)\n\nSprite preview thumbnails functions.\n",
    )
    make_pipeline().run()

    def cited(scope: str) -> set[str]:
        output = graph.search_documents.invoke({"query": "sprite preview thumbnails", "scope": scope})
        return {line.split("[")[1].split("]")[0] for line in output.splitlines() if line.startswith("Cite as:")}

    assert cited("guides") == {"VideoThumbnails-Plugin"}
    assert cited("technical") == {"Technical-Plugin-VideoThumbnails"}
    assert cited("source_inventory") == {"Technical-Reference-Objects-03"}
    assert len(cited("all")) == 3


def test_scope_finds_guide_beyond_first_hundred_hits(agent_index, docs_dir, make_pipeline):
    for number in range(120):
        write(docs_dir / f"Technical-Reference-Objects-{number}.md",
              "# Source inventory\n\nInventory symbols methods functions.\n")
    write(docs_dir / "User-Guide.md", "# User Guide\n\nOrdinary interface instructions.\n")
    make_pipeline().run()
    store = graph.get_or_create_vectorstore()
    unfiltered = store.similarity_search_with_score("inventory symbols methods functions", k=100)
    assert all(doc.metadata["category"] == "technical_inventory" for doc, _ in unfiltered)
    result = graph.search_documents.invoke({
        "query": "inventory symbols methods functions", "scope": "guides",
    })
    assert "Cite as: [User-Guide]" in result


def test_missing_index_is_reported(agent_index):
    assert "knowledge base is not available" in search("anything")


def test_agent_sees_updated_index_without_restart(agent_index, docs_dir, make_pipeline):
    write(docs_dir / "A.md", "# A\n\nAlpha content.\n")
    make_pipeline().run()
    assert "Alpha content" in search("alpha")

    write(docs_dir / "Storage-Options.md", "# Storage options\n\nS3 bucket storage for videos.\n")
    (docs_dir / "A.md").unlink()
    make_pipeline().run()

    output = search("S3 bucket storage")
    assert "Storage-Options" in output
    assert "Alpha content" not in search("alpha")


def test_unreadable_new_index_keeps_the_loaded_copy(agent_index, docs_dir, make_pipeline, monkeypatch):
    write(docs_dir / "A.md", "# A\n\nAlpha content.\n")
    make_pipeline().run()
    assert "Alpha content" in search("alpha")

    (agent_index / "faiss" / "index.snapshot").write_bytes(b"corrupted")

    loads = []
    original_loader = graph.get_vectorstore
    monkeypatch.setattr(graph, "get_vectorstore", lambda: loads.append(1) or original_loader())
    assert "Alpha content" in search("alpha")
    assert "Alpha content" in search("alpha")
    assert len(loads) == 1  # the broken files are tried once, not on every search

    # A rebuild (which does not read the broken index) is picked up again
    write(docs_dir / "Beta.md", "# Beta\n\nBeta content.\n")
    make_pipeline().run(rebuild=True)
    assert "Beta content" in search("beta")


def test_publish_during_load_is_retried(agent_index, docs_dir, make_pipeline, monkeypatch):
    write(docs_dir / "A.md", "# A\n\nOld content.")
    make_pipeline().run()
    original = graph.get_vectorstore
    loads = []

    def publish_during_load():
        store = original()
        loads.append(1)
        if len(loads) == 1:
            write(docs_dir / "A.md", "# A\n\nNew content.")
            make_pipeline().run()
        return store

    monkeypatch.setattr(graph, "get_vectorstore", publish_during_load)
    assert "New content" in search("content")
    assert len(loads) == 2


def test_cold_start_corrupt_snapshot_is_unavailable(agent_index, docs_dir, make_pipeline):
    write(docs_dir / "A.md", "# A\n\nAlpha.")
    make_pipeline().run()
    (agent_index / "faiss" / "index.snapshot").write_bytes(b"partial")
    assert "knowledge base is not available" in search("anything")

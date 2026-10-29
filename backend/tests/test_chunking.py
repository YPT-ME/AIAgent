"""Loading and chunking: section context, wiki links and source metadata."""

from pathlib import Path

from src.ingestion.chunking import DocumentChunker, split_markdown_sections
from src.ingestion.loaders import DocumentLoader, absolutize_wiki_links, doc_category
from tests.conftest import make_pdf, write

WIKI = "https://github.com/WWBN/AVideo/wiki/"


def test_sections_keep_heading_path_and_ignore_code_comments():
    text = (
        "# Title\n\nIntro.\n\n```bash\n# not a heading\nls\n```\n\n"
        "## Setup\n\nStep.\n\n### Firewall\n\nOpen port 3000.\n\n## Problems\n\n| A | B |\n| --- | --- |\n"
    )
    sections = split_markdown_sections(text)
    assert [path for path, _ in sections] == [
        ["Title"],
        ["Title", "Setup"],
        ["Title", "Setup", "Firewall"],
        ["Title", "Problems"],
    ]
    assert "# not a heading" in sections[0][1]
    assert "".join(t for _, t in sections) == text  # nothing lost or reformatted


def test_long_technical_section_keeps_its_context_in_every_chunk(tmp_path: Path):
    rows = "".join(f"| `function{i}()` | [{i}](https://example.com/L{i}) |\n" for i in range(120))
    page = write(
        tmp_path / "technical" / "reference" / "Technical-Reference-Encoder-01.md",
        "# Technical source reference: Encoder (1)\n\nAudience: developers. Review date: 2026-10-29.\n\n"
        f"## API/API.php\n\n| Named function/method | Source line |\n| --- | --- |\n{rows}",
    )
    docs = DocumentLoader().load_file(page, root=tmp_path)
    chunks = DocumentChunker(chunk_size=1000, chunk_overlap=100).chunk_documents(docs)

    table_chunks = [c for c in chunks if "function" in c.page_content]
    assert len(table_chunks) > 3
    for chunk in table_chunks:
        assert chunk.page_content.startswith(
            "[Technical-Reference-Encoder-01 | Technical source reference: Encoder (1) > API/API.php]\n"
        )
        assert chunk.metadata["section"] == "Technical source reference: Encoder (1) > API/API.php"
        assert chunk.metadata["category"] == "technical_inventory"
    assert all(c.metadata["chunk_index"] == i for i, c in enumerate(chunks))


def test_small_sections_are_merged_under_their_common_heading(tmp_path: Path):
    page = write(tmp_path / "Guide.md", "# Guide\n\nIntro.\n\n## One\n\nA.\n\n## Two\n\nB.\n")
    chunks = DocumentChunker(chunk_size=1000, chunk_overlap=100).chunk_documents(
        DocumentLoader().load_file(page)
    )
    assert len(chunks) == 1
    assert chunks[0].page_content.startswith("[Guide | Guide]\n# Guide")
    assert "## One" in chunks[0].page_content and "## Two" in chunks[0].page_content


def test_pdf_chunks_name_file_and_page(tmp_path: Path):
    pdf = make_pdf(tmp_path / "Free plugins.pdf", ["Free plugins already included", "LoginApple Update"])
    chunks = DocumentChunker().chunk_documents(DocumentLoader().load_file(pdf, root=tmp_path))
    assert [c.page_content.splitlines()[0] for c in chunks] == [
        "[Free plugins.pdf, page 1]",
        "[Free plugins.pdf, page 2]",
    ]
    assert chunks[1].metadata["category"] == "pdf"
    assert "wiki_url" not in chunks[1].metadata


def test_relative_wiki_links_become_absolute():
    text = (
        "See [Live](Live-Plugin), [thumbs](Automatic-Thumbs-(JPG-GIF)-on-direct-uploaded-MP4-videos), "
        "[fails](How-to-Update#if-the-update-fails), [ext](https://example.com/x), "
        "[anchor](#local) and ![img](images/a.png)."
    )
    result = absolutize_wiki_links(text)
    assert f"[Live]({WIKI}Live-Plugin)" in result
    assert f"[thumbs]({WIKI}Automatic-Thumbs-(JPG-GIF)-on-direct-uploaded-MP4-videos)" in result
    assert f"[fails]({WIKI}How-to-Update#if-the-update-fails)" in result
    assert "[ext](https://example.com/x)" in result
    assert "[anchor](#local)" in result
    assert "![img](images/a.png)" in result


def test_categories_distinguish_guides_explanations_and_inventories():
    assert doc_category("Local-Encoder") == "guide"
    assert doc_category("Technical-Payments") == "technical"
    assert doc_category("Technical-Plugin-Index") == "technical"
    assert doc_category("Technical-Plugin-WebRTC") == "technical_plugin"
    assert doc_category("Technical-Reference-Index") == "technical"
    assert doc_category("Technical-Reference-Objects-01") == "technical_inventory"


def test_guide_without_stated_audience_gets_no_invented_metadata(tmp_path: Path):
    page = write(tmp_path / "Local-Encoder.md", "# Local Encoder: prepare videos\n\nText.\n")
    meta = DocumentLoader().load_file(page)[0].metadata
    assert meta["title"] == "Local Encoder: prepare videos"
    assert meta["wiki_url"] == WIKI + "Local-Encoder"
    for key in ("audience", "plugin", "plugin_version", "review_date", "code_ownership"):
        assert key not in meta


def test_special_characters_in_page_names_are_encoded(tmp_path: Path):
    page = write(tmp_path / "Dark-&-Light-Themes.md", "# Themes\n\nText.\n")
    meta = DocumentLoader().load_file(page)[0].metadata
    assert meta["wiki_page"] == "Dark-&-Light-Themes"
    assert meta["wiki_url"] == WIKI + "Dark-%26-Light-Themes"

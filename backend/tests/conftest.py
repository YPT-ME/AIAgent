"""
Shared test fixtures.

Tests never call OpenAI or the analytics service: embeddings are a local keyword hash and
the API key is a placeholder that is never used for a request.
"""

import hashlib
import math
import os
import re
import socket
from pathlib import Path

import pytest

os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ["ANALYTICS_API_URL"] = "http://127.0.0.1:9"

from langchain_core.embeddings import Embeddings  # noqa: E402

from src.ingestion.ingest import IngestionPipeline  # noqa: E402
from src.ingestion.manifest import ManifestManager  # noqa: E402
from src.ingestion.vectorstore import FAISSVectorStore  # noqa: E402


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """A mistaken real model or analytics request must fail before connecting."""
    def blocked(*_args, **_kwargs):
        raise AssertionError("Network access is forbidden in offline tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


class KeywordEmbeddings(Embeddings):
    """Deterministic bag-of-words embedding: texts sharing words are close."""

    dim = 512

    def __init__(self) -> None:
        self.embedded_texts = 0

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts += len(texts)
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_pdf(path: Path, pages: list[str]) -> Path:
    """Write a minimal valid PDF with one line of text per page."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        content_id = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"

    out = "%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.encode("latin-1"))
    return path


@pytest.fixture
def embeddings() -> KeywordEmbeddings:
    return KeywordEmbeddings()


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    path = tmp_path / "docs"
    path.mkdir()
    return path


@pytest.fixture
def make_pipeline(tmp_path: Path, docs_dir: Path, embeddings: KeywordEmbeddings):
    """New pipeline objects over the same temporary index, like separate CLI runs."""

    def factory() -> IngestionPipeline:
        return IngestionPipeline(
            docs_dir=docs_dir,
            vectorstore=FAISSVectorStore(index_path=tmp_path / "faiss", embeddings=embeddings),
            manifest_manager=ManifestManager(manifest_path=tmp_path / "manifest.json"),
        )

    return factory

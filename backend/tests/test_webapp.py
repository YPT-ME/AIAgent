"""The /app-info route the chat UI reads for its deploy and knowledge base timestamps."""

import json
import os
from pathlib import Path

from src import webapp


def test_route_is_registered():
    assert "/app-info" in {route.path for route in webapp.app.routes}


def test_app_info_reports_knowledge_base(tmp_path: Path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "version": "1.0",
        "last_updated": "2026-08-20T00:30:30.172323",
        "documents": {
            "/a.md": {"chunk_count": 3},
            "/b.md": {"chunk_count": 4},
        },
    }))
    monkeypatch.setenv("MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(webapp, "_manifest_cache", None)

    body = webapp.app_info()

    assert body["kb_updated_at"] == "2026-08-20T00:30:30.172323+00:00"
    assert body["kb_documents"] == 2
    assert body["kb_chunks"] == 7
    assert body["server_started_at"]
    assert body["code_updated_at"]


def test_app_info_without_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MANIFEST_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setattr(webapp, "_manifest_cache", None)

    body = webapp.app_info()

    assert body["kb_updated_at"] is None
    assert body["kb_documents"] == 0


def test_manifest_is_reread_after_ingestion(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"last_updated": "2026-01-01T00:00:00", "documents": {}}))
    os.utime(manifest, (1, 1))
    assert webapp.knowledge_base_info(manifest)["kb_updated_at"].startswith("2026-01-01")

    manifest.write_text(json.dumps({"last_updated": "2026-02-01T00:00:00", "documents": {}}))
    os.utime(manifest, (2, 2))
    assert webapp.knowledge_base_info(manifest)["kb_updated_at"].startswith("2026-02-01")


def test_code_updated_at_is_newest_source_file(tmp_path: Path):
    (tmp_path / "src").mkdir()
    old, new = tmp_path / "src" / "old.py", tmp_path / "src" / "new.py"
    old.write_text("")
    new.write_text("")
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))

    assert webapp.code_updated_at(tmp_path) == webapp._iso(2_000_000)

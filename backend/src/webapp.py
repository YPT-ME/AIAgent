"""
RAG AI Agent - Custom HTTP routes

Mounted into LangGraph Server through the "http" key in langgraph.json, next to
the built-in routes. Serves GET /app-info, which the chat UI shows as a discreet
"last deploy / knowledge base updated" line.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI

APP_ROOT = Path(__file__).resolve().parent.parent
SERVER_STARTED_AT = datetime.now(timezone.utc)

app = FastAPI()

_manifest_cache: tuple[float, dict[str, Any]] | None = None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def code_updated_at(root: Path = APP_ROOT) -> str | None:
    """Newest modification time of the deployed code (src is bind-mounted from the host)."""
    files = [*(root / "src").rglob("*.py"), root / "langgraph.json", *root.glob("system_prompt*.txt")]
    mtimes = [f.stat().st_mtime for f in files if f.is_file()]
    return _iso(max(mtimes)) if mtimes else None


def knowledge_base_info(manifest_path: Path) -> dict[str, Any]:
    """When the index was last changed by an ingestion, and what it holds."""
    global _manifest_cache

    try:
        mtime = manifest_path.stat().st_mtime
    except OSError:
        return {"kb_updated_at": None, "kb_documents": 0, "kb_chunks": 0}

    if _manifest_cache is None or _manifest_cache[0] != mtime:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"kb_updated_at": None, "kb_documents": 0, "kb_chunks": 0}

        documents = data.get("documents") or {}
        updated = data.get("last_updated") or None
        if updated:
            # The manifest stores naive UTC timestamps
            parsed = datetime.fromisoformat(updated)
            updated = (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).isoformat()
        info = {
            "kb_updated_at": updated,
            "kb_documents": len(documents),
            "kb_chunks": sum(doc.get("chunk_count", 0) for doc in documents.values()),
        }
        _manifest_cache = (mtime, info)

    return _manifest_cache[1]


@app.get("/app-info")
def app_info() -> dict[str, Any]:
    manifest_path = Path(os.getenv("MANIFEST_PATH", "./storage/manifest.json"))
    return {
        "server_started_at": SERVER_STARTED_AT.isoformat(),
        "code_updated_at": code_updated_at(),
        **knowledge_base_info(manifest_path),
    }

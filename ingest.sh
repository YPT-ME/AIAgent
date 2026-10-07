#!/bin/bash
# RAG AI Agent - Update the knowledge base in one command
#
# Usage: ./ingest.sh ["test question"] [--no-pull]
#
#   1. git pull in data/docs (when it is a git clone; skip with --no-pull)
#   2. Rebuild the FAISS index from scratch
#   3. Restart langgraph-server so the agent loads the new index
#   4. Verify: server is up, index is consistent, a test search returns results

set -euo pipefail
cd "$(dirname "$0")"

PULL=1
QUERY="How do I get started?"
SERVICE=langgraph-server

for arg in "$@"; do
    case "$arg" in
        --no-pull) PULL=0 ;;
        --rebuild|-r) ;;  # always rebuilds now; kept for backward compatibility
        -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "Unknown option: $arg (see --help)"; exit 1 ;;
        *) QUERY="$arg" ;;
    esac
done

step() { echo ""; echo "▶ $*"; }
fail() { echo ""; echo "❌ $*"; exit 1; }

if docker compose version >/dev/null 2>&1; then
    DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    DC=(docker-compose)
else
    fail "Docker Compose not found."
fi

docker info >/dev/null 2>&1 \
    || fail "Cannot talk to Docker. Run with sudo or add your user to the docker group."

wait_for_server() {
    for _ in $(seq 1 90); do
        if "${DC[@]}" exec -T "$SERVICE" curl -fsS http://localhost:2024/ok >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

echo ""
echo "🔄 RAG AI Agent - Update Knowledge Base"
echo "========================================"

# 1. Pull the latest docs
if [ "$PULL" = 1 ] && [ -d data/docs/.git ]; then
    step "Pulling latest docs into data/docs..."
    git -C data/docs pull --ff-only \
        || echo "⚠️  git pull failed - continuing with the files already on disk"
fi

if [ -z "$(find data/docs -type f \( -name '*.md' -o -name '*.markdown' -o -name '*.pdf' \) 2>/dev/null | head -1)" ]; then
    fail "No .md/.markdown/.pdf files found in data/docs."
fi

# 2. Rebuild the index (incremental mode leaves stale chunks of edited/deleted files)
if ! "${DC[@]}" exec -T "$SERVICE" true >/dev/null 2>&1; then
    step "Starting $SERVICE..."
    "${DC[@]}" up -d "$SERVICE"
    wait_for_server || fail "$SERVICE did not come up. Check: ${DC[*]} logs $SERVICE"
fi

step "Rebuilding the index from scratch (this may take a few minutes)..."
"${DC[@]}" exec -T "$SERVICE" python -m src.ingestion.ingest --docs-dir /app/data/docs --rebuild \
    || fail "Ingestion failed. $SERVICE was NOT restarted, so the agent keeps answering from the old index in memory. Fix the error above and run this script again."

# 3. Restart so the agent drops its cached index
step "Restarting $SERVICE..."
"${DC[@]}" restart "$SERVICE"
wait_for_server || fail "$SERVICE did not come back up. Check: ${DC[*]} logs $SERVICE"
echo "   Server is up."

# 4. Verify
step "Verifying..."
"${DC[@]}" exec -T "$SERVICE" python - "$QUERY" <<'PY' || fail "Verification failed - see above."
import logging
import sys

logging.disable(logging.CRITICAL)

from src.ingestion.ingest import IngestionPipeline

query = sys.argv[1]
pipeline = IngestionPipeline()
status = pipeline.get_status()
store = pipeline.vectorstore
ok = True

print(f"   Files in data/docs:  {status['files_count']}")
print(f"   Documents indexed:   {status['indexed_documents']}")
print(f"   Chunks in manifest:  {status['total_chunks']}")

if not store.load():
    print("❌ FAISS index could not be loaded")
    sys.exit(1)

vectors = store._vectorstore.index.ntotal
print(f"   Vectors in FAISS:    {vectors}")

if status["indexed_documents"] == 0 or vectors == 0:
    print("❌ Index is empty")
    sys.exit(1)

if vectors != status["total_chunks"]:
    print("❌ FAISS and manifest are out of sync")
    ok = False

skipped = status["files_count"] - status["indexed_documents"]
if skipped > 0:
    print(f"⚠️  {skipped} file(s) not indexed (empty or unreadable) - see the ingestion log above")

print(f'\n   Test search: "{query}"')
results = store.similarity_search(query, k=3)
if not results:
    print("❌ Search returned no results")
    ok = False
for doc in results:
    print(f"     → {doc.metadata.get('file_name', 'Unknown')}")

sys.exit(0 if ok else 1)
PY

echo ""
echo "✅ Done! The agent is now answering with the updated docs."

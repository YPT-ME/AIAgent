#!/bin/bash
set -e

echo "==================================="
echo "Starting RAG AI Agent"
echo "==================================="

# Run document ingestion on startup (if documents exist)
if [ -d "/app/data/docs" ] && [ "$(ls -A /app/data/docs)" ]; then
    echo ""
    echo "📚 Running automatic document ingestion..."
    python -m src.ingestion.ingest || {
        echo "⚠️  Warning: Ingestion failed, but continuing..."
    }
    echo ""
else
    echo "⚠️  No documents found in /app/data/docs - skipping ingestion"
fi

# Start LangGraph Server
echo "🚀 Starting LangGraph Server..."
echo "==================================="
exec "$@"

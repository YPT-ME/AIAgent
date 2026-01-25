#!/bin/bash
# RAG AI Agent - Document Ingestion Script
# Usage: ./ingest.sh [--rebuild]

echo ""
echo "🔄 RAG AI Agent - Document Ingestion"
echo "===================================="
echo ""

if [ "$1" == "--rebuild" ] || [ "$1" == "-r" ]; then
    echo "⚠️  Rebuild mode: Reindexing ALL documents..."
    echo ""
    docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs --rebuild
else
    echo "📄 Indexing new/modified documents..."
    echo ""
    docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs
fi

echo ""
echo "✅ Done!"

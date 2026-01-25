@echo off
REM RAG AI Agent - Document Ingestion Script
REM Usage: ingest.bat [rebuild]

echo.
echo 🔄 RAG AI Agent - Document Ingestion
echo ====================================
echo.

if "%1"=="rebuild" (
    echo ⚠️  Rebuild mode: Reindexing ALL documents...
    echo.
    docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs --rebuild
) else (
    echo 📄 Indexing new/modified documents...
    echo.
    docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs
)

echo.
echo ✅ Done!

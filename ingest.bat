@echo off
REM RAG AI Agent - Document Ingestion Script
REM Supports: PDF, Markdown files (scans subdirectories)
REM Usage: ingest.bat [rebuild]

echo.
echo 🔄 RAG AI Agent - Document Ingestion
echo ====================================
echo.

if "%1"=="rebuild" (
    echo ⚠️  Rebuild mode: Reindexing ALL documents...
    echo.
    docker compose exec langgraph-server python -m src.ingestion.ingest --docs-dir /app/data/docs --rebuild
) else (
    echo 📄 Indexing new/modified documents...
    echo.
    docker compose exec langgraph-server python -m src.ingestion.ingest --docs-dir /app/data/docs
)

set "INGEST_EXIT_CODE=%ERRORLEVEL%"
if not "%INGEST_EXIT_CODE%"=="0" (
    echo.
    echo Ingestion failed. Check the error above.
    exit /b %INGEST_EXIT_CODE%
)

echo.
echo ✅ Done!
exit /b 0

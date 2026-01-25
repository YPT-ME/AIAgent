# RAG AI Agent - Document Ingestion Script
# Supports: PDF, Markdown files (scans subdirectories)
# Usage: .\ingest.ps1 [--rebuild]

param(
    [switch]$rebuild
)

Write-Host "`n🔄 RAG AI Agent - Document Ingestion" -ForegroundColor Cyan
Write-Host "Supported formats: .pdf, .md, .markdown" -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

if ($rebuild) {
    Write-Host "⚠️  Rebuild mode: Reindexing ALL documents...`n" -ForegroundColor Yellow
    docker compose exec langgraph-server python -m src.ingestion.ingest --docs-dir /app/data/docs --rebuild
} else {
    Write-Host "📄 Indexing new/modified documents...`n" -ForegroundColor Green
    docker compose exec langgraph-server python -m src.ingestion.ingest --docs-dir /app/data/docs
}

Write-Host "`n✅ Done!" -ForegroundColor Green

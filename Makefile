# =============================================================================
# RAG AI Agent - Makefile
# =============================================================================
# Common commands for development and deployment

.PHONY: help install dev test lint format type-check ingest run docker-build docker-up docker-down clean

# Default target
help:
	@echo "RAG AI Agent - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Development:"
	@echo "  make install        Install all dependencies"
	@echo "  make dev            Run LangGraph Server in development mode"
	@echo "  make dev-ui         Run Agent Chat UI in development mode"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           Run all tests"
	@echo "  make test-verbose   Run tests with verbose output"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (black)"
	@echo "  make type-check     Run type checker (mypy)"
	@echo "  make check          Run all quality checks"
	@echo ""
	@echo "Ingestion:"
	@echo "  make ingest         Run document ingestion"
	@echo "  make ingest-rebuild Rebuild FAISS index from scratch"
	@echo "  make ingest-status  Show ingestion status"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker images"
	@echo "  make docker-up      Start all services"
	@echo "  make docker-down    Stop all services"
	@echo "  make docker-logs    View service logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Clean generated files"

# =============================================================================
# Installation
# =============================================================================

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -e ".[dev]"
	@echo ""
	@echo "Done! For the UI, follow the instructions in ui/README.md"
	@echo "to set up Agent Chat UI."
	@echo ""
	@echo "Don't forget to copy .env.example to .env and add your API keys."

install-backend:
	cd backend && pip install -e ".[dev]"

# =============================================================================
# Development
# =============================================================================

dev:
	cd backend && langgraph dev

run:
	cd backend && langgraph serve --host 0.0.0.0 --port 2024

# =============================================================================
# Testing & Quality
# =============================================================================

test:
	cd backend && pytest

test-verbose:
	cd backend && pytest -v --tb=short

test-coverage:
	cd backend && pytest --cov=src --cov-report=html --cov-report=term

lint:
	cd backend && ruff check src tests

lint-fix:
	cd backend && ruff check src tests --fix

format:
	cd backend && black src tests

format-check:
	cd backend && black src tests --check

type-check:
	cd backend && mypy src

check: format-check lint type-check test
	@echo "All checks passed!"

# =============================================================================
# Ingestion
# =============================================================================

ingest:
	cd backend && python -m src.ingestion.ingest --pdf-dir ../data/pdfs

ingest-rebuild:
	cd backend && python -m src.ingestion.ingest --pdf-dir ../data/pdfs --rebuild

ingest-status:
	cd backend && python -m src.ingestion.ingest --status

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-up-build:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-logs-backend:
	docker compose logs -f langgraph-server

docker-logs-ui:
	docker compose logs -f agent-chat-ui

docker-shell:
	docker compose exec langgraph-server /bin/bash

docker-ingest:
	docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs

docker-ingest-rebuild:
	docker compose exec langgraph-server python -m src.ingestion.ingest --pdf-dir /app/data/pdfs --rebuild

docker-ingest-status:
	docker compose exec langgraph-server python -m src.ingestion.ingest --status

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaning Node modules..."
	rm -rf ui/node_modules 2>/dev/null || true
	@echo "Done!"

clean-storage:
	@echo "Cleaning FAISS index and manifest..."
	rm -rf backend/storage/faiss/* 2>/dev/null || true
	rm -f backend/storage/manifest.json 2>/dev/null || true
	@echo "Done!"

# =============================================================================
# Setup Helpers
# =============================================================================

setup-dirs:
	mkdir -p data/pdfs
	mkdir -p backend/storage/faiss

setup: setup-dirs
	cp -n .env.example .env 2>/dev/null || true
	cp -n .env.example backend/.env 2>/dev/null || true
	@echo "Setup complete! Edit .env files with your API keys."
	@echo "For UI setup, see ui/README.md"

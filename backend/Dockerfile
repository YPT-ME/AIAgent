# =============================================================================
# RAG AI Agent - LangGraph Server Dockerfile
# =============================================================================
# Multi-stage build for production-ready LangGraph Server

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the package with all dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY ./src ./src
COPY ./langgraph.json ./langgraph.json
COPY ./system_prompt.txt ./system_prompt.txt
COPY ./system_prompt.example.txt ./system_prompt.example.txt

# Create storage directories
RUN mkdir -p /app/storage/faiss /app/data/pdfs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Expose LangGraph Server port
EXPOSE 2024

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:2024/health || exit 1

# Run LangGraph Server
CMD ["langgraph", "serve", "--host", "0.0.0.0", "--port", "2024"]

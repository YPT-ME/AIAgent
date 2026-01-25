"""
RAG AI Agent - Document Ingestion Module

This module provides functionality for ingesting documents into the RAG system:
- PDF loading with LlamaIndex
- Text chunking with LangChain
- Embedding generation with OpenAI
- Vector storage with FAISS
- Manifest tracking for incremental updates
"""

from src.ingestion.ingest import IngestionPipeline, run_ingestion, main

__all__ = ["IngestionPipeline", "run_ingestion", "main"]

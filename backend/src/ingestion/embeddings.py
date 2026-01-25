"""
RAG AI Agent - OpenAI Embeddings

This module provides the embedding functionality using OpenAI's embedding models.
"""

import logging
import os

from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


def get_embeddings() -> OpenAIEmbeddings:
    """
    Get an OpenAI embeddings instance.
    
    Returns:
        OpenAIEmbeddings instance configured with the API key
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    embeddings = OpenAIEmbeddings(
        model=model,
        api_key=api_key,
    )
    
    logger.info(f"Initialized OpenAI embeddings with model: {model}")
    return embeddings

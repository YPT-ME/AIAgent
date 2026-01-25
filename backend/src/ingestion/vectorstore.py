"""
RAG AI Agent - FAISS Vector Store Management

This module provides FAISS vector store functionality for storing
and retrieving document embeddings.
"""

import logging
import os
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.ingestion.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# File names for FAISS persistence
FAISS_INDEX_FILE = "index.faiss"
FAISS_DOCSTORE_FILE = "index.pkl"


class FAISSVectorStore:
    """
    Manages a FAISS vector store for document embeddings.
    
    Supports adding documents, similarity search, and persistence
    to disk for reuse across application restarts.
    """
    
    def __init__(self, index_path: Path | None = None) -> None:
        """
        Initialize the FAISS vector store.
        
        Args:
            index_path: Path to store/load the FAISS index
        """
        default_path = os.getenv("FAISS_INDEX_PATH", "./storage/faiss")
        self.index_path = index_path or Path(default_path)
        self.index_path = Path(self.index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self._vectorstore: FAISS | None = None
        self.embeddings = get_embeddings()
        
        logger.info(f"FAISS vector store initialized at: {self.index_path}")
    
    @property
    def index_file(self) -> Path:
        """Get the path to the FAISS index file."""
        return self.index_path / FAISS_INDEX_FILE
    
    @property
    def docstore_file(self) -> Path:
        """Get the path to the docstore file."""
        return self.index_path / FAISS_DOCSTORE_FILE
    
    def exists(self) -> bool:
        """Check if the FAISS index exists on disk."""
        return self.index_file.exists() and self.docstore_file.exists()
    
    def load(self) -> bool:
        """
        Load the FAISS index from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.exists():
            logger.warning("No existing FAISS index found")
            return False
        
        try:
            logger.info(f"Loading FAISS index from: {self.index_path}")
            self._vectorstore = FAISS.load_local(
                str(self.index_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            doc_count = len(self._vectorstore.docstore._dict)
            logger.info(f"Loaded FAISS index with {doc_count} documents")
            return True
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            return False
    
    def save(self) -> bool:
        """
        Save the FAISS index to disk.
        
        Returns:
            True if saved successfully, False otherwise
        """
        if self._vectorstore is None:
            logger.warning("No vector store to save")
            return False
        
        try:
            logger.info(f"Saving FAISS index to: {self.index_path}")
            self._vectorstore.save_local(str(self.index_path))
            logger.info("FAISS index saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            return False
    
    def create_from_documents(self, documents: list[Document]) -> bool:
        """
        Create a new vector store from documents.
        
        Args:
            documents: List of LangChain documents to embed
            
        Returns:
            True if created successfully
        """
        if not documents:
            logger.warning("No documents provided to create vector store")
            return False
        
        try:
            logger.info(f"Creating FAISS index from {len(documents)} documents")
            self._vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings,
            )
            logger.info("FAISS index created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating FAISS index: {e}")
            return False
    
    def add_documents(self, documents: list[Document]) -> bool:
        """
        Add documents to an existing vector store.
        
        Args:
            documents: List of documents to add
            
        Returns:
            True if added successfully
        """
        if not documents:
            logger.warning("No documents provided to add")
            return False
        
        # Load existing index if not loaded
        if self._vectorstore is None:
            if not self.load():
                # No existing index, create new
                return self.create_from_documents(documents)
        
        try:
            logger.info(f"Adding {len(documents)} documents to FAISS index")
            self._vectorstore.add_documents(documents)
            logger.info("Documents added successfully")
            return True
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def delete_index(self) -> bool:
        """
        Delete the FAISS index from disk.
        
        Returns:
            True if deleted successfully
        """
        try:
            if self.index_file.exists():
                self.index_file.unlink()
            if self.docstore_file.exists():
                self.docstore_file.unlink()
            self._vectorstore = None
            logger.info("FAISS index deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting FAISS index: {e}")
            return False
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:
        """
        Perform similarity search.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of similar documents
        """
        if self._vectorstore is None:
            if not self.load():
                logger.warning("No vector store available for search")
                return []
        
        return self._vectorstore.similarity_search(query=query, k=k)
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of (document, score) tuples
        """
        if self._vectorstore is None:
            if not self.load():
                logger.warning("No vector store available for search")
                return []
        
        return self._vectorstore.similarity_search_with_score(query=query, k=k)


# Global vector store instance
_vectorstore: FAISSVectorStore | None = None


def get_vectorstore() -> FAISSVectorStore:
    """
    Get the global vector store instance.
    
    Returns:
        FAISSVectorStore instance
    """
    global _vectorstore
    
    if _vectorstore is None:
        _vectorstore = FAISSVectorStore()
    
    return _vectorstore

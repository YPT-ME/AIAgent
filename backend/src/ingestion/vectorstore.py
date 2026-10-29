"""
RAG AI Agent - FAISS Vector Store Management

This module provides FAISS vector store functionality for storing
and retrieving document embeddings.
"""

import logging
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.ingestion.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# File names for FAISS persistence
FAISS_INDEX_FILE = "index.faiss"
FAISS_DOCSTORE_FILE = "index.pkl"
FAISS_SNAPSHOT_FILE = "index.snapshot"


def index_files(index_path: Path) -> tuple[Path, ...]:
    """One atomic snapshot, or the two files of a legacy index."""
    snapshot = index_path / FAISS_SNAPSHOT_FILE
    return (snapshot,) if snapshot.exists() else (
        index_path / FAISS_INDEX_FILE, index_path / FAISS_DOCSTORE_FILE,
    )


def load_faiss_index(index_path: Path, embeddings: Embeddings) -> FAISS:
    """Load trusted local storage; new saves contain vectors and metadata in one file."""
    files = index_files(index_path)
    if len(files) == 1:
        store = FAISS.deserialize_from_bytes(
            files[0].read_bytes(), embeddings, allow_dangerous_deserialization=True,
        )
    else:
        store = FAISS.load_local(
            str(index_path), embeddings, allow_dangerous_deserialization=True,
        )
    ids = store.index_to_docstore_id
    if (set(ids) != set(range(store.index.ntotal))
            or len(set(ids.values())) != len(ids)
            or set(ids.values()) != set(store.docstore._dict)):
        raise ValueError("FAISS index and docstore do not match")
    return store


class FAISSVectorStore:
    """
    Manages a FAISS vector store for document embeddings.
    
    Supports adding documents, similarity search, and persistence
    to disk for reuse across application restarts.
    """
    
    def __init__(
        self,
        index_path: Path | None = None,
        embeddings: Embeddings | None = None,
    ) -> None:
        """
        Initialize the FAISS vector store.

        Args:
            index_path: Path to store/load the FAISS index
            embeddings: Embedding model (defaults to OpenAI)
        """
        default_path = os.getenv("FAISS_INDEX_PATH", "./storage/faiss")
        self.index_path = index_path or Path(default_path)
        self.index_path = Path(self.index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        self._vectorstore: FAISS | None = None
        # Set by reset(): build a new index instead of loading the one on disk
        self._ignore_disk = False
        self.embeddings = embeddings or get_embeddings()
        
        logger.info(f"FAISS vector store initialized at: {self.index_path}")
    
    @property
    def index_file(self) -> Path:
        """Get the path to the FAISS index file."""
        return self.index_path / FAISS_INDEX_FILE
    
    @property
    def docstore_file(self) -> Path:
        """Get the path to the docstore file."""
        return self.index_path / FAISS_DOCSTORE_FILE

    @property
    def snapshot_file(self) -> Path:
        """Atomic persistence of vectors, docstore and their mapping."""
        return self.index_path / FAISS_SNAPSHOT_FILE
    
    def exists(self) -> bool:
        """Check if the FAISS index exists on disk."""
        return all(p.exists() for p in index_files(self.index_path))
    
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
            self._vectorstore = load_faiss_index(self.index_path, self.embeddings)
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
        
        # Two os.replace calls cannot commit a .faiss/.pkl pair atomically. Serialize
        # the complete store and publish it with one replacement (also on Windows).
        tmp_path = None
        try:
            logger.info(f"Saving FAISS index to: {self.index_path}")
            with tempfile.NamedTemporaryFile(dir=self.index_path, prefix=".saving-", delete=False) as f:
                tmp_path = Path(f.name)
                f.write(self._vectorstore.serialize_to_bytes())
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.snapshot_file)
            self._ignore_disk = False
            logger.info("FAISS index saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            return False
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    def reset(self) -> None:
        """Start a new, empty index in memory. The index on disk is kept until save()."""
        self._vectorstore = None
        self._ignore_disk = True

    def _load_existing(self) -> None:
        """Load the index on disk, unless reset() started a new one. Raises if it is unreadable."""
        needs_existing = self._vectorstore is None and not self._ignore_disk and self.exists()
        if needs_existing and not self.load():
            raise RuntimeError(
                f"Existing FAISS index at {self.index_path} could not be loaded; "
                "run the ingestion with --rebuild"
            )

    def chunk_counts(self) -> Counter[str]:
        """Number of chunks per file_path in the index (empty when there is no index)."""
        self._load_existing()
        if self._vectorstore is None:
            return Counter()
        return Counter(
            doc.metadata.get("file_path") for doc in self._vectorstore.docstore._dict.values()
        )

    def legacy_sources(self) -> set[str]:
        """Files whose IDs/metadata predate stable per-file chunks, even at equal counts."""
        self._load_existing()
        if self._vectorstore is None:
            return set()
        return {
            doc.metadata.get("file_path")
            for doc_id, doc in self._vectorstore.docstore._dict.items()
            if doc.metadata.get("chunk_id") != doc_id
            or not doc_id.startswith(f"{doc.metadata.get('file_path')}#")
        }

    def replace_documents(
        self,
        sources: list[str],
        documents: list[Document],
        current_sources: set[str] | None = None,
    ) -> int:
        """
        Remove every chunk whose file_path is in sources, then add documents (in memory).

        Removing by source also drops duplicates left by older incremental runs.
        Errors are raised, so the caller does not record a failed update as indexed.

        Args:
            sources: file_path values whose existing chunks must be removed
            documents: new chunks, each with a unique metadata["chunk_id"]
            current_sources: when given, chunks of any other file_path are removed too
                (files that left the docs folder but were never in the manifest)

        Returns:
            Number of chunks removed
        """
        self._load_existing()

        removed = 0
        if self._vectorstore is not None and (sources or current_sources is not None):
            source_set = set(sources)
            stale_ids = [
                doc_id
                for doc_id, doc in self._vectorstore.docstore._dict.items()
                if doc.metadata.get("file_path") in source_set
                or (current_sources is not None and doc.metadata.get("file_path") not in current_sources)
            ]
            if stale_ids:
                self._vectorstore.delete(stale_ids)
                removed = len(stale_ids)
                logger.info(f"Removed {removed} outdated chunks from the FAISS index")

        if documents:
            ids = [doc.metadata["chunk_id"] for doc in documents]
            if self._vectorstore is None:
                self._vectorstore = FAISS.from_documents(documents, self.embeddings, ids=ids)
            else:
                self._vectorstore.add_documents(documents, ids=ids)
            logger.info(f"Added {len(documents)} chunks to the FAISS index")

        return removed

    @property
    def is_loaded(self) -> bool:
        """Whether an index (possibly empty) is held in memory."""
        return self._vectorstore is not None

    @property
    def vector_count(self) -> int:
        """Number of vectors in the loaded index (0 when none is loaded)."""
        return self._vectorstore.index.ntotal if self._vectorstore is not None else 0
    
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
            if self.snapshot_file.exists():
                self.snapshot_file.unlink()
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

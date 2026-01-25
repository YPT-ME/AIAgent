"""
RAG AI Agent - Document Manifest Management

This module manages a manifest file that tracks which documents have been
indexed, their hashes, and when they were last processed. This enables
incremental updates where only changed files are re-indexed.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DocumentEntry(BaseModel):
    """Represents a single document entry in the manifest."""
    
    filename: str
    filepath: str
    file_hash: str
    last_indexed_at: str
    chunk_count: int
    file_size: int
    page_count: int | None = None


class Manifest(BaseModel):
    """Document manifest tracking indexed files."""
    
    version: str = "1.0"
    last_updated: str = ""
    documents: dict[str, DocumentEntry] = {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        """Create manifest from dictionary."""
        return cls.model_validate(data)


class ManifestManager:
    """
    Manages the document manifest for tracking indexed files.
    
    The manifest enables incremental updates by tracking file hashes
    and only re-indexing files that have changed.
    """
    
    def __init__(self, manifest_path: Path | None = None) -> None:
        """
        Initialize the manifest manager.
        
        Args:
            manifest_path: Path to the manifest file
        """
        default_path = os.getenv("MANIFEST_PATH", "./storage/manifest.json")
        self.manifest_path = manifest_path or Path(default_path)
        self.manifest_path = Path(self.manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._manifest: Manifest | None = None
        logger.info(f"Manifest manager initialized at: {self.manifest_path}")
    
    def load(self) -> Manifest:
        """
        Load the manifest from disk.
        
        Returns:
            Loaded or new manifest
        """
        if self._manifest is not None:
            return self._manifest
        
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._manifest = Manifest.from_dict(data)
                logger.info(
                    f"Loaded manifest with {len(self._manifest.documents)} documents"
                )
            except Exception as e:
                logger.warning(f"Error loading manifest, creating new: {e}")
                self._manifest = Manifest()
        else:
            logger.info("No existing manifest found, creating new")
            self._manifest = Manifest()
        
        return self._manifest
    
    def save(self) -> bool:
        """
        Save the manifest to disk.
        
        Returns:
            True if saved successfully
        """
        if self._manifest is None:
            self._manifest = Manifest()
        
        self._manifest.last_updated = datetime.utcnow().isoformat()
        
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self._manifest.to_dict(), f, indent=2)
            logger.info(f"Saved manifest to {self.manifest_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving manifest: {e}")
            return False
    
    def clear(self) -> None:
        """Clear the manifest."""
        self._manifest = Manifest()
        self.save()
        logger.info("Manifest cleared")
    
    @staticmethod
    def compute_file_hash(filepath: Path) -> str:
        """
        Compute SHA256 hash of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def is_file_indexed(self, filepath: Path) -> bool:
        """
        Check if a file is already indexed with the same hash.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if file is indexed with same content
        """
        manifest = self.load()
        file_key = str(filepath.absolute())
        
        if file_key not in manifest.documents:
            return False
        
        current_hash = self.compute_file_hash(filepath)
        return manifest.documents[file_key].file_hash == current_hash
    
    def add_document(
        self,
        filepath: Path,
        chunk_count: int,
        page_count: int | None = None,
    ) -> None:
        """
        Add or update a document in the manifest.
        
        Args:
            filepath: Path to the document
            chunk_count: Number of chunks created
            page_count: Number of pages in document
        """
        manifest = self.load()
        file_key = str(filepath.absolute())
        
        entry = DocumentEntry(
            filename=filepath.name,
            filepath=file_key,
            file_hash=self.compute_file_hash(filepath),
            last_indexed_at=datetime.utcnow().isoformat(),
            chunk_count=chunk_count,
            file_size=filepath.stat().st_size,
            page_count=page_count,
        )
        
        manifest.documents[file_key] = entry
        logger.debug(f"Added document to manifest: {filepath.name}")
    
    def remove_document(self, filepath: Path) -> bool:
        """
        Remove a document from the manifest.
        
        Args:
            filepath: Path to remove
            
        Returns:
            True if removed, False if not found
        """
        manifest = self.load()
        file_key = str(filepath.absolute())
        
        if file_key in manifest.documents:
            del manifest.documents[file_key]
            logger.debug(f"Removed document from manifest: {filepath.name}")
            return True
        return False
    
    def get_files_to_index(self, pdf_files: list[Path]) -> list[Path]:
        """
        Determine which files need to be indexed.
        
        Args:
            pdf_files: List of PDF file paths
            
        Returns:
            List of files that need indexing
        """
        files_to_index = []
        
        for pdf_file in pdf_files:
            if not self.is_file_indexed(pdf_file):
                files_to_index.append(pdf_file)
        
        logger.info(f"{len(files_to_index)} of {len(pdf_files)} files need indexing")
        return files_to_index
    
    def get_removed_files(self, pdf_files: list[Path]) -> list[Path]:
        """
        Find files in manifest that no longer exist.
        
        Args:
            pdf_files: Current list of PDF files
            
        Returns:
            List of file paths that were removed
        """
        manifest = self.load()
        current_paths = {str(p.absolute()) for p in pdf_files}
        
        removed = []
        for file_key in manifest.documents:
            if file_key not in current_paths:
                removed.append(Path(file_key))
        
        return removed
    
    @property
    def document_count(self) -> int:
        """Get the number of indexed documents."""
        return len(self.load().documents)
    
    @property
    def total_chunks(self) -> int:
        """Get the total number of chunks across all documents."""
        manifest = self.load()
        return sum(doc.chunk_count for doc in manifest.documents.values())


# Global manifest manager instance
_manifest_manager: ManifestManager | None = None


def get_manifest_manager() -> ManifestManager:
    """
    Get the global manifest manager instance.
    
    Returns:
        ManifestManager instance
    """
    global _manifest_manager
    
    if _manifest_manager is None:
        _manifest_manager = ManifestManager()
    
    return _manifest_manager

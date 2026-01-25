"""
RAG AI Agent - Document Loaders

This module provides document loading functionality using LlamaIndex
for parsing PDF and Markdown files with metadata.
"""

import logging
from pathlib import Path

from llama_index.core import Document

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown"}


class DocumentLoader:
    """
    Loads documents using LlamaIndex readers.
    
    Supports PDF and Markdown files, extracting text content
    along with metadata including file path, file name, and page numbers.
    """
    
    def __init__(self) -> None:
        """Initialize the document loader."""
        pass
    
    def load_file(self, file_path: Path) -> list[Document]:
        """
        Load a single file and return documents with metadata.
        
        Args:
            file_path: Path to the file (PDF or Markdown)
            
        Returns:
            List of LlamaIndex Document objects
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return []
        
        extension = file_path.suffix.lower()
        
        if extension == ".pdf":
            return self._load_pdf(file_path)
        elif extension in {".md", ".markdown"}:
            return self._load_markdown(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return []
    
    def _load_pdf(self, file_path: Path) -> list[Document]:
        """
        Load a PDF file using pdfplumber (more tolerant with problematic PDFs).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects (one per page)
        """
        try:
            import pdfplumber
            
            logger.info(f"Loading PDF: {file_path.name}")
            
            enriched_docs = []
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        doc = Document(
                            text=text,
                            metadata={
                                "file_path": str(file_path.absolute()),
                                "file_name": file_path.name,
                                "file_type": "pdf",
                                "page_number": idx + 1,
                                "total_pages": total_pages,
                            }
                        )
                        enriched_docs.append(doc)
            
            logger.info(f"Loaded {len(enriched_docs)} pages from {file_path.name}")
            return enriched_docs
            
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {e}")
            return []
    
    def _load_markdown(self, file_path: Path) -> list[Document]:
        """
        Load a Markdown file.
        
        Args:
            file_path: Path to the Markdown file
            
        Returns:
            List containing a single Document object
        """
        try:
            logger.info(f"Loading Markdown: {file_path.name}")
            
            content = file_path.read_text(encoding="utf-8")
            
            if not content.strip():
                logger.warning(f"Empty markdown file: {file_path.name}")
                return []
            
            doc = Document(
                text=content,
                metadata={
                    "file_path": str(file_path.absolute()),
                    "file_name": file_path.name,
                    "file_type": "markdown",
                    "page_number": 1,
                    "total_pages": 1,
                },
            )
            
            logger.info(f"Loaded markdown file: {file_path.name}")
            return [doc]
            
        except Exception as e:
            logger.error(f"Error loading Markdown {file_path}: {e}")
            return []
    
    def load_directory(
        self, 
        directory: Path, 
        recursive: bool = True
    ) -> dict[str, list[Document]]:
        """
        Load all supported files from a directory.
        
        Args:
            directory: Path to the directory containing documents
            recursive: Whether to search subdirectories
            
        Returns:
            Dictionary mapping file paths to their documents
        """
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return {}
        
        if not directory.is_dir():
            logger.error(f"Not a directory: {directory}")
            return {}
        
        # Find all supported files
        all_files = []
        for ext in SUPPORTED_EXTENSIONS:
            pattern = f"**/*{ext}" if recursive else f"*{ext}"
            all_files.extend(directory.glob(pattern))
        
        logger.info(f"Found {len(all_files)} supported files in {directory}")
        
        results: dict[str, list[Document]] = {}
        for file_path in all_files:
            docs = self.load_file(file_path)
            if docs:
                results[str(file_path)] = docs
        
        total_docs = sum(len(docs) for docs in results.values())
        logger.info(f"Loaded {total_docs} total documents from {len(results)} files")
        
        return results


# Backward compatibility alias
PDFDocumentLoader = DocumentLoader

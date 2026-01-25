"""
RAG AI Agent - Main Ingestion Orchestrator

This module provides the main ingestion pipeline that:
1. Scans a directory for supported files (PDF, Markdown)
2. Determines which files need indexing (based on hash changes)
3. Loads and parses documents using LlamaIndex
4. Chunks documents using LangChain
5. Embeds and stores in FAISS
6. Updates the manifest

Can be run as a CLI command or called programmatically.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from src.ingestion.chunking import DocumentChunker
from src.ingestion.loaders import DocumentLoader, SUPPORTED_EXTENSIONS
from src.ingestion.manifest import ManifestManager, get_manifest_manager
from src.ingestion.vectorstore import FAISSVectorStore, get_vectorstore

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class IngestionPipeline:
    """
    Orchestrates the document ingestion pipeline.
    
    Coordinates loading, chunking, embedding, and storing of documents
    while managing incremental updates through the manifest.
    
    Supports PDF and Markdown files in the configured directory.
    """
    
    def __init__(
        self,
        docs_dir: Path | None = None,
        vectorstore: FAISSVectorStore | None = None,
        manifest_manager: ManifestManager | None = None,
    ) -> None:
        """
        Initialize the ingestion pipeline.
        
        Args:
            docs_dir: Directory containing document files (PDF, Markdown)
            vectorstore: FAISS vector store instance
            manifest_manager: Manifest manager instance
        """
        # Check DOCS_DIR first, fall back to PDF_DIR for backward compatibility
        default_docs_dir = os.getenv("DOCS_DIR") or os.getenv("PDF_DIR", "./data/docs")
        self.docs_dir = docs_dir or Path(default_docs_dir)
        self.docs_dir = Path(self.docs_dir)
        
        self.vectorstore = vectorstore or get_vectorstore()
        self.manifest = manifest_manager or get_manifest_manager()
        
        self.loader = DocumentLoader()
        self.chunker = DocumentChunker()
        
        logger.info(f"Ingestion pipeline initialized for: {self.docs_dir}")
    
    def find_supported_files(self) -> list[Path]:
        """
        Find all supported files in the configured directory (including subdirs).
        
        Returns:
            List of file paths (PDF and Markdown files)
        """
        if not self.docs_dir.exists():
            logger.warning(f"Documents directory does not exist: {self.docs_dir}")
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            return []
        
        all_files = []
        for ext in SUPPORTED_EXTENSIONS:
            # Use **/ pattern to search subdirectories
            all_files.extend(self.docs_dir.glob(f"**/*{ext}"))
        
        logger.info(
            f"Found {len(all_files)} supported files "
            f"({', '.join(SUPPORTED_EXTENSIONS)}) in {self.docs_dir}"
        )
        return all_files
    
    def run(self, rebuild: bool = False) -> dict[str, Any]:
        """
        Run the ingestion pipeline.
        
        Args:
            rebuild: If True, rebuild the entire index from scratch
            
        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "total_files": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "files_removed": 0,
            "total_chunks": 0,
            "errors": [],
        }
        
        # Find all supported files
        doc_files = self.find_supported_files()
        stats["total_files"] = len(doc_files)
        
        if not doc_files:
            logger.warning("No supported files found to ingest")
            return stats
        
        # Handle rebuild mode
        if rebuild:
            logger.info("Rebuild mode: clearing existing index and manifest")
            self.vectorstore.delete_index()
            self.manifest.clear()
        
        # Determine which files need indexing
        files_to_index = self.manifest.get_files_to_index(doc_files)
        stats["files_skipped"] = len(doc_files) - len(files_to_index)
        
        # Handle removed files
        removed_files = self.manifest.get_removed_files(doc_files)
        stats["files_removed"] = len(removed_files)
        
        for filepath in removed_files:
            self.manifest.remove_document(filepath)
        
        # Process files that need indexing
        if files_to_index:
            logger.info(f"Processing {len(files_to_index)} files...")
            
            all_chunks = []
            
            for doc_file in files_to_index:
                try:
                    # Load document (PDF or Markdown)
                    documents = self.loader.load_file(doc_file)
                    
                    if not documents:
                        logger.warning(f"No content extracted from: {doc_file.name}")
                        stats["errors"].append(f"No content: {doc_file.name}")
                        continue
                    
                    # Chunk documents
                    chunks = self.chunker.chunk_documents(documents)
                    
                    if not chunks:
                        logger.warning(f"No chunks created from: {doc_file.name}")
                        stats["errors"].append(f"No chunks: {doc_file.name}")
                        continue
                    
                    # Track statistics
                    all_chunks.extend(chunks)
                    stats["files_processed"] += 1
                    stats["total_chunks"] += len(chunks)
                    
                    # Update manifest
                    page_count = len(documents)
                    self.manifest.add_document(
                        doc_file,
                        chunk_count=len(chunks),
                        page_count=page_count,
                    )
                    
                    logger.info(
                        f"Processed {doc_file.name}: "
                        f"{page_count} pages/sections, {len(chunks)} chunks"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing {doc_file.name}: {e}")
                    stats["errors"].append(f"Error: {doc_file.name} - {str(e)}")
            
            # Add all chunks to vector store
            if all_chunks:
                logger.info(f"Adding {len(all_chunks)} chunks to vector store...")
                
                if rebuild or not self.vectorstore.exists():
                    self.vectorstore.create_from_documents(all_chunks)
                else:
                    self.vectorstore.add_documents(all_chunks)
                
                # Save vector store and manifest
                self.vectorstore.save()
                self.manifest.save()
                
                logger.info("Ingestion complete!")
        else:
            logger.info("No files need indexing")
            # Still save manifest to record any removed files
            self.manifest.save()
        
        return stats
    
    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the index.
        
        Returns:
            Dictionary with status information
        """
        return {
            "docs_directory": str(self.docs_dir),
            "supported_extensions": list(SUPPORTED_EXTENSIONS),
            "files_count": len(self.find_supported_files()),
            "indexed_documents": self.manifest.document_count,
            "total_chunks": self.manifest.total_chunks,
            "index_exists": self.vectorstore.exists(),
        }


def run_ingestion(
    docs_dir: str | Path | None = None,
    rebuild: bool = False,
) -> dict[str, Any]:
    """
    Run document ingestion.
    
    Convenience function for programmatic use.
    
    Args:
        docs_dir: Directory containing document files (PDF, Markdown)
        rebuild: Whether to rebuild from scratch
        
    Returns:
        Ingestion statistics
    """
    docs_path = Path(docs_dir) if docs_dir else None
    pipeline = IngestionPipeline(docs_dir=docs_path)
    return pipeline.run(rebuild=rebuild)


def main() -> None:
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="RAG AI Agent - Document Ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest documents from the default directory
  rag-ingest

  # Ingest documents from a custom directory
  rag-ingest --docs-dir ./my-docs

  # Rebuild the entire index from scratch
  rag-ingest --rebuild

  # Show current index status
  rag-ingest --status

Supported file types: .pdf, .md, .markdown
        """,
    )
    
    parser.add_argument(
        "--docs-dir",
        type=str,
        default=None,
        help="Directory containing document files (default: ./data/pdfs)",
    )
    
    # Keep backward compatibility
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default=None,
        help="[DEPRECATED] Use --docs-dir instead",
    )
    
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the entire index from scratch",
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current index status and exit",
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Validate OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error(
            "OpenAI API key not configured. "
            "Set OPENAI_API_KEY environment variable."
        )
        sys.exit(1)
    
    # Handle backward compatibility for --pdf-dir
    docs_dir = args.docs_dir or args.pdf_dir
    if args.pdf_dir:
        logger.warning("--pdf-dir is deprecated, use --docs-dir instead")
    
    # Create pipeline
    docs_path = Path(docs_dir) if docs_dir else None
    pipeline = IngestionPipeline(docs_dir=docs_path)
    
    # Handle status command
    if args.status:
        status = pipeline.get_status()
        print("\n=== RAG AI Agent - Index Status ===")
        print(f"Documents Directory:    {status['docs_directory']}")
        print(f"Supported Extensions:   {', '.join(status['supported_extensions'])}")
        print(f"Files Found:            {status['files_count']}")
        print(f"Indexed Documents:      {status['indexed_documents']}")
        print(f"Total Chunks:           {status['total_chunks']}")
        print(f"Index Exists:           {status['index_exists']}")
        print("===================================\n")
        return
    
    # Run ingestion
    print("\n=== RAG AI Agent - Document Ingestion ===")
    print(f"Documents Directory: {pipeline.docs_dir}")
    print(f"Supported Types:     {', '.join(SUPPORTED_EXTENSIONS)}")
    print(f"Rebuild Mode:        {args.rebuild}")
    print("==========================================\n")
    
    try:
        stats = pipeline.run(rebuild=args.rebuild)
        
        print("\n=== Ingestion Results ===")
        print(f"Total Files:     {stats['total_files']}")
        print(f"Files Processed: {stats['files_processed']}")
        print(f"Files Skipped:   {stats['files_skipped']}")
        print(f"Files Removed:   {stats['files_removed']}")
        print(f"Total Chunks:    {stats['total_chunks']}")
        
        if stats["errors"]:
            print(f"Errors:          {len(stats['errors'])}")
            for error in stats["errors"]:
                print(f"  - {error}")
        
        print("=========================\n")
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

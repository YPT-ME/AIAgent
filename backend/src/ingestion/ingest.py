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
from src.ingestion.loaders import DocumentLoader, SUPPORTED_EXTENSIONS, is_indexable
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
        
        all_files = sorted(
            p for p in self.docs_dir.rglob("*") if p.is_file() and is_indexable(p)
        )

        # Wiki pages are addressed by file name alone, so a repeated name is ambiguous
        names = [p.stem for p in all_files if p.suffix.lower() != ".pdf"]
        repeated = sorted({n for n in names if names.count(n) > 1})
        if repeated:
            logger.warning(f"Markdown page names used by more than one file: {', '.join(repeated)}")
        
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
            raise RuntimeError(
                "No supported files found; check the documents mount. The previous index was kept"
            )
        
        # A manifest without its index would skip every file and leave the agent with nothing
        if not rebuild and self.manifest.document_count and not self.vectorstore.exists():
            logger.warning("Manifest lists documents but the FAISS index is missing: rebuilding")
            rebuild = True

        # Handle rebuild mode. The index and manifest on disk stay in place until the
        # new ones are saved, so a failed rebuild keeps the previous knowledge base.
        if rebuild:
            logger.info("Rebuild mode: building a new index and manifest")
            self.vectorstore.reset()
            self.manifest.reset()

        # Determine which files need indexing
        files_to_index = self.manifest.get_files_to_index(doc_files)
        current_sources = {str(p.absolute()) for p in doc_files}

        # Older builds left chunks of previous file versions, and of files missing from the
        # manifest; files whose chunk count disagrees with the manifest are indexed again
        orphans = False
        if not rebuild:
            counts = self.vectorstore.chunk_counts()
            legacy_sources = self.vectorstore.legacy_sources()
            entries = self.manifest.load().documents
            pending = set(files_to_index)
            out_of_sync = [
                p for p in doc_files
                if p not in pending
                and str(p.absolute()) in entries
                and (counts[str(p.absolute())] != entries[str(p.absolute())].chunk_count
                     or str(p.absolute()) in legacy_sources)
            ]
            if out_of_sync:
                logger.warning(f"{len(out_of_sync)} indexed files disagree with the manifest: re-indexing")
                files_to_index += out_of_sync
            orphans = any(source not in current_sources and source not in entries for source in counts)

        stats["files_skipped"] = len(doc_files) - len(files_to_index)

        # Handle removed files
        removed_files = self.manifest.get_removed_files(doc_files)
        stats["files_removed"] = len(removed_files)

        if not files_to_index and not removed_files and not orphans:
            logger.info("No files need indexing")
            return stats

        logger.info(f"Processing {len(files_to_index)} files...")

        all_chunks = []
        indexed: list[tuple[Path, str, int, int]] = []

        for doc_file in files_to_index:
            try:
                file_hash = self.manifest.compute_file_hash(doc_file)

                # Load document (PDF or Markdown)
                documents = self.loader.load_file(doc_file, root=self.docs_dir)

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

                # Stable per-file ids: a repeated add of the same chunk fails instead of duplicating
                file_key = str(doc_file.absolute())
                for idx, chunk in enumerate(chunks):
                    chunk.metadata["chunk_id"] = f"{file_key}#{idx}"

                all_chunks.extend(chunks)
                indexed.append((doc_file, file_hash, len(chunks), len(documents)))

                logger.info(
                    f"Processed {doc_file.name}: "
                    f"{len(documents)} pages/sections, {len(chunks)} chunks"
                )

            except Exception as e:
                logger.error(f"Error processing {doc_file.name}: {e}")
                stats["errors"].append(f"Error: {doc_file.name} - {str(e)}")

        if stats["errors"] or (rebuild and not all_chunks):
            raise RuntimeError(
                "Ingestion failed; the previous index and manifest were kept: "
                + "; ".join(stats["errors"])
            )

        # Old chunks of changed (or now unreadable) and removed files leave the index too
        stale_sources = [str(p.absolute()) for p in files_to_index] + [str(p) for p in removed_files]
        self.vectorstore.replace_documents(stale_sources, all_chunks, current_sources)

        # Persist the index first; the manifest records only what the saved index contains
        if self.vectorstore.is_loaded and not self.vectorstore.save():
            raise RuntimeError("FAISS index could not be saved; the manifest was not updated")

        for filepath in removed_files:
            self.manifest.remove_document(filepath)
        for doc_file in files_to_index:
            self.manifest.remove_document(doc_file)
        for doc_file, file_hash, chunk_count, page_count in indexed:
            self.manifest.add_document(
                doc_file,
                chunk_count=chunk_count,
                page_count=page_count,
                file_hash=file_hash,
            )
            stats["files_processed"] += 1
            stats["total_chunks"] += chunk_count

        if not self.manifest.save():
            raise RuntimeError(
                "Manifest could not be saved; the next run re-indexes the affected files"
            )

        logger.info("Ingestion complete!")
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
        help="Directory containing document files (default: $DOCS_DIR, else $PDF_DIR, else ./data/docs)",
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

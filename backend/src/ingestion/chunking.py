"""
RAG AI Agent - Text Chunking Strategies

This module provides text chunking functionality to split documents
into smaller, semantically meaningful chunks for embedding.
"""

import logging
import os
import re
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from llama_index.core import Document as LlamaDocument

from src.ingestion.markdown import markdown_lines

logger = logging.getLogger(__name__)

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_TABLE = re.compile(r"^\|[^\n]+\|\s*\n\|[ :|\-]+\|[ \t]*\n(?:^\|[^\n]*\|[ \t]*(?:\n|$))+", re.MULTILINE)


def split_markdown_sections(text: str) -> list[tuple[list[str], str]]:
    """
    Split Markdown into (heading path, text) sections, keeping each heading line in its text.

    Lines starting with "#" inside fenced code blocks are not headings.
    """
    sections: list[tuple[list[str], str]] = []
    path: list[str] = []
    headings: list[tuple[int, str]] = []
    lines: list[str] = []
    for line, in_code in markdown_lines(text):
        if not in_code:
            heading = _HEADING.match(line)
            if heading:
                if "".join(lines).strip():
                    sections.append((path, "".join(lines)))
                lines = []
                level = len(heading.group(1))
                headings = [(n, title) for n, title in headings if n < level]
                headings.append((level, heading.group(2)))
                path = [title for _, title in headings]
        lines.append(line)

    if "".join(lines).strip():
        sections.append((path, "".join(lines)))
    return sections


def _common_path(paths: list[list[str]]) -> list[str]:
    common = paths[0]
    for path in paths[1:]:
        size = 0
        while size < min(len(common), len(path)) and common[size] == path[size]:
            size += 1
        common = common[:size]
    return common


class DocumentChunker:
    """
    Chunks documents using LangChain's RecursiveCharacterTextSplitter.
    
    Converts LlamaIndex documents to LangChain documents and splits them
    into smaller chunks while preserving metadata.
    """
    
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        """
        Initialize the document chunker.
        
        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size if chunk_size is not None else int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else int(os.getenv("CHUNK_OVERLAP", "200"))
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True,
        )
        
        logger.info(
            f"Initialized chunker with size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )
    
    def llama_to_langchain_doc(
        self, 
        llama_doc: LlamaDocument
    ) -> LangChainDocument:
        """
        Convert a LlamaIndex Document to a LangChain Document.
        
        Args:
            llama_doc: LlamaIndex document
            
        Returns:
            LangChain document with preserved metadata
        """
        return LangChainDocument(
            page_content=llama_doc.text,
            metadata=llama_doc.metadata or {},
        )
    
    def chunk_document(
        self, 
        doc: LlamaDocument | LangChainDocument
    ) -> list[LangChainDocument]:
        """
        Split a single document into chunks.
        
        Args:
            doc: Document to chunk (LlamaIndex or LangChain)
            
        Returns:
            List of chunked LangChain documents
        """
        # Convert LlamaIndex doc if necessary
        if isinstance(doc, LlamaDocument):
            langchain_doc = self.llama_to_langchain_doc(doc)
        else:
            langchain_doc = doc

        # Split the document
        if langchain_doc.metadata.get("file_type") == "markdown":
            chunks = self._chunk_markdown(langchain_doc)
        else:
            chunks = self.splitter.split_documents([langchain_doc])
            metadata = langchain_doc.metadata
            if metadata.get("file_type") == "pdf":
                label = f"[{metadata.get('file_name')}, page {metadata.get('page_number')}]"
                for chunk in chunks:
                    chunk.page_content = f"{label}\n{chunk.page_content}"

        # Add chunk index to metadata
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["total_chunks"] = len(chunks)

        return chunks

    def _chunk_markdown(self, doc: LangChainDocument) -> list[LangChainDocument]:
        """
        Split Markdown along its sections, so every chunk keeps the page and heading path it
        came from. Small neighbouring sections are merged; long ones are split further.
        """
        page = doc.metadata.get("wiki_page") or doc.metadata.get("file_name", "")
        chunks: list[LangChainDocument] = []

        def emit(path: list[str], text: str) -> None:
            section = " > ".join(path)
            label = f"[{page} | {section}]" if section else f"[{page}]"
            pieces = self._split_markdown_text(text)
            for piece in pieces:
                if piece.strip():
                    chunks.append(
                        LangChainDocument(
                            page_content=f"{label}\n{piece.strip()}",
                            metadata={**doc.metadata, "section": section},
                        )
                    )

        buffer: list[tuple[list[str], str]] = []
        for path, text in split_markdown_sections(doc.page_content):
            if buffer and sum(len(t) for _, t in buffer) + len(text) > self.chunk_size:
                emit(_common_path([p for p, _ in buffer]), "".join(t for _, t in buffer))
                buffer = []
            buffer.append((path, text))
        if buffer:
            emit(_common_path([p for p, _ in buffer]), "".join(t for _, t in buffer))

        return chunks

    def _split_markdown_text(self, text: str) -> list[str]:
        """Repeat column names in long table fragments; keep ordinary splitting elsewhere."""
        if len(text) <= self.chunk_size:
            return [text]
        pieces = []
        offset = 0
        # Fenced examples are not live Markdown tables.
        visible = "".join(line if not code else re.sub(r"[^\r\n]", " ", line)
                          for line, code in markdown_lines(text))
        for table in _TABLE.finditer(visible):
            pieces.extend(self.splitter.split_text(text[offset:table.start()]))
            rows = text[table.start():table.end()].splitlines(keepends=True)
            header = "".join(rows[:2])
            batch = header
            for row in rows[2:]:
                if len(batch) + len(row) > self.chunk_size and batch != header:
                    pieces.append(batch)
                    batch = header
                batch += row
            if batch != header:
                pieces.append(batch)
            offset = table.end()
        pieces.extend(self.splitter.split_text(text[offset:]))
        return pieces
    
    def chunk_documents(
        self, 
        docs: list[LlamaDocument | LangChainDocument]
    ) -> list[LangChainDocument]:
        """
        Chunk multiple documents.
        
        Args:
            docs: List of documents to chunk
            
        Returns:
            List of all chunked documents
        """
        all_chunks = []
        
        for doc in docs:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(docs)} documents")
        return all_chunks

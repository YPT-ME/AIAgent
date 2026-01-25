"""
RAG AI Agent - Text Chunking Strategies

This module provides text chunking functionality to split documents
into smaller, semantically meaningful chunks for embedding.
"""

import logging
import os
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from llama_index.core import Document as LlamaDocument

logger = logging.getLogger(__name__)


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
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", "200"))
        
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
        chunks = self.splitter.split_documents([langchain_doc])
        
        # Add chunk index to metadata
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["total_chunks"] = len(chunks)
        
        return chunks
    
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

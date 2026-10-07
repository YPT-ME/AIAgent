"""
RAG AI Agent - Configuration Management

This module handles all application configuration using Pydantic Settings.
Configuration is loaded from environment variables with sensible defaults.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by environment variables or a .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Vector Store Configuration
    faiss_index_path: str = "./storage/faiss"
    manifest_path: str = "./storage/manifest.json"
    
    # Document Ingestion Configuration
    pdf_dir: str = "./data/pdfs"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # RAG Configuration
    top_k: int = 5
    
    # Logging Configuration
    log_level: str = "INFO"
    
    # Analytics Configuration (ClickHouse)
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "analytics"
    clickhouse_password: str = "analytics_password"
    clickhouse_db: str = "analytics"
    analytics_enabled: bool = True
    
    @property
    def faiss_index_dir(self) -> Path:
        """Get FAISS index directory as Path object."""
        return Path(self.faiss_index_path)
    
    @property
    def manifest_file(self) -> Path:
        """Get manifest file path as Path object."""
        return Path(self.manifest_path)
    
    @property
    def pdf_directory(self) -> Path:
        """Get PDF directory as Path object."""
        return Path(self.pdf_dir)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance (cached)
    """
    return Settings()


# Global settings instance
settings = get_settings()

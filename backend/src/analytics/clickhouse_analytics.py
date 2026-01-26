"""
ClickHouse Analytics - High-Performance Chat Metrics Tracking

This module provides analytics tracking for the RAG AI Agent using ClickHouse,
a high-performance columnar database designed for analytics workloads.

Features:
- Real-time chat metrics tracking
- High-throughput ingestion (millions of events per second)
- Efficient aggregation queries
- Thread-safe async operations
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import clickhouse_connect
from clickhouse_connect.driver.client import Client

logger = logging.getLogger(__name__)


class ClickHouseAnalytics:
    """
    Analytics tracker using ClickHouse for high-performance metrics storage.
    
    This class provides methods to track various chat-related events and metrics
    with support for high-volume ingestion.
    """
    
    def __init__(
        self,
        host: str = "clickhouse",
        port: int = 8123,
        username: str = "analytics",
        password: str = "analytics_password",
        database: str = "analytics",
    ):
        """
        Initialize ClickHouse analytics client.
        
        Args:
            host: ClickHouse host
            port: ClickHouse HTTP port
            username: ClickHouse username
            password: ClickHouse password
            database: ClickHouse database name
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self._client: Optional[Client] = None
        self._lock = asyncio.Lock()
        
    def _get_client(self) -> Client:
        """Get or create ClickHouse client."""
        if self._client is None:
            try:
                self._client = clickhouse_connect.get_client(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    database=self.database,
                )
                logger.info(f"Connected to ClickHouse at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to ClickHouse: {e}")
                raise
        return self._client
    
    async def track_message(
        self,
        thread_id: str,
        user_id: Optional[str],
        message_type: str,  # 'user' or 'assistant'
        content: str,
        tokens: int = 0,
        duration_ms: Optional[int] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track a chat message event.
        
        Args:
            thread_id: Conversation thread identifier
            user_id: User identifier (None for anonymous)
            message_type: Type of message ('user' or 'assistant')
            content: Message content
            tokens: Number of tokens used
            duration_ms: Response duration in milliseconds
            model: AI model used (for assistant messages)
            metadata: Additional metadata
        """
        try:
            client = self._get_client()
            
            data = [[
                datetime.now(),
                thread_id,
                user_id or 'anonymous',
                message_type,
                len(content),
                tokens,
                duration_ms or 0,
                model or '',
                str(metadata or {})
            ]]
            
            client.insert(
                'chat_messages',
                data,
                column_names=[
                    'timestamp', 'thread_id', 'user_id', 'message_type',
                    'content_length', 'tokens', 'duration_ms', 'model', 'metadata'
                ]
            )
            
            logger.debug(f"Tracked message for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to track message: {e}")
    
    async def track_tool_call(
        self,
        thread_id: str,
        tool_name: str,
        duration_ms: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Track a tool/function call event.
        
        Args:
            thread_id: Conversation thread identifier
            tool_name: Name of the tool/function called
            duration_ms: Execution duration in milliseconds
            success: Whether the call was successful
            error_message: Error message if failed
        """
        try:
            client = self._get_client()
            
            data = [[
                datetime.now(),
                thread_id,
                tool_name,
                duration_ms,
                success,
                error_message or ''
            ]]
            
            client.insert(
                'tool_calls',
                data,
                column_names=[
                    'timestamp', 'thread_id', 'tool_name',
                    'duration_ms', 'success', 'error_message'
                ]
            )
            
            logger.debug(f"Tracked tool call: {tool_name}")
            
        except Exception as e:
            logger.error(f"Failed to track tool call: {e}")
    
    async def track_session(
        self,
        thread_id: str,
        user_id: Optional[str],
        session_start: datetime,
        session_end: Optional[datetime] = None,
        message_count: int = 0,
        total_tokens: int = 0,
    ) -> None:
        """
        Track a chat session.
        
        Args:
            thread_id: Conversation thread identifier
            user_id: User identifier (None for anonymous)
            session_start: Session start time
            session_end: Session end time
            message_count: Total messages in session
            total_tokens: Total tokens used in session
        """
        try:
            client = self._get_client()
            
            duration_ms = 0
            if session_end:
                duration_ms = int((session_end - session_start).total_seconds() * 1000)
            
            data = [[
                session_start,
                thread_id,
                user_id or 'anonymous',
                duration_ms,
                message_count,
                total_tokens
            ]]
            
            client.insert(
                'chat_sessions',
                data,
                column_names=[
                    'timestamp', 'thread_id', 'user_id',
                    'duration_ms', 'message_count', 'total_tokens'
                ]
            )
            
            logger.debug(f"Tracked session for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to track session: {e}")
    
    async def track_error(
        self,
        thread_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
    ) -> None:
        """
        Track an error event.
        
        Args:
            thread_id: Conversation thread identifier
            error_type: Type/category of error
            error_message: Error message
            stack_trace: Stack trace if available
        """
        try:
            client = self._get_client()
            
            data = [[
                datetime.now(),
                thread_id,
                error_type,
                error_message,
                stack_trace or ''
            ]]
            
            client.insert(
                'chat_errors',
                data,
                column_names=[
                    'timestamp', 'thread_id', 'error_type',
                    'error_message', 'stack_trace'
                ]
            )
            
            logger.debug(f"Tracked error for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Failed to track error: {e}")
    
    def get_metrics_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get summary metrics for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary containing summary metrics
        """
        try:
            client = self._get_client()
            
            # Total messages
            total_messages = client.query(
                f"""
                SELECT count() as total
                FROM chat_messages
                WHERE timestamp >= now() - INTERVAL {hours} HOUR
                """
            ).first_row[0]
            
            # Average response time
            avg_response_time_result = client.query(
                f"""
                SELECT avg(duration_ms) as avg_duration
                FROM chat_messages
                WHERE message_type = 'assistant'
                  AND timestamp >= now() - INTERVAL {hours} HOUR
                  AND duration_ms > 0
                """
            ).first_row[0]
            
            # Handle NaN, None, or infinity
            if avg_response_time_result is None or not (0 <= avg_response_time_result < float('inf')):
                avg_response_time = 0.0
            else:
                avg_response_time = float(avg_response_time_result)
            
            # Total sessions
            total_sessions = client.query(
                f"""
                SELECT count() as total
                FROM chat_sessions
                WHERE timestamp >= now() - INTERVAL {hours} HOUR
                """
            ).first_row[0]
            
            # Total tokens used
            total_tokens = client.query(
                f"""
                SELECT sum(tokens) as total
                FROM chat_messages
                WHERE timestamp >= now() - INTERVAL {hours} HOUR
                """
            ).first_row[0] or 0
            
            # Error rate
            total_errors = client.query(
                f"""
                SELECT count() as total
                FROM chat_errors
                WHERE timestamp >= now() - INTERVAL {hours} HOUR
                """
            ).first_row[0]
            
            return {
                "total_messages": int(total_messages),
                "avg_response_time_ms": round(avg_response_time, 2),
                "total_sessions": int(total_sessions),
                "total_tokens": int(total_tokens),
                "total_errors": int(total_errors),
                "hours": hours,
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    def close(self) -> None:
        """Close ClickHouse connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("ClickHouse connection closed")


# Global analytics instance
_analytics_instance: Optional[ClickHouseAnalytics] = None


def get_analytics() -> ClickHouseAnalytics:
    """
    Get or create the global analytics instance.
    
    Returns:
        ClickHouseAnalytics instance
    """
    global _analytics_instance
    
    if _analytics_instance is None:
        import os
        _analytics_instance = ClickHouseAnalytics(
            host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            username=os.getenv("CLICKHOUSE_USER", "analytics"),
            password=os.getenv("CLICKHOUSE_PASSWORD", "analytics_password"),
            database=os.getenv("CLICKHOUSE_DB", "analytics"),
        )
    
    return _analytics_instance

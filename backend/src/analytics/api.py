"""
FastAPI endpoints for analytics and monitoring.

Provides REST API access to chat metrics and analytics data.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .clickhouse_analytics import get_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


class TrackMessageRequest(BaseModel):
    """Request model for tracking messages."""
    thread_id: str
    user_id: str
    message_type: str
    content_length: int
    tokens: int
    duration_ms: int = 0
    model: str = ""


class TrackToolCallRequest(BaseModel):
    """Request model for tracking tool calls."""
    thread_id: str
    tool_name: str
    duration_ms: int
    success: bool
    error_message: Optional[str] = None


class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary."""
    total_messages: int
    avg_response_time_ms: float
    total_sessions: int
    total_tokens: int
    total_errors: int
    hours: int


@router.get("/health", status_code=200)
async def health_check():
    """Check if analytics service is healthy."""
    try:
        analytics = get_analytics()
        analytics._get_client()  # Test connection
        return {"status": "healthy", "service": "analytics"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")


@router.post("/track/message", status_code=201)
async def track_message(request: TrackMessageRequest):
    """
    Track a chat message event.
    
    This endpoint is called by the LangGraph agent to track messages.
    """
    try:
        analytics = get_analytics()
        await analytics.track_message(
            thread_id=request.thread_id,
            user_id=request.user_id,
            message_type=request.message_type,
            content="",  # We only track length, not actual content for privacy
            tokens=request.tokens,
            duration_ms=request.duration_ms,
            model=request.model,
        )
        return {"status": "success", "message": "Message tracked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track/tool", status_code=201)
async def track_tool_call(request: TrackToolCallRequest):
    """
    Track a tool/function call event.
    
    This endpoint is called by the LangGraph agent to track tool usage.
    """
    try:
        analytics = get_analytics()
        await analytics.track_tool_call(
            thread_id=request.thread_id,
            tool_name=request.tool_name,
            duration_ms=request.duration_ms,
            success=request.success,
            error_message=request.error_message,
        )
        return {"status": "success", "message": "Tool call tracked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back (1-168)")
):
    """
    Get summary metrics for the specified time period.
    
    Args:
        hours: Number of hours to look back (default: 24, max: 168/7 days)
        
    Returns:
        Summary metrics including message count, response times, sessions, etc.
    """
    try:
        analytics = get_analytics()
        metrics = analytics.get_metrics_summary(hours=hours)
        
        if not metrics:
            raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/response-time")
async def get_response_time_percentiles():
    """
    Get response time percentiles for the last 24 hours.
    
    Returns:
        Dictionary with p50, p90, p95, p99 response times in milliseconds
    """
    try:
        analytics = get_analytics()
        client = analytics._get_client()
        
        result = client.query("""
            SELECT
                quantile(0.50)(duration_ms) AS p50_ms,
                quantile(0.90)(duration_ms) AS p90_ms,
                quantile(0.95)(duration_ms) AS p95_ms,
                quantile(0.99)(duration_ms) AS p99_ms
            FROM chat_messages
            WHERE message_type = 'assistant'
              AND timestamp >= now() - INTERVAL 24 HOUR
              AND duration_ms > 0
        """)
        
        row = result.first_row
        
        return {
            "p50_ms": round(row[0], 2),
            "p90_ms": round(row[1], 2),
            "p95_ms": round(row[2], 2),
            "p99_ms": round(row[3], 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/top-users")
async def get_top_users(
    limit: int = Query(10, ge=1, le=100, description="Number of users to return")
):
    """
    Get top users by activity in the last 7 days.
    
    Args:
        limit: Maximum number of users to return (default: 10, max: 100)
        
    Returns:
        List of top users with their activity metrics
    """
    try:
        analytics = get_analytics()
        client = analytics._get_client()
        
        result = client.query(f"""
            SELECT
                user_id,
                count() AS session_count,
                sum(message_count) AS total_messages,
                sum(total_tokens) AS total_tokens
            FROM chat_sessions
            WHERE timestamp >= now() - INTERVAL 7 DAY
            GROUP BY user_id
            ORDER BY session_count DESC
            LIMIT {limit}
        """)
        
        users = []
        for row in result.result_rows:
            users.append({
                "user_id": row[0],
                "session_count": row[1],
                "total_messages": row[2],
                "total_tokens": row[3],
            })
        
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/popular-tools")
async def get_popular_tools():
    """
    Get most used tools in the last 24 hours.
    
    Returns:
        List of tools with usage statistics
    """
    try:
        analytics = get_analytics()
        client = analytics._get_client()
        
        result = client.query("""
            SELECT
                tool_name,
                count() AS call_count,
                countIf(success) AS success_count,
                round(avg(duration_ms), 2) AS avg_duration_ms,
                round(countIf(success) * 100.0 / count(), 2) AS success_rate
            FROM tool_calls
            WHERE timestamp >= now() - INTERVAL 24 HOUR
            GROUP BY tool_name
            ORDER BY call_count DESC
        """)
        
        tools = []
        for row in result.result_rows:
            tools.append({
                "tool_name": row[0],
                "call_count": row[1],
                "success_count": row[2],
                "avg_duration_ms": row[3],
                "success_rate": row[4],
            })
        
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/recent-errors")
async def get_recent_errors(
    limit: int = Query(50, ge=1, le=100, description="Number of errors to return")
):
    """
    Get recent errors from the last 24 hours.
    
    Args:
        limit: Maximum number of errors to return (default: 50, max: 100)
        
    Returns:
        List of recent errors
    """
    try:
        analytics = get_analytics()
        client = analytics._get_client()
        
        result = client.query(f"""
            SELECT
                timestamp,
                thread_id,
                error_type,
                error_message
            FROM chat_errors
            WHERE timestamp >= now() - INTERVAL 24 HOUR
            ORDER BY timestamp DESC
            LIMIT {limit}
        """)
        
        errors = []
        for row in result.result_rows:
            errors.append({
                "timestamp": row[0].isoformat(),
                "thread_id": row[1],
                "error_type": row[2],
                "error_message": row[3],
            })
        
        return {"errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

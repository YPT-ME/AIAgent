"""
Custom LangGraph Server with Analytics API

This module extends the LangGraph Server to include analytics endpoints.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import analytics API
from analytics.api import router as analytics_router


def create_custom_server() -> FastAPI:
    """
    Create a custom FastAPI server with analytics endpoints.
    
    This will be used alongside LangGraph Server.
    """
    app = FastAPI(
        title="RAG Agent Analytics API",
        description="Analytics and monitoring endpoints for RAG Agent",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include analytics router
    app.include_router(analytics_router)
    
    @app.get("/")
    async def root():
        return {
            "service": "RAG Agent Analytics API",
            "status": "running",
            "endpoints": {
                "analytics": "/analytics",
                "health": "/analytics/health",
                "metrics": "/analytics/metrics/summary",
            }
        }
    
    return app


# Create the FastAPI app
app = create_custom_server()


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("ANALYTICS_PORT", "8080"))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )

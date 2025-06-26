"""
Main FastAPI application for the RAG server.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from .services.db import engine
from .models.chat_summary import Base as ChatSummaryBase

from .config import API_HOST, API_PORT, CORS_ORIGINS, LOG_LEVEL, LOG_FORMAT
from .api.routes import router

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RAG Server",
    description="A RAG (Retrieval-Augmented Generation) server for academic papers",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "rag-server"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RAG Server API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(ChatSummaryBase.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    ) 
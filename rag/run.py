#!/usr/bin/env python3
"""
Entry point for the RAG server.
"""
import uvicorn
from src.config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    ) 
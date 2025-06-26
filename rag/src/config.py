"""
Configuration settings for the RAG server.
"""
import os
from typing import Optional

# LLM Configuration
LLM_URL = os.getenv("LLM_URL", "http://100.115.151.29:8080/completion")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_N_PREDICT = int(os.getenv("LLM_N_PREDICT", "300"))
LLM_STOP_TOKENS = ["\nUser:", "\nAssistant:"]

# ChromaDB Configuration
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "papers_v2")

# Dual Collection Configuration
FINE_CHUNKS_COLLECTION = os.getenv("FINE_CHUNKS_COLLECTION", "fine_chunks")
COARSE_CHUNKS_COLLECTION = os.getenv("COARSE_CHUNKS_COLLECTION", "coarse_chunks")

# Fine Chunks Configuration (for citation suggestion and sentence-level similarity)
FINE_CHUNK_MIN_CHARS = int(os.getenv("FINE_CHUNK_MIN_CHARS", "300"))
FINE_CHUNK_MAX_CHARS = int(os.getenv("FINE_CHUNK_MAX_CHARS", "500"))
FINE_CHUNK_MIN_SENTENCES = int(os.getenv("FINE_CHUNK_MIN_SENTENCES", "1"))
FINE_CHUNK_MAX_SENTENCES = int(os.getenv("FINE_CHUNK_MAX_SENTENCES", "3"))

# Coarse Chunks Configuration (for question answering and summarization)
COARSE_CHUNK_MIN_CHARS = int(os.getenv("COARSE_CHUNK_MIN_CHARS", "1000"))
COARSE_CHUNK_MAX_CHARS = int(os.getenv("COARSE_CHUNK_MAX_CHARS", "1500"))
COARSE_CHUNK_MIN_TOKENS = int(os.getenv("COARSE_CHUNK_MIN_TOKENS", "300"))
COARSE_CHUNK_MAX_TOKENS = int(os.getenv("COARSE_CHUNK_MAX_TOKENS", "512"))

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/e5-base-v2")

# Text Processing Configuration
MAX_CHUNK_LENGTH = int(os.getenv("MAX_CHUNK_LENGTH", "1500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_CHARS_PER_PARAGRAPH = int(os.getenv("MAX_CHARS_PER_PARAGRAPH", "1500"))

# Advanced Chunking Configuration
ADVANCED_CHUNKING_ENABLED = os.getenv("ADVANCED_CHUNKING_ENABLED", "true").lower() == "true"
MIN_TOKENS_PER_CHUNK = int(os.getenv("MIN_TOKENS_PER_CHUNK", "300"))
MAX_TOKENS_PER_CHUNK = int(os.getenv("MAX_TOKENS_PER_CHUNK", "800"))
OVERLAP_TOKENS = int(os.getenv("OVERLAP_TOKENS", "100"))
TOKENIZER_MODEL = os.getenv("TOKENIZER_MODEL", "gpt-3.5-turbo")

# File Storage Configuration
PAPERS_DIR = os.getenv("PAPERS_DIR", "papers")
TEMP_DIR = os.getenv("TEMP_DIR", "temp")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Agent Configuration
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
AGENT_N_PREDICT = int(os.getenv("AGENT_N_PREDICT", "300"))

# Search Configuration
DEFAULT_SEARCH_K = int(os.getenv("DEFAULT_SEARCH_K", "5")) 
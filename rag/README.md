# RAG Server - Reorganized Structure

A well-organized RAG (Retrieval-Augmented Generation) server for academic papers with proper separation of concerns and modular architecture.

## 🏗️ Project Structure

```
rag/
├── src/                          # Main source code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Centralized configuration
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   └── routes.py             # All API route handlers
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   └── api_models.py         # Pydantic models for API
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── pdf_service.py        # PDF downloading and processing
│   │   ├── vector_store_service.py # Vector database operations
│   │   └── agent_service.py      # LangChain agent functionality
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── text_processing.py    # Text cleaning and chunking
│       └── llm_client.py         # LLM interaction utilities
├── papers/                       # Downloaded PDF papers
├── chroma_db/                    # ChromaDB vector database
├── run.py                        # Application entry point
├── requirements_new.txt          # Dependencies
└── README_NEW.md                 # This file
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements_new.txt
   ```

2. **Run the server:**
   ```bash
   python run.py
   ```

3. **Access the API:**
   - API Documentation: http://localhost:8001/docs
   - Health Check: http://localhost:8001/health
   - Root: http://localhost:8001/

## 📋 API Endpoints

### Core RAG Endpoints
- `POST /api/v1/embed` - Generate embeddings for text
- `POST /api/v1/ingest_paper` - Ingest a paper from URL or arXiv ID
- `POST /api/v1/search` - Search the knowledge base
- `POST /api/v1/chat` - Chat with RAG system
- `POST /api/v1/chat_stream` - Streaming chat

### Agent Endpoints
- `POST /api/v1/agent` - Process agent requests
- `POST /api/v1/agent/inline` - Inline chat with document context
- `POST /api/v1/agent/tool_execution` - Execute agent tools
- `GET /api/v1/agent/tools` - List available tools

### Management Endpoints
- `GET /api/v1/count_chunks` - Count chunks in database
- `GET /api/v1/list_chunks` - List all chunks
- `POST /api/v1/delete_all_chunks` - Delete all chunks
- `POST /api/v1/clean_chunks` - Clean short chunks

## 🔧 Configuration

All configuration is centralized in `src/config.py` and can be overridden with environment variables:

```bash
# LLM Configuration
export LLM_URL="http://your-llm-server:8080/completion"
export LLM_TEMPERATURE="0.7"
export LLM_N_PREDICT="300"

# API Configuration
export API_HOST="0.0.0.0"
export API_PORT="8001"

# Vector Store Configuration
export CHROMA_DB_DIR="chroma_db"
export COLLECTION_NAME="papers"

# Text Processing
export MAX_CHUNK_LENGTH="1500"
export CHUNK_OVERLAP="200"
```

## 🏛️ Architecture

### Layers

1. **API Layer** (`src/api/`)
   - Route handlers
   - Request/response validation
   - Error handling

2. **Service Layer** (`src/services/`)
   - Business logic
   - External service integration
   - Data processing

3. **Model Layer** (`src/models/`)
   - Pydantic models
   - Data validation
   - API schemas

4. **Utility Layer** (`src/utils/`)
   - Helper functions
   - Text processing
   - LLM client utilities

### Key Services

- **PDFService**: Handles paper downloading and text extraction
- **VectorStoreService**: Manages ChromaDB operations and embeddings
- **AgentService**: Orchestrates LangChain agent functionality

## 🔄 Migration from Old Structure

The old files have been reorganized as follows:

| Old File | New Location | Purpose |
|----------|--------------|---------|
| `main.py` | `src/main.py` + `src/api/routes.py` | Split into app setup and routes |
| `agent.py` | `src/services/agent_service.py` | Agent business logic |
| `chat.py` | `src/utils/llm_client.py` | LLM utilities |
| `pdf_downloader.py` | `src/services/pdf_service.py` | PDF processing |
| `pdf_text_extractor.py` | `src/services/pdf_service.py` | Integrated into PDF service |
| `embedder_preparation.py` | `src/utils/text_processing.py` | Text processing utilities |

## 🧪 Testing

Run the test script:
```bash
python test_agent.py
```

## 📝 Usage Examples

### Ingest a Paper
```bash
curl -X POST "http://localhost:8001/api/v1/ingest_paper" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/abs/1706.03762"}'
```

### Search Knowledge Base
```bash
curl -X POST "http://localhost:8001/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "attention mechanism", "k": 5}'
```

### Chat with RAG
```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the transformer architecture?"}'
```

## 🎯 Benefits of New Structure

1. **Separation of Concerns**: Each module has a single responsibility
2. **Maintainability**: Easy to locate and modify specific functionality
3. **Testability**: Services can be tested independently
4. **Scalability**: Easy to add new features without affecting existing code
5. **Configuration Management**: Centralized configuration with environment variable support
6. **Code Reusability**: Utilities and services can be reused across the application
7. **Clear Dependencies**: Explicit import structure shows dependencies clearly

## 🚨 Important Notes

- The old files are still present but should be considered deprecated
- Use `run.py` as the new entry point
- All API endpoints now have the `/api/v1/` prefix
- Configuration is now centralized and environment-variable driven
- The vector database and papers directories are preserved 
"""
API models for the RAG server.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Embedding Models
class EmbedRequest(BaseModel):
    text: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]

# Paper Ingest Models
class PaperIngestRequest(BaseModel):
    url: str  # can be full URL or arXiv ID
    user_id: Optional[str] = None  # optional user scoping

class PaperIngestResponse(BaseModel):
    success: bool
    message: str
    paper_id: Optional[str] = None
    chunks_added: Optional[int] = None

# Search Models
class SearchRequest(BaseModel):
    query: str
    k: int = 5  # number of top similar chunks to return

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

# Chat Models
class ChatTurn(BaseModel):
    user: str
    assistant: str

class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    chat_history: List[ChatTurn] = []
    chat_id: Optional[str] = None  # Add chat_id for session tracking

class ChatResponse(BaseModel):
    answer: str

# Agent Models
class AgentRequest(BaseModel):
    user_input: str
    chat_history: Optional[List[Dict[str, str]]] = []
    user_id: Optional[str] = None

class InlineChatRequest(BaseModel):
    user_input: str
    selected_text: str
    document_context: str
    document_path: Optional[str] = None
    line_number: Optional[int] = None
    chat_history: Optional[List[Dict[str, str]]] = []

class AgentResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    tool_calls: Optional[List] = None
    error: Optional[str] = None

class ToolExecutionRequest(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any]

class ToolExecutionResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None

# Management Models
class CollectionStatsResponse(BaseModel):
    total_documents: int
    collection_name: str
    db_path: str

class ChunkInfo(BaseModel):
    text: str
    metadata: Dict[str, Any]
    text_length: int
    embedding_preview: List[float]

class ListChunksResponse(BaseModel):
    chunks: List[ChunkInfo]

class CleanChunksResponse(BaseModel):
    success: bool
    chunks_deleted: int
    message: str

# Chat Summary Models
class ChatSummaryCreateRequest(BaseModel):
    summary: Optional[str] = ""

class ChatSummaryResponse(BaseModel):
    id: int
    summary: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ChatSummaryUpdateRequest(BaseModel):
    new_message: str

# Citation Suggestion Models
class CitationSuggestionRequest(BaseModel):
    text: str

class PaperInfo(BaseModel):
    title: str
    authors: str
    citation_key: str
    bibtex: str
    match_snippet: Optional[str] = None

class CitationSuggestionResponse(BaseModel):
    match: bool
    score: float
    paper: Optional[PaperInfo] = None 
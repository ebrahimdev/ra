"""
API routes for the RAG server.
"""
import logging
import re
import json
import requests
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import tiktoken
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
import arxiv

from ..models.api_models import (
    EmbedRequest, EmbedResponse,
    PaperIngestRequest, PaperIngestResponse,
    SearchRequest, SearchResponse,
    ChatRequest, ChatResponse,
    AgentRequest, AgentResponse,
    InlineChatRequest, ToolExecutionRequest, ToolExecutionResponse,
    CollectionStatsResponse, ListChunksResponse, CleanChunksResponse,
    ChatSummaryCreateRequest, ChatSummaryResponse, ChatSummaryUpdateRequest,
    CitationSuggestionRequest, CitationSuggestionResponse
)
from ..services.pdf_service import PDFService
from ..services.vector_store_service import VectorStoreService
from ..utils.llm_client import call_llm, create_semantic_query, build_prompt, build_rag_prompt
from ..utils.text_processing import extract_arxiv_id
from ..config import DEFAULT_SEARCH_K
from ..services.db import get_db
from ..services.chat_summary_service import ChatSummaryService
from ..services.agent_service import AgentService

logger = logging.getLogger(__name__)

# Initialize services
pdf_service = PDFService()
vector_store = VectorStoreService()
agent_service = AgentService(vector_store=vector_store)

# Create router
router = APIRouter()

# === Embedding Routes ===
@router.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    """Generate embeddings for a list of texts."""
    try:
        embeddings = vector_store.embed_texts(req.text)
        return EmbedResponse(embeddings=embeddings)
    except Exception as e:
        logger.error(f"Error in embed endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Paper Ingest Routes ===
@router.post("/ingest_paper", response_model=PaperIngestResponse)
async def ingest_paper(req: PaperIngestRequest):
    """Ingest a paper from URL or arXiv ID."""
    try:
        logger.info(f"=== Ingest Paper Request ===")
        logger.info(f"Request data: {req.dict()}")
        logger.info(f"url: {req.url}")
        logger.info(f"user_id: {req.user_id}")
        
        # Accept both arXiv IDs and URLs
        input_str = req.url
        
        # Check if it's an arXiv ID or URL
        if "arxiv.org" in input_str or re.match(r'\d{4}\.\d{4,5}', input_str):
            # Extract arXiv ID
            arxiv_id = extract_arxiv_id(input_str)
            logger.info(f"Extracted arXiv ID: {arxiv_id}")
            
            try:
                # Download and extract text
                text = pdf_service.download_arxiv_pdf_text(arxiv_id)

                # Fetch arXiv metadata
                client = arxiv.Client()
                search = arxiv.Search(id_list=[arxiv_id])
                results = list(client.results(search))
                if results:
                    paper = results[0]
                    title = paper.title
                    authors = [a.name for a in paper.authors]
                    year = paper.published.year if paper.published else None
                else:
                    title = None
                    authors = None
                    year = None

                # Prepare metadata
                paper_metadata = {
                    'source': 'arxiv',
                    'arxiv_id': arxiv_id,
                    'user_id': req.user_id,
                    'ingest_timestamp': datetime.now().isoformat(),
                    'title': title,
                    'authors': authors,
                    'year': year
                }
                
            except ValueError as e:
                # Handle arXiv-specific errors
                logger.error(f"ArXiv download error: {str(e)}")
                raise HTTPException(status_code=404, detail=f"ArXiv paper not found: {str(e)}")
            except Exception as e:
                # Handle other errors
                logger.error(f"Unexpected error downloading arXiv paper: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to download arXiv paper: {str(e)}")
            
        else:
            # Generic URL download
            pdf_path = pdf_service.download_paper(input_str)
            if not pdf_path:
                raise HTTPException(status_code=400, detail="Failed to download paper")
            
            # Extract text from downloaded PDF
            text = pdf_service.extract_text_from_pdf(pdf_path)
            if not text:
                raise HTTPException(status_code=400, detail="Failed to extract text from PDF")
            
            # Prepare metadata
            paper_metadata = {
                'source': 'url',
                'url': input_str,
                'user_id': req.user_id,
                'ingest_timestamp': datetime.now().isoformat()
            }
        
        # Ingest into vector store
        success = vector_store.ingest_paper_text(text, paper_metadata)
        
        if success:
            return PaperIngestResponse(
                success=True,
                message="Paper successfully ingested",
                paper_id=arxiv_id if "arxiv_id" in paper_metadata else None,
                chunks_added=len(text.split()) // 1500  # Approximate chunk count
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to ingest paper into vector store")
            
    except Exception as e:
        logger.error(f"Error in ingest_paper endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Search Routes ===
@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """Search for similar texts in the vector store."""
    try:
        # Create a semantic query using LLM before embedding
        semantic_query = create_semantic_query(req.query)
        logger.info(f"Original query: {req.query}")
        logger.info(f"Semantic query: {semantic_query}")
        
        # Search both collections and combine results
        results = vector_store.search_both_collections(semantic_query, k_fine=3, k_coarse=2)
        
        return SearchResponse(results=results["results"])
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/fine", response_model=SearchResponse)
async def search_fine_chunks(req: SearchRequest):
    """Search for similar texts in the fine chunks collection (for citation suggestion)."""
    try:
        semantic_query = create_semantic_query(req.query)
        logger.info(f"Fine search query: {semantic_query}")
        
        results = vector_store.search_collection(semantic_query, req.k, "fine")
        
        return SearchResponse(results=results["results"])
        
    except Exception as e:
        logger.error(f"Error in fine search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/coarse", response_model=SearchResponse)
async def search_coarse_chunks(req: SearchRequest):
    """Search for similar texts in the coarse chunks collection (for question answering)."""
    try:
        semantic_query = create_semantic_query(req.query)
        logger.info(f"Coarse search query: {semantic_query}")
        
        results = vector_store.search_collection(semantic_query, req.k, "coarse")
        
        return SearchResponse(results=results["results"])
        
    except Exception as e:
        logger.error(f"Error in coarse search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest-citation", response_model=CitationSuggestionResponse)
async def suggest_citation(req: CitationSuggestionRequest):
    """Suggest a citation for the given text by finding the most similar paper chunk."""
    try:
        logger.info(f"=== Citation Suggestion Request ===")
        logger.info(f"Text: {req.text[:100]}...")  # Log first 100 chars
        
        # Search for similar chunks in fine collection (top 3)
        search_results = vector_store.search_collection(req.text, k=3, collection_name="fine")
        
        if not search_results["results"]:
            return CitationSuggestionResponse(
                match=False,
                score=0.0,
                paper=None
            )
        
        # Get the result with highest similarity score
        best_match = max(search_results["results"], key=lambda x: x["similarity_score"])
        print(f"Best match content: {best_match['text']}")
        top_score = best_match["similarity_score"]
        
        # Check if similarity score is above threshold (0.8)
        if top_score >= 0.8:
            metadata = best_match["metadata"]
            
            # Extract and truncate the matching text snippet
            match_text = best_match["text"]
            if len(match_text) > 300:
                # Truncate to ~300 characters, trying to break at a word boundary
                truncated = match_text[:300]
                last_space = truncated.rfind(' ')
                if last_space > 250:  # Only use word boundary if it's not too far back
                    match_snippet = truncated[:last_space] + "..."
                else:
                    match_snippet = truncated + "..."
            else:
                match_snippet = match_text
            
            # Extract paper information from metadata
            paper_info = {
                "title": metadata.get("title", "Unknown Title"),
                "authors": metadata.get("authors", "Unknown Authors"),
                "citation_key": metadata.get("citation_key", "unknown"),
                "bibtex": metadata.get("bibtex", ""),
                "match_snippet": match_snippet
            }
            
            return CitationSuggestionResponse(
                match=True,
                score=top_score,
                paper=paper_info
            )
        else:
            return CitationSuggestionResponse(
                match=False,
                score=top_score,
                paper=None
            )
        
    except Exception as e:
        logger.error(f"Error in suggest_citation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Chat Routes ===
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Chat with the RAG system."""
    try:
        # If this is the first message in chat, include RAG context
        if not req.chat_history:
            # Search for relevant context
            semantic_query = create_semantic_query(req.query)
            search_results = vector_store.search(semantic_query, DEFAULT_SEARCH_K)
            
            if search_results["results"]:
                # Build context from search results
                context_chunks = "\n\n".join([result["text"] for result in search_results["results"]])
                context = f"Relevant context:\n{context_chunks}\n\n"
            else:
                context = "No relevant context found.\n\n"
        else:
            context = ""
        
        # Convert chat history to the format expected by build_prompt
        history = [{"user": turn.user, "assistant": turn.assistant} for turn in req.chat_history]
        
        # Build the prompt
        system_message = "You are a helpful research assistant. Use the provided context to answer questions accurately and comprehensively."
        prompt = build_prompt(system_message, context, history, req.query)
        
        # Get response from LLM
        response = call_llm(prompt)
        
        return ChatResponse(answer=response)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    """Streaming chat endpoint."""
    try:
        logger.info(f"=== Chat Stream Request ===")
        logger.info(f"Query: {req.query}")
        logger.info(f"User ID: {req.user_id}")
        logger.info(f"Chat ID: {req.chat_id}")
        
        # Search for relevant context using coarse chunks for question answering
        semantic_query = create_semantic_query(req.query)
        search_results = vector_store.search_collection(semantic_query, DEFAULT_SEARCH_K, "coarse")
        
        # Build context
        if search_results["results"]:
            context_chunks = "\n\n".join([result["text"] for result in search_results["results"]])
            context = f"Relevant context:\n{context_chunks}\n\n"
        else:
            context = "No relevant context found.\n\n"
        
        # Convert chat history
        history = [{"user": turn.user, "assistant": turn.assistant} for turn in req.chat_history]
        
        # Build the prompt
        system_message = "You are a helpful research assistant. Use the provided context to answer questions accurately and comprehensively."
        prompt = build_prompt(system_message, context, history, req.query)
        
        def event_stream():
            # Always yield chat_id as the first event
            if req.chat_id:
                yield f"data: {json.dumps({'chat_id': req.chat_id})}\n\n"
            
            # Stream the LLM response
            response = requests.post(
                "http://100.115.151.29:8080/completion",
                json={
                    "prompt": prompt,
                    "temperature": 0.7,
                    "n_predict": 300,
                    "stream": True,
                    "stop": ["\nUser:", "\nAssistant:"]
                },
                stream=True
            )

            for line in response.iter_lines():
                if line:
                    try:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            json_str = line_str[6:]
                            chunk = json.loads(json_str)
                            content = chunk.get("content", "")
                            done = chunk.get("stop", False)
                            yield f"data: {json.dumps({'content': content, 'done': done})}\n\n"
                        else:
                            chunk = json.loads(line_str)
                            content = chunk.get("content", "")
                            done = chunk.get("stop", False)
                            yield f"data: {json.dumps({'content': content, 'done': done})}\n\n"
                    except Exception as e:
                        error_data = json.dumps({'error': str(e), 'done': True})
                        yield f"data: {error_data}\n\n"
            
            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        
        return StreamingResponse(event_stream(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"Error in chat_stream endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Agent Routes ===
@router.post("/agent", response_model=AgentResponse)
async def process_agent_request(req: AgentRequest):
    """Process agent requests."""
    try:
        result = await agent_service.process_request(req.user_input, req.chat_history)
        return AgentResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in agent endpoint: {str(e)}")
        return AgentResponse(success=False, error=str(e))

@router.post("/agent/inline", response_model=AgentResponse)
async def process_inline_chat_request(req: InlineChatRequest):
    """Process inline chat requests."""
    try:
        result = await agent_service.process_inline_request(
            req.user_input, req.selected_text, req.document_context,
            req.document_path, req.line_number, req.chat_history
        )
        return AgentResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in inline agent endpoint: {str(e)}")
        return AgentResponse(success=False, error=str(e))

@router.post("/agent/tool_execution", response_model=ToolExecutionResponse)
async def handle_tool_execution(req: ToolExecutionRequest):
    """Handle tool execution requests."""
    try:
        result = agent_service.handle_tool_execution(req.tool_name, req.tool_input)
        return ToolExecutionResponse(success=True, result=result)
        
    except Exception as e:
        logger.error(f"Error in tool execution endpoint: {str(e)}")
        return ToolExecutionResponse(success=False, error=str(e))

@router.get("/agent/tools")
async def list_available_tools():
    """List available tools."""
    try:
        tools = agent_service.get_available_tools()
        return {"tools": tools}
        
    except Exception as e:
        logger.error(f"Error in tools endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Management Routes ===
@router.get("/count_chunks")
async def count_chunks():
    """Get the number of chunks in both collections."""
    try:
        stats = vector_store.get_collection_stats()
        return {
            "fine_chunks_count": stats.get("fine_chunks_count", 0),
            "coarse_chunks_count": stats.get("coarse_chunks_count", 0),
            "total_documents": stats.get("total_documents", 0)
        }
    except Exception as e:
        logger.error(f"Error in count_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list_chunks", response_model=ListChunksResponse)
async def list_chunks():
    """List all chunks from both collections."""
    try:
        fine_chunks = vector_store.list_chunks_from_collection("fine")
        coarse_chunks = vector_store.list_chunks_from_collection("coarse")
        all_chunks = fine_chunks + coarse_chunks
        return ListChunksResponse(chunks=all_chunks)
    except Exception as e:
        logger.error(f"Error in list_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list_chunks/fine", response_model=ListChunksResponse)
async def list_fine_chunks():
    """List all chunks from the fine chunks collection."""
    try:
        chunks = vector_store.list_chunks_from_collection("fine")
        return ListChunksResponse(chunks=chunks)
    except Exception as e:
        logger.error(f"Error in list_fine_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list_chunks/coarse", response_model=ListChunksResponse)
async def list_coarse_chunks():
    """List all chunks from the coarse chunks collection."""
    try:
        chunks = vector_store.list_chunks_from_collection("coarse")
        return ListChunksResponse(chunks=chunks)
    except Exception as e:
        logger.error(f"Error in list_coarse_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_all_chunks")
async def delete_all_chunks():
    """Delete all chunks from both collections."""
    try:
        success = vector_store.delete_all_chunks()
        if success:
            return {"message": "All chunks deleted successfully from both collections"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete chunks")
    except Exception as e:
        logger.error(f"Error in delete_all_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clean_chunks", response_model=CleanChunksResponse)
async def clean_chunks():
    """Clean chunks by removing those that are too short from both collections."""
    try:
        # This would need to be implemented in VectorStoreService
        # For now, return a placeholder response
        return CleanChunksResponse(
            success=True,
            chunks_deleted=0,
            message="Clean chunks functionality to be implemented for dual collections"
        )
    except Exception as e:
        logger.error(f"Error in clean_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Utility Routes ===
def count_tokens(text: str, model_name="gpt-3.5-turbo"):
    """Count tokens in text."""
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

# === Chat Summary Endpoints ===
@router.post("/chats", response_model=ChatSummaryResponse)
async def create_chat_summary(req: ChatSummaryCreateRequest, db: AsyncSession = Depends(get_db)):
    chat = await ChatSummaryService.create_summary(db, summary=req.summary)
    return ChatSummaryResponse(
        id=chat.id,
        summary=chat.summary,
        created_at=str(chat.created_at),
        updated_at=str(chat.updated_at)
    )

@router.get("/chats/{chat_id}/summary", response_model=ChatSummaryResponse)
async def get_chat_summary(chat_id: int, db: AsyncSession = Depends(get_db)):
    try:
        chat = await ChatSummaryService.get_summary(db, chat_id)
        return ChatSummaryResponse(
            id=chat.id,
            summary=chat.summary,
            created_at=str(chat.created_at),
            updated_at=str(chat.updated_at)
        )
    except NoResultFound:
        return {"error": f"ChatSummary with id {chat_id} not found"}

@router.post("/chats/{chat_id}/summary", response_model=ChatSummaryResponse)
async def update_chat_summary(chat_id: int, req: ChatSummaryUpdateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    chat = await ChatSummaryService.update_summary(db, chat_id, req.new_message, background_tasks)
    return ChatSummaryResponse(
        id=chat.id,
        summary=chat.summary,
        created_at=str(chat.created_at),
        updated_at=str(chat.updated_at)
    ) 
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from sentence_transformers import SentenceTransformer
import arxiv
import tempfile
import pdfminer.high_level
import re
import chromadb
from chromadb.config import Settings
import os
import numpy as np
from chat import ChatRequest, ChatResponse, build_prompt, build_rag_prompt, call_llm, count_tokens, llm_stream_generator, create_semantic_query
from fastapi.middleware.cors import CORSMiddleware
import requests
from fastapi.responses import StreamingResponse
import logging
from pdf_downloader import PDFDownloader
from pdf_text_extractor import extract_text_from_pdf
from embedder_preparation import chunk_text_with_overlap

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat_stream")

def chunk_by_paragraphs(text: str, max_chars=1500):
    """
    Split text into chunks by paragraphs, with preprocessing to clean the text.
    """
    # Preprocess text to remove common PDF artifacts
    text = preprocess_text(text)
    
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:  # Skip empty paragraphs
            continue
            
        if len(current) + len(p) < max_chars:
            if current:
                current += "\n\n" + p
            else:
                current = p
        else:
            if current.strip():  # Just check if not empty
                chunks.append(current.strip())
            current = p
    
    # Add the last chunk if it exists
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def preprocess_text(text: str) -> str:
    """
    Clean and preprocess text extracted from PDF to remove common artifacts.
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple line breaks to double
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    
    # Remove common PDF artifacts
    text = re.sub(r'^\s*Page \d+\s*$', '', text, flags=re.MULTILINE)  # Page numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)  # Standalone numbers
    
    # Remove headers and footers that appear on every page
    text = re.sub(r'^\s*[A-Z\s]{3,}\s*$', '', text, flags=re.MULTILINE)  # ALL CAPS headers
    
    # Remove common non-content lines
    text = re.sub(r'^\s*(Abstract|Introduction|Conclusion|References|Bibliography)\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove fragmented single-character lines
    text = re.sub(r'^\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)  # Single letters
    text = re.sub(r'^\s*[a-zA-Z]\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)  # Two letters
    text = re.sub(r'^\s*[a-zA-Z]\s*[a-zA-Z]\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)  # Three letters
    
    # Remove arXiv identifiers and URLs
    text = re.sub(r'https?://arxiv\.org/abs/\d+\.\d+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\d{4}\.\d{4,5}', '', text, flags=re.MULTILINE)
    
    # Remove fragmented content patterns
    text = re.sub(r'^\s*[a-zA-Z]\s*\n\s*[a-zA-Z]\s*\n\s*[a-zA-Z]', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # Clean up mathematical expressions that might be broken across lines
    text = re.sub(r'([A-Za-z])\s*\n\s*([+\-*/=])', r'\1\2', text)  # Fix broken math expressions
    
    # Remove excessive punctuation
    text = re.sub(r'[.!?]{3,}', '...', text)  # Multiple punctuation to ellipsis
    
    # Normalize quotes and dashes
    text = text.replace('"', '"').replace('"', '"')  # Smart quotes to regular
    text = text.replace('–', '-').replace('—', '-')  # Em/en dashes to regular
    
    # Remove lines with too many isolated characters
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        words = line.split()
        isolated_chars = len(re.findall(r'\b[a-zA-Z]\b', line))
        if len(words) > 0 and isolated_chars <= len(words) * 0.4:
            cleaned_lines.append(line)
        elif len(words) == 0:
            continue  # Skip empty lines
        elif isolated_chars <= 2:  # Allow a few isolated chars
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Final cleanup: remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple line breaks to double
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    
    return text.strip()

# Create a persistent directory for ChromaDB
CHROMA_DB_DIR = "chroma_db"
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="papers")

# === Setup FastAPI ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with ["vscode-webview://<your-extension-id>"] for tighter control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
model = SentenceTransformer("intfloat/e5-base-v2")

# === Models ===
class EmbedRequest(BaseModel):
    text: list[str]

class PaperIngestRequest(BaseModel):
    url: str  # can be full URL or arXiv ID
    user_id: Optional[str] = None  # optional user scoping

class SearchRequest(BaseModel):
    query: str
    k: int = 5  # number of top similar chunks to return

# === Utils ===
def extract_arxiv_id(input_str: str) -> str:
    match = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', input_str)
    if not match:
        raise ValueError("Invalid arXiv ID or URL.")
    return match.group(1)

def download_arxiv_pdf_text(arxiv_id: str) -> str:
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(search.results())
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Download PDF with explicit filename
            pdf_path = f"{tmpdir}/{paper.get_short_id()}.pdf"
            paper.download_pdf(dirpath=tmpdir, filename=f"{paper.get_short_id()}.pdf")
            
            # Verify file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"Failed to download PDF for {arxiv_id}")
                
            text = pdfminer.high_level.extract_text(pdf_path)
            if not text.strip():
                raise ValueError(f"Extracted text is empty for {arxiv_id}")
                
            return text
        except Exception as e:
            raise Exception(f"Failed to process arXiv paper {arxiv_id}: {str(e)}")


# === Routes ===
@app.post("/embed")
async def embed(req: EmbedRequest):
    embeddings = model.encode(req.text, convert_to_numpy=True).tolist()
    return {"embeddings": embeddings}

@app.post("/ingest_paper")
async def ingest_paper(req: PaperIngestRequest):
    try:
        # Log the incoming request
        logger.info(f"=== Ingest Paper Request ===")
        logger.info(f"Request data: {req.dict()}")
        logger.info(f"url: {req.url}")
        logger.info(f"user_id: {req.user_id}")
        
        # Accept both arXiv IDs and URLs
        input_str = req.url
        user_id = req.user_id
        user_prefix = f"{user_id}:" if user_id else "global:"
        
        logger.info(f"Input string: {input_str}")
        logger.info(f"User prefix: {user_prefix}")

        # Extract arXiv ID if possible (for deduplication)
        try:
            arxiv_id = extract_arxiv_id(input_str)
            logger.info(f"Extracted arXiv ID: {arxiv_id}")
        except Exception as e:
            arxiv_id = None
            logger.warning(f"Could not extract arXiv ID: {str(e)}")

        # Check if any chunks for this arxiv_id and user_id already exist
        if arxiv_id:
            logger.info(f"Checking for existing chunks with arxiv_id: {arxiv_id}, user_id: {user_id}")
            existing = collection.get(
                where={"$and": [
                    {"arxiv_id": {"$eq": arxiv_id}},
                    {"user_id": {"$eq": user_id}}
                ]},
                include=["metadatas"]
            )
            logger.info(f"Found {len(existing['metadatas'])} existing chunks")
            if existing["metadatas"]:
                logger.info("Skipping ingestion - paper already exists for this user")
                return {
                    "status": "skipped",
                    "reason": "Already ingested for this user",
                    "chunks_present": len(existing["metadatas"])
                }

        # Download the PDF using the downloader module
        logger.info("Starting PDF download...")
        downloader = PDFDownloader()
        pdf_path = downloader.download_paper(input_str)
        logger.info(f"PDF download result: {pdf_path}")
        if not pdf_path:
            logger.error("Failed to download PDF")
            return {"status": "error", "error": "Failed to download PDF."}

        # Extract text from the PDF
        logger.info("Starting text extraction...")
        text = extract_text_from_pdf(pdf_path)
        logger.info(f"Text extraction result: {len(text) if text else 0} characters")
        if not text:
            logger.error("Failed to extract text from PDF")
            return {"status": "error", "error": "Failed to extract text from PDF."}

        # Chunk the text using the chunker module
        logger.info("Starting text chunking...")
        chunks = chunk_text_with_overlap(text, max_length=1500, overlap=200)
        logger.info(f"Chunking result: {len(chunks)} chunks")
        if not chunks:
            logger.error("No chunks produced from text")
            return {"status": "error", "error": "No chunks produced from text."}

        # Embed and store in vector DB
        logger.info("Starting embedding and storage...")
        embeddings = model.encode(chunks, convert_to_numpy=True).tolist()
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{user_prefix}{arxiv_id or os.path.basename(pdf_path)}-{i}"
            collection.add(
                documents=[chunk],
                embeddings=[embeddings[i]],
                ids=[chunk_id],
                metadatas=[{
                    "source_url": input_str,
                    "arxiv_id": arxiv_id or os.path.basename(pdf_path),
                    "user_id": user_id
                }]
            )
        
        logger.info(f"Successfully stored {len(chunks)} chunks in vector DB")
        logger.info("=== Ingest Paper Request Complete ===")

        return {
            "status": "success",
            "chunks_added": len(chunks),
            "source": input_str,
            "arxiv_id": arxiv_id or os.path.basename(pdf_path)
        }
    except Exception as e:
        logger.error(f"Error in ingest_paper: {str(e)}")
        return {"status": "error", "error": str(e)}
    
@app.get("/list_chunks")
def list_chunks():
    # Get all chunk data
    results = collection.get(include=["documents", "metadatas", "embeddings"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    embeds = results.get("embeddings", [])
    ids = results.get("ids", []) if "ids" in results else [None]*len(docs)

    def summarize_text(text, n_words=8):
        words = text.split()
        if len(words) > n_words:
            return " ".join(words[:n_words]) + " ..."
        return text

    def to_serializable_embedding(emb):
        if emb is None:
            return []
        if isinstance(emb, np.ndarray):
            return emb[:5].tolist()
        return list(emb)[:5]

    summary = []
    for i, (doc, meta, emb) in enumerate(zip(docs, metas, embeds)):
        summary.append({
            "id": ids[i] if i < len(ids) else None,
            "embedding_start": to_serializable_embedding(emb),
            "text_start": summarize_text(str(doc)),
            "metadata": dict(meta) if isinstance(meta, dict) else meta
        })
    return summary

@app.get("/count_chunks")
def count_chunks():
    total = collection.count()
    return {"total_chunks": total}

@app.post("/delete_all_chunks")
def delete_all_chunks():
    # Get count before deletion
    count_before = collection.count()
    # Use a where clause that matches all documents by checking for non-empty arxiv_id
    collection.delete(where={"arxiv_id": {"$ne": ""}})
    return {"status": "success", "deleted": count_before}

@app.post("/clean_chunks")
def clean_chunks():
    """
    Clean up existing chunks by removing low-quality content and re-processing with improved filtering.
    """
    try:
        # Get all existing chunks
        results = collection.get(include=["documents", "metadatas", "embeddings", "ids"])
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])
        embeds = results.get("embeddings", [])
        ids = results.get("ids", [])
        
        if not docs:
            return {"status": "success", "message": "No chunks to clean", "kept": 0, "removed": 0}
        
        # Since we removed is_useful_chunk, just return the current state
        return {
            "status": "success", 
            "message": "No filtering applied - all chunks kept",
            "kept": len(docs), 
            "removed": 0,
            "total_processed": len(docs)
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/search")
def search(req: SearchRequest):
    # Create a semantic query using LLM before embedding
    semantic_query = create_semantic_query(req.query)
    print(f"Original query: {req.query}")
    print(f"Semantic query: {semantic_query}")
    
    # Create embedding for the semantic query
    query_embedding = model.encode(semantic_query, convert_to_numpy=True).tolist()
    
    # Search the collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=req.k,
        include=["documents", "metadatas", "distances"]
    )
    
    # Format the results
    search_results = []
    for i in range(len(results["documents"][0])):
        search_results.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity score
        })
    
    return {
        "query": req.query,
        "semantic_query": semantic_query,
        "results": search_results
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # If this is the first message in chat, include RAG context
    rag_context = ""
    if not req.chat_history:
        from main import collection, model  # avoid circular import

        # Create a semantic query using LLM before embedding
        semantic_query = create_semantic_query(req.query)
        print(f"Original query: {req.query}")
        print(f"Semantic query: {semantic_query}")

        query_embedding = model.encode(semantic_query, convert_to_numpy=True).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["documents", "metadatas"]
        )

        rag_chunks = []
        for i, text in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            source = meta.get("source_url", "Unknown")
            rag_chunks.append(f"Context {i+1} ({source}):\n{text}")
        rag_context = "\n\n".join(rag_chunks)

    # Use the new RAG prompt format
    if rag_context:
        prompt = build_rag_prompt("", rag_context, req.query)
    else:
        # Fallback to original format for non-RAG responses
        system = (
            "You are a research assistant that helps users write and improve LaTeX papers. "
            "You answer clearly, rewrite sections, and recommend citations based on saved research papers."
        )
        prompt = build_prompt(system, "", req.chat_history, req.query)
    
    prompt = prompt.strip()
    tokens_used = count_tokens(prompt)
    print(f"[DEBUG] Tokens used in prompt: {tokens_used}")
    reply = call_llm(prompt)

    return ChatResponse(answer=reply)


@app.post("/chat_stream")
def chat_stream(req: ChatRequest):
    # Log the incoming request data
    logger.info(f"Received /chat_stream request: {req.dict()}")

    # If chat_id is not provided, create a new chat via Rails API
    chat_id = req.chat_id
    if not chat_id:
        try:
            create_chat_url = "http://localhost:3000/api/chats"
            headers = {"Content-Type": "application/json"}
            resp = requests.post(create_chat_url, json={}, headers=headers, timeout=5)
            if 200 <= resp.status_code < 300:
                try:
                    chat_id = resp.json().get("chat_id") or resp.json().get("id")
                    logger.info(f"Generated new chat_id from Rails: {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to parse chat_id from Rails response: {str(e)} | Response text: {resp.text}")
                    chat_id = None
            else:
                logger.error(f"Failed to create chat: {resp.status_code} {resp.text}")
                chat_id = None
        except Exception as e:
            logger.error(f"Error creating chat: {str(e)}")
            chat_id = None
    logger.info(f"chat_id used: {chat_id}")

    # Always build RAG context for every request
    from main import collection, model
    # Create a semantic query using LLM before embedding
    semantic_query = create_semantic_query(req.query)
    logger.info(f"Original query: {req.query}")
    logger.info(f"Semantic query: {semantic_query}")
    
    query_embedding = model.encode(semantic_query, convert_to_numpy=True).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["documents", "metadatas"]
    )
    rag_chunks = [
        f"Context {i+1} ({meta.get('source_url', 'N/A')}):\n{text}"
        for i, (text, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]))
    ]
    rag_context = "\n\n".join(rag_chunks)

    # Fetch chat summary from Rails server if chat_id is provided
    chat_summary = ""
    if chat_id:
        try:
            summary_url = f"http://localhost:3000/api/chats/{chat_id}/summary"
            payload = {"new_message": f"user: {req.query}"}
            headers = {"Content-Type": "application/json"}
            resp = requests.post(summary_url, json=payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                chat_summary = resp.json().get("summary", "")
            else:
                chat_summary = f"[Failed to fetch summary: {resp.status_code}]"
        except Exception as e:
            chat_summary = f"[Error fetching summary: {str(e)}]"

    # Add chat summary to the prompt if available
    summary_section = f"\n\nChat Summary:\n{chat_summary}" if chat_summary else ""

    # Use the new RAG prompt format
    prompt = build_rag_prompt(chat_summary, rag_context, req.query)

    # Log the full prompt sent to the LLM
    logger.info("\n====== PROMPT SENT TO LLM ======\n%s\n===============================\n" % prompt)

    # Custom generator to yield chat_id first, then stream content
    def event_stream():
        # Always yield chat_id as the first event
        yield f"data: {{\"chat_id\": \"{chat_id}\"}}\n\n"
        # Then yield the LLM stream as usual
        for chunk in llm_stream_generator(prompt):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")

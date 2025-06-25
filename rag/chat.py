from typing import List, Optional
from pydantic import BaseModel
import requests
import tiktoken
from fastapi.responses import StreamingResponse
import json

def llm_stream_generator(prompt: str):
    response = requests.post(
        LLM_URL,
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


def stream_llm_response(prompt: str):
    return StreamingResponse(llm_stream_generator(prompt), media_type="text/event-stream")


def count_tokens(text: str, model_name="gpt-3.5-turbo"):
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


LLM_URL = "http://100.115.151.29:8080/completion"  # Update if needed

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

def build_prompt(system: str, context: str, history: List[ChatTurn], query: str):
    # context can now include RAG context and/or a chat summary section
    history_text = "\n\n".join(
        f"{turn.user}\n{turn.assistant}" for turn in history[-2:]
    )

    return f"""{system}\n\n{context}\n\n{history_text}\n\n{query}\n"""

def build_rag_prompt(chat_summary: str, context_chunks: str, user_question: str) -> str:
    """
    Build a prompt for RAG-based responses using the new format, without explicit role labels.
    """
    return f"""You are a research assistant that helps users understand and analyze academic papers.

You are provided with:
- A brief summary of the prior conversation.
- A set of retrieved excerpts from a vector database of academic paper content.

Your task is to use only the retrieved context to answer the latest user question in a formal academic tone. Do not rely on prior conversation unless it is reflected in the retrieved context. If the context is insufficient to answer the question, state that explicitly.

---

Chat Summary:
{chat_summary}

---

Context:
{context_chunks}

---

{user_question}
"""

def call_llm(prompt: str) -> str:
    response = requests.post(LLM_URL, json={
        "prompt": prompt,
        "temperature": 0.7,
        "n_predict": 300,
        "stream": False,
        "stop": ["\nUser:", "\nAssistant:"]
    })
    return response.json().get("content", "")

def create_semantic_query(user_question: str) -> str:
    """
    Use LLM to rewrite a user question into a clear, specific, and semantically rich query
    suitable for embedding and similarity-based retrieval.
    """
    prompt = f"""You are a research assistant helping users retrieve the most relevant content from a vector database of academic paper chunks.

Given a user question, rewrite it into a clear, specific, and semantically rich query suitable for embedding and similarity-based retrieval.

Assume:
- The content comes from scientific papers.
- The goal is to retrieve text that contains factual answers or explanations.
- Avoid vague pronouns like "this", "it", or "the paper" unless clarified.

User Question:
{user_question}

Rewritten Semantic Search Query:"""

    try:
        response = requests.post(LLM_URL, json={
            "prompt": prompt,
            "temperature": 0.3,  # Lower temperature for more consistent query rewriting
            "n_predict": 100,
            "stream": False,
            "stop": ["\nUser:", "\nAssistant:", "\n\n"]
        })
        rewritten_query = response.json().get("content", "").strip()
        
        # Fallback to original query if LLM call fails or returns empty
        if not rewritten_query:
            return user_question
            
        return rewritten_query
    except Exception as e:
        # Fallback to original query if there's an error
        print(f"Error creating semantic query: {e}")
        return user_question

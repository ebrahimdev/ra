"""
LLM client utilities for the RAG server.
"""
import requests
import json
import logging
from typing import Optional, List, Dict, Any
from ..config import LLM_URL, LLM_TEMPERATURE, LLM_N_PREDICT, LLM_STOP_TOKENS

logger = logging.getLogger(__name__)

def call_llm(prompt: str, temperature: Optional[float] = None, n_predict: Optional[int] = None) -> str:
    """
    Call the LLM with a prompt and return the response.
    
    Args:
        prompt: The prompt to send to the LLM
        temperature: Temperature for generation (optional)
        n_predict: Number of tokens to predict (optional)
        
    Returns:
        LLM response as string
    """
    try:
        response = requests.post(LLM_URL, json={
            "prompt": prompt,
            "temperature": temperature or LLM_TEMPERATURE,
            "n_predict": n_predict or LLM_N_PREDICT,
            "stream": False,
            "stop": LLM_STOP_TOKENS
        })
        
        if response.status_code == 200:
            return response.json().get("content", "")
        else:
            logger.error(f"LLM request failed with status {response.status_code}")
            return ""
            
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ""

def create_semantic_query(user_question: str) -> str:
    """
    Use LLM to rewrite a user question into a clear, specific, and semantically rich query
    suitable for embedding and similarity-based retrieval.
    
    Args:
        user_question: Original user question
        
    Returns:
        Rewritten semantic query
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
        logger.error(f"Error creating semantic query: {e}")
        return user_question

def build_prompt(system: str, context: str, history: List[Dict[str, str]], query: str) -> str:
    """
    Build a prompt for the LLM with system message, context, history, and current query.
    
    Args:
        system: System message
        context: Context information (e.g., RAG results)
        history: Chat history
        query: Current user query
        
    Returns:
        Formatted prompt string
    """
    # Convert history to text format
    history_text = "\n\n".join(
        f"{turn['user']}\n{turn['assistant']}" for turn in history[-2:]
    )

    return f"""{system}\n\n{context}\n\n{history_text}\n\n{query}\n"""

def build_rag_prompt(chat_summary: str, context_chunks: str, user_question: str) -> str:
    """
    Build a prompt for RAG-based responses.
    
    Args:
        chat_summary: Summary of prior conversation
        context_chunks: Retrieved context chunks
        user_question: Current user question
        
    Returns:
        Formatted RAG prompt
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
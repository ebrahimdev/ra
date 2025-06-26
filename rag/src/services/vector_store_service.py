"""
Vector store service for managing ChromaDB operations and embeddings.
"""
import os
import logging
import chromadb
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import List, Dict, Any, Optional
import uuid

from ..config import (
    CHROMA_DB_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    ADVANCED_CHUNKING_ENABLED,
    MIN_TOKENS_PER_CHUNK,
    MAX_TOKENS_PER_CHUNK,
    OVERLAP_TOKENS,
    TOKENIZER_MODEL,
)
from ..utils.text_processing import chunk_by_paragraphs, advanced_chunk_by_structure, ChunkingConfig

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Service for managing vector store operations."""

    def __init__(self, db_dir: str = CHROMA_DB_DIR, collection_name: str = COLLECTION_NAME):
        """Initialize the vector store service."""
        self.db_dir = db_dir
        self.collection_name = collection_name

        os.makedirs(self.db_dir, exist_ok=True)

        self.embedding_model = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")

        self.client = chromadb.PersistentClient(path=self.db_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_model
        )
        logger.info(f"Connected to collection: {self.collection_name}")

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Add texts with embeddings to the vector store."""
        try:
            if not texts:
                return False

            clean_texts = [t for t in texts if t]

            if not clean_texts:
                raise ValueError("No valid texts to embed.")

            ids = [str(uuid.uuid4()) for _ in range(len(clean_texts))]

            if metadatas is None:
                metadatas = [{"source": "unknown"} for _ in clean_texts]

            clean_metadatas = [
                {k: v for k, v in md.items() if v is not None}
                for md in metadatas
            ]

            self.collection.add(
                documents=clean_texts,
                ids=ids,
                metadatas=clean_metadatas
            )
            logger.info(f"Added {len(clean_texts)} texts")
            return True

        except Exception as e:
            logger.error(f"Error adding texts: {e}")
            return False

    def search(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Search for similar texts."""
        try:
            query_embedding = self.embedding_model(query)

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )

            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_results.append({
                        'text': doc,
                        'metadata': metadata or {},
                        'distance': float(distance),
                        'rank': i + 1
                    })

            return {"results": formatted_results}

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return {"results": []}

    def ingest_paper_text(self, text: str, paper_metadata: Dict[str, Any]) -> bool:
        """Ingest paper text into vector store."""
        try:
            if ADVANCED_CHUNKING_ENABLED:
                config = ChunkingConfig(
                    min_tokens=MIN_TOKENS_PER_CHUNK,
                    max_tokens=MAX_TOKENS_PER_CHUNK,
                    overlap_tokens=OVERLAP_TOKENS,
                    tokenizer_model=TOKENIZER_MODEL
                )
                chunks = advanced_chunk_by_structure(text, config)
            else:
                chunks = chunk_by_paragraphs(text, 1500)

            if not chunks:
                return False

            chunk_metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = paper_metadata.copy()
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_length': len(chunk)
                })
                chunk_metadatas.append(chunk_metadata)

            return self.add_texts(chunks, chunk_metadatas)

        except Exception as e:
            logger.error(f"Error ingesting paper: {e}")
            return False

    def list_chunks(self) -> List[Dict[str, Any]]:
        """List all chunks with embedding previews."""
        try:
            results = self.collection.get(include=["documents", "metadatas", "embeddings"])

            chunks = []
            for doc, meta, embedding in zip(results["documents"], results["metadatas"], results["embeddings"]):
                chunk_info = {
                    'text': doc[:200],
                    'metadata': meta,
                    'text_length': len(doc),
                    'embedding_preview': embedding[:10]
                }
                chunks.append(chunk_info)
            return chunks

        except Exception as e:
            logger.error(f"Error listing chunks: {e}")
            return []


    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection_name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def delete_all_chunks(self) -> bool:
        """Delete all chunks."""
        try:
            results = self.collection.get()
            if results['ids']:
                self.collection.delete(ids=results['ids'])
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return False

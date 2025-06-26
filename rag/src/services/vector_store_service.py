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
import pdb
from sentence_transformers import SentenceTransformer


from ..config import (
    CHROMA_DB_DIR,
    COLLECTION_NAME,
    FINE_CHUNKS_COLLECTION,
    COARSE_CHUNKS_COLLECTION,
    EMBEDDING_MODEL,
    ADVANCED_CHUNKING_ENABLED,
    MIN_TOKENS_PER_CHUNK,
    MAX_TOKENS_PER_CHUNK,
    OVERLAP_TOKENS,
    TOKENIZER_MODEL,
    FINE_CHUNK_MIN_CHARS,
    FINE_CHUNK_MAX_CHARS,
    FINE_CHUNK_MIN_SENTENCES,
    FINE_CHUNK_MAX_SENTENCES,
    COARSE_CHUNK_MIN_CHARS,
    COARSE_CHUNK_MAX_CHARS,
    COARSE_CHUNK_MIN_TOKENS,
    COARSE_CHUNK_MAX_TOKENS,
)
from ..utils.text_processing import (
    chunk_by_paragraphs, 
    advanced_chunk_by_structure, 
    ChunkingConfig,
    create_fine_chunks,
    create_coarse_chunks
)

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Service for managing vector store operations with dual collections."""

    def __init__(self, db_dir: str = CHROMA_DB_DIR):
        """Initialize the vector store service with dual collections."""
        self.db_dir = db_dir

        os.makedirs(self.db_dir, exist_ok=True)

        self.embedding_model = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")

        self.client = chromadb.PersistentClient(path=self.db_dir)
        
        # Initialize both collections
        self.fine_collection = self.client.get_or_create_collection(
            name=FINE_CHUNKS_COLLECTION,
            embedding_function=self.embedding_model
        )
        
        self.coarse_collection = self.client.get_or_create_collection(
            name=COARSE_CHUNKS_COLLECTION,
            embedding_function=self.embedding_model
        )
        
        logger.info(f"Connected to collections: {FINE_CHUNKS_COLLECTION}, {COARSE_CHUNKS_COLLECTION}")

    def add_texts_to_collection(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, 
                               collection_name: str = "fine") -> bool:
        """Add texts with embeddings to a specific collection."""
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

            # Choose collection based on name
            collection = self.fine_collection if collection_name == "fine" else self.coarse_collection

            collection.add(
                documents=clean_texts,
                ids=ids,
                metadatas=clean_metadatas
            )
            logger.info(f"Added {len(clean_texts)} texts to {collection_name} collection")
            return True

        except Exception as e:
            logger.error(f"Error adding texts to {collection_name} collection: {e}")
            return False

    def search_collection(self, query: str, k: int = 5, collection_name: str = "fine") -> Dict[str, Any]:
        """Search for similar texts in a specific collection."""
        try:
            query_embedding = self.model.encode(query, convert_to_numpy=True).tolist()

            # Choose collection based on name
            collection = self.fine_collection if collection_name == "fine" else self.coarse_collection

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Convert distance to similarity score (1 - distance)
                    similarity_score = 1.0 - float(distance)
                    formatted_results.append({
                        'text': doc,
                        'metadata': metadata or {},
                        'distance': float(distance),
                        'similarity_score': similarity_score,
                        'rank': i + 1,
                        'collection': collection_name
                    })

            return {"results": formatted_results}

        except Exception as e:
            logger.error(f"Error searching {collection_name} collection: {e}")
            return {"results": []}

    def search_both_collections(self, query: str, k_fine: int = 3, k_coarse: int = 2) -> Dict[str, Any]:
        """Search both collections and combine results."""
        try:
            fine_results = self.search_collection(query, k_fine, "fine")
            coarse_results = self.search_collection(query, k_coarse, "coarse")
            
            # Combine and sort by similarity score
            all_results = fine_results["results"] + coarse_results["results"]
            all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return {"results": all_results}
            
        except Exception as e:
            logger.error(f"Error searching both collections: {e}")
            return {"results": []}

    def ingest_paper_text(self, text: str, paper_metadata: Dict[str, Any]) -> bool:
        """Ingest paper text into both fine and coarse collections."""
        try:
            # Robust bibtex and citation_key generation using available metadata
            citation_key = None
            bibtex = None
            title = paper_metadata.get('title', 'Unknown Title')
            authors = paper_metadata.get('authors', ['Unknown'])
            year = paper_metadata.get('year', 'xxxx')
            arxiv_id = paper_metadata.get('arxiv_id', None)

            # citation_key: firstauthorYYYYfirstwordoftitle or arxiv_id
            if authors and authors[0] != 'Unknown' and year != 'xxxx' and title != 'Unknown Title':
                first_author = authors[0].split()[-1]
                first_word_title = title.split()[0].lower()
                citation_key = f"{first_author.lower()}{year}{first_word_title}"
            elif arxiv_id:
                citation_key = arxiv_id
            else:
                citation_key = title.replace(' ', '_')[:20]

            # bibtex
            if arxiv_id:
                bibtex = (
                    f"@article{{{citation_key},\n"
                    f"  title={{ {title} }},\n"
                    f"  author={{ {' and '.join(authors)} }},\n"
                    f"  year={{ {year} }},\n"
                    f"  eprint={{ {arxiv_id} }},\n"
                    f"  archivePrefix={{arXiv}},\n"
                    f"  url={{ https://arxiv.org/abs/{arxiv_id} }}\n"
                    f"}}"
                )
            else:
                bibtex = (
                    f"@misc{{{citation_key},\n"
                    f"  title={{ {title} }},\n"
                    f"  author={{ {' and '.join(authors)} }},\n"
                    f"  year={{ {year} }},\n"
                    f"  url={{ {paper_metadata.get('url', '')} }}\n"
                    f"}}"
                )

            # Create fine chunks
            fine_chunks = create_fine_chunks(
                text, 
                min_chars=FINE_CHUNK_MIN_CHARS,
                max_chars=FINE_CHUNK_MAX_CHARS,
                min_sentences=FINE_CHUNK_MIN_SENTENCES,
                max_sentences=FINE_CHUNK_MAX_SENTENCES
            )

            # Create coarse chunks
            coarse_chunks = create_coarse_chunks(
                text,
                min_chars=COARSE_CHUNK_MIN_CHARS,
                max_chars=COARSE_CHUNK_MAX_CHARS,
                min_tokens=COARSE_CHUNK_MIN_TOKENS,
                max_tokens=COARSE_CHUNK_MAX_TOKENS
            )

            if not fine_chunks and not coarse_chunks:
                return False

            # Prepare metadata for fine chunks
            fine_chunk_metadatas = []
            for i, chunk in enumerate(fine_chunks):
                chunk_metadata = paper_metadata.copy()
                # Convert any list values to a string (e.g., authors)
                for k, v in chunk_metadata.items():
                    if isinstance(v, list):
                        chunk_metadata[k] = ', '.join(str(x) for x in v)
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(fine_chunks),
                    'chunk_length': len(chunk),
                    'citation_key': citation_key,
                    'bibtex': bibtex,
                    'chunk_type': 'fine'
                })
                fine_chunk_metadatas.append(chunk_metadata)

            # Prepare metadata for coarse chunks
            coarse_chunk_metadatas = []
            for i, chunk in enumerate(coarse_chunks):
                chunk_metadata = paper_metadata.copy()
                # Convert any list values to a string (e.g., authors)
                for k, v in chunk_metadata.items():
                    if isinstance(v, list):
                        chunk_metadata[k] = ', '.join(str(x) for x in v)
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(coarse_chunks),
                    'chunk_length': len(chunk),
                    'citation_key': citation_key,
                    'bibtex': bibtex,
                    'chunk_type': 'coarse'
                })
                coarse_chunk_metadatas.append(chunk_metadata)

            # Add to both collections
            fine_success = self.add_texts_to_collection(fine_chunks, fine_chunk_metadatas, "fine")
            coarse_success = self.add_texts_to_collection(coarse_chunks, coarse_chunk_metadatas, "coarse")

            return fine_success and coarse_success

        except Exception as e:
            logger.error(f"Error ingesting paper: {e}")
            return False

    def list_chunks_from_collection(self, collection_name: str = "fine") -> List[Dict[str, Any]]:
        """List all chunks from a specific collection with embedding previews."""
        try:
            collection = self.fine_collection if collection_name == "fine" else self.coarse_collection
            
            results = collection.get(include=["documents", "metadatas", "embeddings"])

            chunks = []
            for doc, meta, embedding in zip(results["documents"], results["metadatas"], results["embeddings"]):
                chunk_info = {
                    'text': doc[:200],
                    'metadata': meta,
                    'text_length': len(doc),
                    'embedding_preview': embedding[:10],
                    'collection': collection_name
                }
                chunks.append(chunk_info)
            return chunks

        except Exception as e:
            logger.error(f"Error listing chunks from {collection_name} collection: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for both collections."""
        try:
            fine_count = self.fine_collection.count()
            coarse_count = self.coarse_collection.count()
            
            return {
                'fine_chunks_count': fine_count,
                'coarse_chunks_count': coarse_count,
                'total_documents': fine_count + coarse_count,
                'fine_collection_name': FINE_CHUNKS_COLLECTION,
                'coarse_collection_name': COARSE_CHUNKS_COLLECTION
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def delete_all_chunks(self) -> bool:
        """Delete all chunks from both collections."""
        try:
            # Delete from fine collection
            fine_results = self.fine_collection.get()
            if fine_results['ids']:
                self.fine_collection.delete(ids=fine_results['ids'])
            
            # Delete from coarse collection
            coarse_results = self.coarse_collection.get()
            if coarse_results['ids']:
                self.coarse_collection.delete(ids=coarse_results['ids'])
                
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return False

    # Backward compatibility methods
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Backward compatibility: add texts to fine collection."""
        return self.add_texts_to_collection(texts, metadatas, "fine")

    def search(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Backward compatibility: search fine collection."""
        return self.search_collection(query, k, "fine")

    def list_chunks(self) -> List[Dict[str, Any]]:
        """Backward compatibility: list chunks from fine collection."""
        return self.list_chunks_from_collection("fine")

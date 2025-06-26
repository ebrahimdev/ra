"""
Tests for API routes.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from .routes import router
from ..models.api_models import CitationSuggestionRequest, CitationSuggestionResponse

# Create test client
client = TestClient(router)

class TestCitationSuggestion:
    """Test cases for the citation suggestion endpoint."""
    
    @patch('rag.src.api.routes.vector_store')
    def test_suggest_citation_with_match(self, mock_vector_store):
        """Test citation suggestion when a good match is found."""
        # Mock search results
        mock_search_results = {
            "results": [
                {
                    "text": "This is a sample text about machine learning.",
                    "metadata": {
                        "title": "Machine Learning Fundamentals",
                        "authors": "John Doe, Jane Smith",
                        "citation_key": "doe2023ml",
                        "bibtex": "@article{doe2023ml,\n  title={Machine Learning Fundamentals},\n  author={John Doe and Jane Smith},\n  year={2023}\n}"
                    },
                    "similarity_score": 0.85,
                    "distance": 0.15,
                    "rank": 1
                },
                {
                    "text": "Another text about AI.",
                    "metadata": {
                        "title": "AI Basics",
                        "authors": "Alice Johnson",
                        "citation_key": "johnson2023ai",
                        "bibtex": "@article{johnson2023ai,\n  title={AI Basics},\n  author={Alice Johnson},\n  year={2023}\n}"
                    },
                    "similarity_score": 0.75,
                    "distance": 0.25,
                    "rank": 2
                }
            ]
        }
        
        mock_vector_store.search.return_value = mock_search_results
        
        # Test request
        request_data = {"text": "This is a paragraph about machine learning algorithms."}
        
        response = client.post("/suggest-citation", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match"] is True
        assert data["score"] == 0.85
        assert data["paper"]["title"] == "Machine Learning Fundamentals"
        assert data["paper"]["authors"] == "John Doe, Jane Smith"
        assert data["paper"]["citation_key"] == "doe2023ml"
        assert "bibtex" in data["paper"]["bibtex"]
        
        # Verify vector store was called correctly
        mock_vector_store.search.assert_called_once_with(request_data["text"], k=3)
    
    @patch('rag.src.api.routes.vector_store')
    def test_suggest_citation_no_match(self, mock_vector_store):
        """Test citation suggestion when no good match is found."""
        # Mock search results with low similarity scores
        mock_search_results = {
            "results": [
                {
                    "text": "This is a sample text about machine learning.",
                    "metadata": {
                        "title": "Machine Learning Fundamentals",
                        "authors": "John Doe, Jane Smith",
                        "citation_key": "doe2023ml",
                        "bibtex": "@article{doe2023ml,\n  title={Machine Learning Fundamentals},\n  author={John Doe and Jane Smith},\n  year={2023}\n}"
                    },
                    "similarity_score": 0.65,
                    "distance": 0.35,
                    "rank": 1
                }
            ]
        }
        
        mock_vector_store.search.return_value = mock_search_results
        
        # Test request
        request_data = {"text": "This is a paragraph about something completely different."}
        
        response = client.post("/suggest-citation", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match"] is False
        assert data["score"] == 0.65
        assert data["paper"] is None
        
        # Verify vector store was called correctly
        mock_vector_store.search.assert_called_once_with(request_data["text"], k=3)
    
    @patch('rag.src.api.routes.vector_store')
    def test_suggest_citation_no_results(self, mock_vector_store):
        """Test citation suggestion when no search results are found."""
        # Mock empty search results
        mock_search_results = {"results": []}
        
        mock_vector_store.search.return_value = mock_search_results
        
        # Test request
        request_data = {"text": "This is a paragraph about something."}
        
        response = client.post("/suggest-citation", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["match"] is False
        assert data["score"] == 0.0
        assert data["paper"] is None
        
        # Verify vector store was called correctly
        mock_vector_store.search.assert_called_once_with(request_data["text"], k=3)
    
    def test_suggest_citation_invalid_request(self):
        """Test citation suggestion with invalid request data."""
        # Test with missing text field
        request_data = {}
        
        response = client.post("/suggest-citation", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('rag.src.api.routes.vector_store')
    def test_suggest_citation_vector_store_error(self, mock_vector_store):
        """Test citation suggestion when vector store throws an error."""
        # Mock vector store error
        mock_vector_store.search.side_effect = Exception("Vector store error")
        
        # Test request
        request_data = {"text": "This is a paragraph about something."}
        
        response = client.post("/suggest-citation", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Vector store error" in data["detail"]

class TestSearch:
    """Test cases for the search endpoint."""
    
    @patch('rag.src.api.routes.vector_store')
    @patch('rag.src.api.routes.create_semantic_query')
    def test_search_endpoint(self, mock_create_semantic_query, mock_vector_store):
        """Test the search endpoint returns correct format."""
        # Mock semantic query
        mock_create_semantic_query.return_value = "semantic query"
        
        # Mock search results
        mock_search_results = {
            "results": [
                {
                    "text": "Sample text 1",
                    "metadata": {"source": "test"},
                    "similarity_score": 0.9,
                    "distance": 0.1,
                    "rank": 1
                },
                {
                    "text": "Sample text 2", 
                    "metadata": {"source": "test"},
                    "similarity_score": 0.8,
                    "distance": 0.2,
                    "rank": 2
                }
            ]
        }
        
        mock_vector_store.search.return_value = mock_search_results
        
        # Test request
        request_data = {"query": "test query", "k": 5}
        
        response = client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 2
        assert data["results"][0]["text"] == "Sample text 1"
        assert data["results"][1]["text"] == "Sample text 2"
        
        # Verify mocks were called correctly
        mock_create_semantic_query.assert_called_once_with("test query")
        mock_vector_store.search.assert_called_once_with("semantic query", 5) 
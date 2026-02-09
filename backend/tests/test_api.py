"""
Tests for FastAPI endpoints.
"""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check returns 200 and correct structure."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "status" in data
        assert "pinecone_connected" in data
        assert "openai_configured" in data
        assert "anthropic_configured" in data
        assert data["status"] == "healthy"
    
    def test_health_check_connections(self, client):
        """Test health check reports service connections."""
        response = client.get("/health")
        data = response.json()
        
        # These should be True if .env is configured
        assert isinstance(data["pinecone_connected"], bool)
        assert isinstance(data["openai_configured"], bool)
        assert isinstance(data["anthropic_configured"], bool)


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data


class TestSECFetchEndpoint:
    """Tests for /api/fetch-sec endpoint."""
    
    def test_fetch_sec_filings_success(self, client, sample_sec_request):
        """Test SEC filings fetch succeeds."""
        response = client.post("/api/fetch-sec", json=sample_sec_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "chunks_stored" in data
        assert data["chunks_stored"] >= 0
    
    def test_fetch_sec_invalid_ticker(self, client):
        """Test SEC fetch with invalid ticker."""
        response = client.post("/api/fetch-sec", json={
            "ticker": "INVALID",
            "forms": ["10-K"]
        })
        
        # Should either fail or return 0 chunks
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["chunks_stored"] == 0
    
    def test_fetch_sec_multiple_forms(self, client, sample_ticker):
        """Test fetching multiple form types."""
        response = client.post("/api/fetch-sec", json={
            "ticker": sample_ticker,
            "forms": ["10-K", "10-Q"]
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "chunks_stored" in data


class TestUploadEndpoint:
    """Tests for /api/upload endpoint."""
    
    def test_upload_text_file(self, client, sample_ticker, tmp_path):
        """Test uploading a text file."""
        # Create temporary test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a test document for SEC filing analysis.")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"ticker": sample_ticker}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert "message" in data
        assert data["chunks_stored"] > 0
    
    def test_upload_without_ticker(self, client, tmp_path):
        """Test upload fails without ticker."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.txt", f, "text/plain")}
            )
        
        # Should require ticker
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestChatEndpoint:
    """Tests for /api/chat endpoint."""
    
    def test_chat_endpoint_success(self, client, sample_chat_request):
        """Test chat endpoint returns answer."""
        response = client.post("/api/chat", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "answer" in data
        assert "citations" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["citations"], list)
        assert len(data["answer"]) > 0
    
    def test_chat_with_different_providers(self, client, sample_ticker, sample_question):
        """Test chat with different model providers."""
        providers = ["openai"]  # Add "anthropic" if configured
        
        for provider in providers:
            response = client.post("/api/chat", json={
                "ticker": sample_ticker,
                "question": sample_question,
                "model_provider": provider,
                "search_mode": "vector",
                "sources": "both"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "answer" in data
    
    def test_chat_with_hybrid_search(self, client, sample_chat_request):
        """Test chat with hybrid search mode."""
        sample_chat_request["search_mode"] = "hybrid"
        response = client.post("/api/chat", json=sample_chat_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
    
    def test_chat_citations_structure(self, client, sample_chat_request):
        """Test that citations have correct structure."""
        response = client.post("/api/chat", json=sample_chat_request)
        data = response.json()
        
        if len(data["citations"]) > 0:
            citation = data["citations"][0]
            assert "ticker" in citation
            assert "source" in citation
            assert "chunk_index" in citation


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
    
    def test_docs_ui(self, client):
        """Test Swagger UI is available."""
        response = client.get("/docs")
        
        assert response.status_code == status.HTTP_200_OK
        assert "swagger" in response.text.lower()

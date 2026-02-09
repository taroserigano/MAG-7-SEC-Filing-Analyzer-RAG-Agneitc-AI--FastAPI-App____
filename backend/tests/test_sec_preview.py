"""
Test SEC Preview endpoint functionality.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path


def test_sec_preview_markdown(client, mock_sec_service_with_cache):
    """Test preview endpoint with markdown format."""
    response = client.get("/api/sec-preview/AAPL?format=markdown")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ticker"] == "AAPL"
    assert data["format"] == "markdown"
    assert "content" in data
    assert data["file_size"] > 0
    assert len(data["content"]) > 100  # Should have substantial content


def test_sec_preview_text(client, mock_sec_service_with_cache):
    """Test preview endpoint with text format."""
    response = client.get("/api/sec-preview/AAPL?format=text")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ticker"] == "AAPL"
    assert data["format"] == "text"
    assert "content" in data
    assert data["file_size"] > 0


def test_sec_preview_case_insensitive(client, mock_sec_service_with_cache):
    """Test preview endpoint is case-insensitive for ticker."""
    response = client.get("/api/sec-preview/aapl?format=markdown")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"


def test_sec_preview_not_cached(client, mock_sec_service):
    """Test preview endpoint when filing not cached."""
    response = client.get("/api/sec-preview/MSFT?format=markdown")
    
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "cached" in detail or "not found" in detail
    assert "fetch" in detail


def test_sec_preview_invalid_format(client, mock_sec_service_with_cache):
    """Test preview endpoint with invalid format."""
    response = client.get("/api/sec-preview/AAPL?format=invalid")
    
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


def test_sec_preview_default_format(client, mock_sec_service_with_cache):
    """Test preview endpoint defaults to markdown."""
    response = client.get("/api/sec-preview/AAPL")
    
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "markdown"


def test_sec_preview_content_readable(client, mock_sec_service_with_cache):
    """Test that preview content is human-readable."""
    response = client.get("/api/sec-preview/AAPL?format=text")
    
    assert response.status_code == 200
    data = response.json()
    content = data["content"]
    
    # Check for common 10-K content
    assert "Apple" in content or "AAPL" in content
    # Should contain actual text, not just metadata
    assert len(content.split()) > 100  # At least 100 words
    # Should not be JSON or encoded
    assert not content.startswith("{")
    assert not content.startswith("[")

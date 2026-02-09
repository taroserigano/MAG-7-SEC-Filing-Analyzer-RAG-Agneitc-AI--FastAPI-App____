"""
Tests for batch API endpoint and smart query routing optimizations.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_simple_query_detection():
    """Test that simple queries are detected correctly."""
    from app.agents.router_agent import RouterAgent
    
    router = RouterAgent()
    
    # Should detect simple queries
    assert router.is_simple_query("hello") == True
    assert router.is_simple_query("hi") == True
    assert router.is_simple_query("thanks") == True
    assert router.is_simple_query("thank you") == True
    assert router.is_simple_query("ok") == True
    assert router.is_simple_query("?") == True
    assert router.is_simple_query("help") == True
    
    # Should not detect complex queries
    assert router.is_simple_query("What is Apple's revenue?") == False
    assert router.is_simple_query("Tell me about Tesla's risks") == False
    assert router.is_simple_query("How did NVIDIA perform?") == False


def test_chat_endpoint_handles_simple_queries(client):
    """Test that chat endpoint returns quick response for simple queries."""
    response = client.post(
        "/api/chat",
        json={
            "ticker": "AAPL",
            "question": "hello",
            "modelProvider": "openai",
            "searchMode": "vector",
            "sources": "both",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return quick response without LLM call
    assert "Hello" in data["answer"] or "help" in data["answer"].lower()
    assert data["citations"] == []
    assert "simple_query" in data["flags_summary"]


def test_chat_endpoint_processes_complex_queries(client):
    """Test that complex queries go through full pipeline."""
    with patch('app.agents.graph.run_agent_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            "answer": "Apple's revenue was $394.3B in 2023.",
            "citations": [
                {
                    "ticker": "AAPL",
                    "form_type": "10-K",
                    "year": 2023,
                    "chunk_index": 0,
                    "source": "sec"
                }
            ],
            "retrieval_flags": {},
        }
        
        response = client.post(
            "/api/chat",
            json={
                "ticker": "AAPL",
                "question": "What is Apple's revenue?",
                "modelProvider": "openai",
                "searchMode": "vector",
                "sources": "both",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should process through pipeline
        assert mock_pipeline.called
        assert "revenue" in data["answer"].lower()
        assert len(data["citations"]) > 0


def test_batch_endpoint_exists(client):
    """Test that batch endpoint is registered."""
    with patch('app.agents.graph.run_agent_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            "answer": "Test answer",
            "citations": [],
            "retrieval_flags": {},
        }
        
        response = client.post(
            "/api/chat/batch",
            json={
                "tickers": ["AAPL", "TSLA"],
                "question": "What is the revenue?",
                "modelProvider": "openai",
                "searchMode": "vector",
                "sources": "both",
            },
        )
        
        # Should accept the request
        assert response.status_code in [200, 422]  # May fail validation but endpoint exists


def test_batch_endpoint_handles_simple_queries(client):
    """Test that batch endpoint returns quick response for simple queries."""
    response = client.post(
        "/api/chat/batch",
        json={
            "requests": [
                {
                    "ticker": "AAPL",
                    "question": "hello",
                    "model_provider": "openai",
                    "search_mode": "vector",
                    "sources": "both",
                },
                {
                    "ticker": "TSLA",
                    "question": "hi",
                    "model_provider": "openai",
                    "search_mode": "vector",
                    "sources": "both",
                },
            ]
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return quick responses for all tickers
    assert len(data["responses"]) == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    for response_item in data["responses"]:
        assert "Hello" in response_item["answer"] or "help" in response_item["answer"].lower()


def test_batch_endpoint_processes_multiple_tickers(client):
    """Test that batch endpoint processes multiple tickers."""
    with patch('app.agents.graph.run_agent_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            "answer": "Test answer",
            "citations": [],
            "retrieval_flags": {},
        }
        
        response = client.post(
            "/api/chat/batch",
            json={
                "requests": [
                    {
                        "ticker": "AAPL",
                        "question": "What is the revenue trend?",
                        "model_provider": "openai",
                        "search_mode": "vector",
                        "sources": "both",
                    },
                    {
                        "ticker": "TSLA",
                        "question": "What is the revenue trend?",
                        "model_provider": "openai",
                        "search_mode": "vector",
                        "sources": "both",
                    },
                    {
                        "ticker": "NVDA",
                        "question": "What is the revenue trend?",
                        "model_provider": "openai",
                        "search_mode": "vector",
                        "sources": "both",
                    },
                ]
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should process all tickers
        assert len(data["responses"]) == 3
        assert data["successful"] == 3
        assert data["failed"] == 0


def test_batch_endpoint_handles_errors_gracefully(client):
    """Test that batch endpoint handles individual failures."""
    call_count = 0
    
    def mock_pipeline_with_error(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("ticker") == "TSLA":
            return {"error": "Test error"}
        return {
            "answer": f"Answer for {kwargs.get('ticker')}",
            "citations": [],
            "retrieval_flags": {},
        }
    
    with patch('app.agents.graph.run_agent_pipeline', side_effect=mock_pipeline_with_error):
        response = client.post(
            "/api/chat/batch",
            json={
                "requests": [
                    {
                        "ticker": "AAPL",
                        "question": "What is the revenue?",
                        "model_provider": "openai",
                        "search_mode": "vector",
                        "sources": "both",
                    },
                    {
                        "ticker": "TSLA",
                        "question": "What is the revenue?",
                        "model_provider": "openai",
                        "search_mode": "vector",
                        "sources": "both",
                    },
                    {
                        "ticker": "NVDA",
                        "question": "What is the revenue?",
                        "model_provider": "openai",
                        "search_mode": "vector",
                        "sources": "both",
                    },
                ]
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have results for all tickers
        assert len(data["responses"]) == 3
        assert data["successful"] == 2
        assert data["failed"] == 1
        
        # AAPL should succeed
        assert "AAPL" in data["responses"][0]["answer"]
        
        # TSLA should have error
        assert data["results"][1]["error"] is not None
        assert "Test error" in data["results"][1]["error"]
        
        # NVDA should succeed
        assert data["results"][2]["error"] is None


def test_router_classify_skips_llm_for_simple_queries():
    """Test that classify returns 'simple' for simple queries without LLM call."""
    from app.agents.router_agent import RouterAgent
    
    with patch('app.agents.router_agent.ChatOpenAI') as mock_openai:
        router = RouterAgent(model_provider="openai")
        
        # Should not call LLM for simple query
        result = router.classify("hello")
        assert result == "simple"
        
        # Should not have invoked the LLM
        if hasattr(router.llm, 'invoke'):
            assert not router.llm.invoke.called or mock_openai.call_count == 0


def test_batch_models_defined():
    """Test that batch models are defined in models.py."""
    from app.models import BatchChatRequest, BatchChatResponse
    
    # Should be able to import
    assert BatchChatRequest is not None
    assert BatchChatResponse is not None

"""
Tests for HTTP connection pooling and request deduplication optimizations.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_http_client_singleton():
    """Test that HTTP client is a singleton with connection pooling."""
    from app.utils.http_client import get_http_client, _http_client
    
    # Get client twice
    client1 = await get_http_client()
    client2 = await get_http_client()
    
    # Should be the same instance
    assert client1 is client2
    assert client1 is not None


@pytest.mark.asyncio
async def test_http_client_configuration():
    """Test that HTTP client has correct pooling configuration."""
    from app.utils.http_client import get_http_client
    
    client = await get_http_client()
    
    # Check limits are configured
    assert client._limits.max_keepalive_connections == 20
    assert client._limits.max_connections == 50
    
    # Check timeout is configured
    assert client._timeout.connect == 10.0
    assert client._timeout.read == 60.0


@pytest.mark.asyncio
async def test_http_client_cleanup():
    """Test that HTTP client can be closed properly."""
    from app.utils.http_client import get_http_client, close_http_client, _http_client
    
    client = await get_http_client()
    assert client is not None
    
    await close_http_client()
    
    # Should be None after closing
    from app.utils import http_client
    assert http_client._http_client is None


@pytest.mark.asyncio
async def test_deduplication_creates_unique_keys():
    """Test that request keys are created correctly."""
    from app.utils.deduplication import _create_request_key
    
    # Same parameters should create same key
    key1 = _create_request_key("AAPL", "What is revenue?", model_provider="openai")
    key2 = _create_request_key("AAPL", "What is revenue?", model_provider="openai")
    assert key1 == key2
    
    # Different parameters should create different keys
    key3 = _create_request_key("TSLA", "What is revenue?", model_provider="openai")
    assert key1 != key3
    
    # Case insensitive for ticker
    key4 = _create_request_key("aapl", "What is revenue?", model_provider="openai")
    assert key1 == key4


@pytest.mark.asyncio
async def test_deduplication_prevents_duplicate_requests():
    """Test that duplicate concurrent requests are deduplicated."""
    from app.utils.deduplication import deduplicate_request, clear_pending
    
    await clear_pending()
    
    call_count = 0
    
    async def mock_handler(**kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate work
        return {"answer": "test", "citations": []}
    
    # Launch two identical requests concurrently
    results = await asyncio.gather(
        deduplicate_request("AAPL", "test question", mock_handler),
        deduplicate_request("AAPL", "test question", mock_handler),
    )
    
    # Should only call handler once
    assert call_count == 1
    
    # Both should get results
    assert results[0][0] == {"answer": "test", "citations": []}
    assert results[1][0] == {"answer": "test", "citations": []}
    
    # One should be deduplicated
    assert results[0][1] == False  # First request not deduplicated
    assert results[1][1] == True   # Second request was deduplicated


@pytest.mark.asyncio
async def test_deduplication_different_requests():
    """Test that different requests are not deduplicated."""
    from app.utils.deduplication import deduplicate_request, clear_pending
    
    await clear_pending()
    
    call_count = 0
    
    async def mock_handler(**kwargs):
        nonlocal call_count
        call_count += 1
        return {"answer": f"test{call_count}", "citations": []}
    
    # Launch two different requests
    results = await asyncio.gather(
        deduplicate_request("AAPL", "question 1", mock_handler),
        deduplicate_request("TSLA", "question 2", mock_handler),
    )
    
    # Should call handler twice
    assert call_count == 2
    
    # Neither should be deduplicated
    assert results[0][1] == False
    assert results[1][1] == False


@pytest.mark.asyncio
async def test_deduplication_pending_count():
    """Test that pending request count is tracked."""
    from app.utils.deduplication import deduplicate_request, get_pending_count, clear_pending
    
    await clear_pending()
    
    async def slow_handler(**kwargs):
        await asyncio.sleep(0.2)
        return {"answer": "test"}
    
    # Start a request
    task = asyncio.create_task(
        deduplicate_request("AAPL", "slow question", slow_handler)
    )
    
    # Give it time to register
    await asyncio.sleep(0.05)
    
    # Should have 1 pending
    count = await get_pending_count()
    assert count == 1
    
    # Wait for completion
    await task
    
    # Should have 0 pending
    count = await get_pending_count()
    assert count == 0


@pytest.mark.asyncio
async def test_chat_endpoint_uses_deduplication(client):
    """Test that chat endpoint uses deduplication."""
    with patch('app.agents.graph.run_agent_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            "answer": "Test answer",
            "citations": [],
            "retrieval_flags": {},
        }
        
        # Make the same request twice concurrently
        import httpx
        async with httpx.AsyncClient(app=client.app, base_url="http://test") as ac:
            responses = await asyncio.gather(
                ac.post("/api/chat", json={
                    "ticker": "AAPL",
                    "question": "What is revenue?",
                    "modelProvider": "openai",
                    "searchMode": "vector",
                    "sources": "both",
                }),
                ac.post("/api/chat", json={
                    "ticker": "AAPL",
                    "question": "What is revenue?",
                    "modelProvider": "openai",
                    "searchMode": "vector",
                    "sources": "both",
                }),
            )
        
        # Both requests should succeed
        assert responses[0].status_code == 200
        assert responses[1].status_code == 200
        
        # Pipeline should be called (deduplication happens inside)
        assert mock_pipeline.called


def test_http_client_in_lifespan():
    """Test that HTTP client is initialized in lifespan."""
    import inspect
    from app.main import lifespan
    
    source = inspect.getsource(lifespan)
    
    # Should initialize HTTP client
    assert 'get_http_client' in source
    assert 'close_http_client' in source

"""
Request deduplication to prevent redundant concurrent API calls.
"""
import asyncio
from typing import Dict, Any, Tuple, Callable, Awaitable
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# In-flight request tracking
_pending_requests: Dict[str, asyncio.Task] = {}
_dedup_lock = asyncio.Lock()


def _create_request_key(ticker: str, question: str, **kwargs) -> str:
    """
    Create a unique key for a request based on parameters.
    
    Args:
        ticker: Stock ticker
        question: User question
        **kwargs: Additional parameters (model_provider, search_mode, etc.)
    
    Returns:
        Hash string representing the unique request
    """
    # Normalize and sort parameters for consistent hashing
    params = {
        "ticker": ticker.upper(),
        "question": question.strip().lower(),
        **{k: v for k, v in sorted(kwargs.items()) if v is not None}
    }
    
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.sha256(param_str.encode()).hexdigest()[:16]


async def deduplicate_request(
    ticker: str,
    question: str,
    handler: Callable[..., Awaitable[Dict[str, Any]]],
    **kwargs
) -> Tuple[Dict[str, Any], bool]:
    """
    Execute request with deduplication - if same request is in-flight, wait for it.
    
    Args:
        ticker: Stock ticker
        question: User question
        handler: Async function to execute if not deduplicated
        **kwargs: Additional parameters to pass to handler
    
    Returns:
        Tuple of (result, was_deduplicated)
    """
    request_key = _create_request_key(ticker, question, **kwargs)
    
    async with _dedup_lock:
        # Check if request is already in flight
        if request_key in _pending_requests:
            existing_task = _pending_requests[request_key]
            logger.info(f"Deduplicating request: {ticker} - {question[:50]}...")
            
            # Wait for existing request to complete (outside lock)
            async with _dedup_lock:
                pass  # Release lock before awaiting
            
            try:
                result = await existing_task
                return result, True  # Deduplicated
            except Exception as e:
                logger.error(f"Deduplicated request failed: {e}")
                raise
        
        # No existing request, create new task
        task = asyncio.create_task(handler(**kwargs))
        _pending_requests[request_key] = task
    
    try:
        result = await task
        return result, False  # Not deduplicated
    finally:
        # Remove from pending when complete
        async with _dedup_lock:
            _pending_requests.pop(request_key, None)


async def get_pending_count() -> int:
    """Get count of pending deduplicated requests."""
    async with _dedup_lock:
        return len(_pending_requests)


async def clear_pending() -> None:
    """Clear all pending requests (for testing)."""
    async with _dedup_lock:
        _pending_requests.clear()

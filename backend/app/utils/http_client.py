"""
HTTP client utilities with connection pooling for improved performance.
"""
import httpx
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create the global HTTP client with connection pooling.
    
    Benefits:
    - Reuses TCP connections across requests
    - Reduces latency from connection setup
    - Limits concurrent connections to prevent overwhelming servers
    
    Returns:
        Configured httpx AsyncClient
    """
    global _http_client
    
    async with _client_lock:
        if _http_client is None:
            # Configure connection pooling
            limits = httpx.Limits(
                max_keepalive_connections=20,  # Keep 20 connections alive
                max_connections=50,            # Max 50 total connections
                keepalive_expiry=30.0          # Keep connections for 30s
            )
            
            timeout = httpx.Timeout(
                connect=10.0,   # 10s to establish connection
                read=60.0,      # 60s to read response
                write=10.0,     # 10s to send request
                pool=5.0        # 5s to get connection from pool
            )
            
            _http_client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True,
                http2=False  # Disable HTTP/2 to avoid h2 dependency
            )
            
            logger.info("HTTP client initialized with connection pooling")
    
    return _http_client


async def close_http_client():
    """Close the global HTTP client and cleanup connections."""
    global _http_client
    
    async with _client_lock:
        if _http_client is not None:
            await _http_client.aclose()
            _http_client = None
            logger.info("HTTP client closed")

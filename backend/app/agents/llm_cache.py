"""
LLM Client Cache - Reuses LLM instances across requests for better performance.
OPTIMIZED: Faster model defaults, request timeouts, connection reuse.
"""
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Global LLM instance cache (reused across requests)
_LLM_CACHE: Dict[str, Any] = {}

# Optimized model defaults for speed
_MODEL_DEFAULTS = {
    "openai": "gpt-4o-mini",  # Fastest OpenAI model
    "anthropic": "claude-3-5-haiku-latest",  # Fastest Anthropic model
    "ollama": "llama3:8b"
}


def get_cached_llm(
    model_provider: str = "openai",
    model_name: Optional[str] = None,
    temperature: float = 0.0,  # Lower default for faster, deterministic responses
    max_tokens: int = 300  # Reduced default for faster generation
) -> Any:
    """
    Get a cached LLM instance or create a new one.
    OPTIMIZED: Faster defaults, request timeouts, connection reuse.
    
    Args:
        model_provider: LLM provider ("openai", "anthropic", "ollama")
        model_name: Specific model name (uses fast defaults if not provided)
        temperature: Model temperature (0.0 = deterministic/fastest)
        max_tokens: Maximum tokens for response
        
    Returns:
        Cached or newly created LLM instance
    """
    settings = get_settings()
    
    # Use fast model defaults
    if model_name is None:
        model_name = _MODEL_DEFAULTS.get(model_provider, "gpt-4o-mini")
    
    # Create cache key
    cache_key = f"{model_provider}:{model_name}:{temperature}:{max_tokens}"
    
    # Return cached instance if available
    if cache_key in _LLM_CACHE:
        return _LLM_CACHE[cache_key]
    
    # Create new instance with optimized settings
    logger.info(f"Creating LLM instance: {cache_key}")
    
    if model_provider == "openai":
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=settings.openai_api_key,
            request_timeout=30,  # 30s timeout
            max_retries=1  # Minimal retries for speed
        )
    elif model_provider == "anthropic":
        llm = ChatAnthropic(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            anthropic_api_key=settings.anthropic_api_key,
            timeout=30.0  # 30s timeout
        )
    elif model_provider == "ollama":
        llm = ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=settings.ollama_base_url,
            num_predict=max_tokens
        )
    else:
        # Default to OpenAI
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=settings.openai_api_key,
            request_timeout=30
        )
    
    # Cache and return
    _LLM_CACHE[cache_key] = llm
    return llm


def clear_llm_cache():
    """Clear the LLM cache (useful for testing)."""
    global _LLM_CACHE
    _LLM_CACHE = {}
    logger.info("LLM cache cleared")

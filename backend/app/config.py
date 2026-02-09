from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Performance-tuned defaults for fast responses.
    """
    model_config = SettingsConfigDict(extra="ignore")
    # OpenAI
    openai_api_key: str
    
    # Anthropic (optional)
    anthropic_api_key: str = ""
    
    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "mag7-sec-filings"
    pinecone_environment: str = "us-west1-gcp"
    
    # Ollama (optional)
    ollama_base_url: str = "http://localhost:11434"

    # Retrieval options / feature flags (tuned for speed)
    enable_rerank: bool = False  # Disabled by default for speed
    enable_query_rewrite: bool = False  # Disabled by default for speed
    enable_retrieval_cache: bool = True  # Keep enabled for cache hits
    retrieval_cache_ttl_seconds: int = 600  # 10 min TTL for better hit rate
    rerank_top_k: int = 4  # Reduced from 6 for faster processing
    enable_section_boost: bool = False  # Disabled by default for speed
    reranker_model: str = "builtin"
    
    # Performance settings
    max_concurrent_requests: int = 10  # Limit concurrent LLM calls
    embedding_batch_size: int = 64  # Batch size for embeddings
    llm_timeout_seconds: int = 30  # LLM request timeout
    answer_cache_ttl_seconds: int = 600  # Answer cache TTL
    
    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    reload: bool = True
    
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        case_sensitive=False,
    )


def get_settings() -> Settings:
    """
    Get settings instance.
    """
    return Settings()

from typing import List, Optional
from pydantic import BaseModel, Field


class SECPreviewResponse(BaseModel):
    """Response model for SEC filing preview."""
    ticker: str
    format: str
    content: str
    file_size: int


class SECFetchRequest(BaseModel):
    """Request model for fetching SEC filings."""
    ticker: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    forms: List[str] = Field(default=["10-K", "10-Q"], description="Types of SEC forms to fetch")
    count: int = Field(default=5, description="Number of filings per form type (e.g., 5 = 5 years of 10-K + 5 years of 10-Q)")


class UploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    message: str
    chunks_stored: int


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    ticker: str = Field(..., description="Stock ticker to query about")
    question: str = Field(..., description="User's question")
    model_provider: str = Field(default="openai", description="LLM provider: openai, anthropic, or ollama")
    search_mode: str = Field(default="vector", description="Search mode: vector or hybrid")
    sources: str = Field(default="both", description="Data sources: sec, user, or both")
    enable_rerank: bool = Field(default=False, description="Toggle reranker stage")
    enable_query_rewrite: bool = Field(default=False, description="Toggle query rewrite stage")
    enable_retrieval_cache: bool = Field(default=False, description="Toggle retrieval result caching")
    enable_section_boost: bool = Field(default=False, description="Toggle section-aware boosting")
    reranker_model: str = Field(default="builtin", description="Reranker choice: builtin or external model id")


class Citation(BaseModel):
    """Citation from a source document."""
    ticker: str
    form_type: Optional[str] = None
    year: Optional[int] = None
    chunk_index: int
    source: str  # "sec" or "user"


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    citations: List[Citation]
    flags_summary: str = Field(default="", description="Summary of retrieval flags applied")
    cache_hit: bool = Field(default=False, description="Whether retrieval cache served the request")


class BatchChatRequest(BaseModel):
    """Request model for batch chat endpoint."""
    requests: List[ChatRequest] = Field(..., description="List of chat requests to process")


class BatchChatResponse(BaseModel):
    """Response model for batch chat endpoint."""
    responses: List[ChatResponse] = Field(..., description="List of chat responses")
    total: int
    successful: int
    failed: int
    comparative_summary: str = Field(default="", description="Comparative analysis across all responses")


class CompareRequest(BaseModel):
    """Request for comparing multiple tickers on a question."""
    tickers: List[str]
    question: str = Field(..., min_length=1)
    model_provider: str = Field(default="openai")
    search_mode: str = Field(default="vector")
    sources: str = Field(default="both")
    enable_rerank: bool = False
    enable_query_rewrite: bool = False
    enable_retrieval_cache: bool = False
    enable_section_boost: bool = False
    reranker_model: str = "builtin"


class CompareResult(BaseModel):
    """Per-ticker result for a comparison run."""
    ticker: str
    answer: str
    flags_summary: str = ""
    cache_hit: bool = False


class CompareResponse(BaseModel):
    """Response model for compare endpoint."""
    combined_answer: str
    results: List[CompareResult]


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    pinecone_connected: bool
    openai_configured: bool
    anthropic_configured: bool

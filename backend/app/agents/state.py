"""
State management for the multi-agent workflow.
"""
from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    State shared across all agents in the workflow.
    """
    # Input
    ticker: str
    question: str
    model_provider: str
    search_mode: str
    sources: str
    retrieval_overrides: Optional[Dict[str, Any]]
    
    # Router output
    task_type: Optional[str]
    
    # Retriever output
    retrieved_chunks: Optional[List[Dict[str, Any]]]
    retrieval_flags: Optional[Dict[str, Any]]
    retrieval_cache_hit: Optional[bool]
    
    # Analyst output
    analysis: Optional[str]
    extracted_info: Optional[Dict[str, Any]]
    
    # Reporter output
    answer: Optional[str]
    citations: Optional[List[Dict[str, Any]]]
    
    # Error handling
    error: Optional[str]

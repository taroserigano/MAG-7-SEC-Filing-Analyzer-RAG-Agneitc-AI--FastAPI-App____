"""
Fast RAG Agent: Combined retriever + analyzer + reporter in minimal LLM calls.
OPTIMIZED: Single LLM call instead of 3 separate calls.
"""
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from app.pinecone_client import get_pinecone_client
from app.config import get_settings
from app.agents.llm_cache import get_cached_llm
from app.agents.router_agent import RouterAgent
import logging
import asyncio
import time
import hashlib

logger = logging.getLogger(__name__)

# Retrieval cache
_RETRIEVAL_CACHE: dict = {}


class FastRAGAgent:
    """
    Optimized RAG agent that combines retrieval, analysis, and answer generation.
    Uses a single LLM call instead of separate Analyst and Reporter calls.
    """
    
    def __init__(self, model_provider: str = "openai"):
        """Initialize the fast RAG agent."""
        self.model_provider = model_provider
        self.settings = get_settings()
        self.pinecone_client = None
        self.router = RouterAgent(model_provider=model_provider)
        
        # Single combined prompt for analysis + answer generation
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a financial analyst. Analyze SEC filings and provide clear, concise answers.
Include key data points and cite sources. Keep responses under 250 words and focus on the most relevant information."""),
            ("user", """Question: {question}
Company: {ticker}

SEC Filing Excerpts:
{chunks}

Answer:""")
        ])
    
    def _get_pinecone_client(self):
        """Lazy load Pinecone client."""
        if self.pinecone_client is None:
            self.pinecone_client = get_pinecone_client()
        return self.pinecone_client
    
    def _cache_key(self, question: str, ticker: str, search_mode: str) -> str:
        """Generate cache key for retrieval (uses hash for efficiency)."""
        key_str = f"{ticker}|{search_mode}|{question.lower().strip()[:100]}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_chunks(self, key: str) -> Optional[List[Dict]]:
        """Get cached retrieval results with extended TTL."""
        entry = _RETRIEVAL_CACHE.get(key)
        if not entry:
            return None
        ts, value = entry
        if time.time() - ts > self.settings.retrieval_cache_ttl_seconds:
            _RETRIEVAL_CACHE.pop(key, None)
            return None
        logger.debug(f"Cache hit for key {key[:8]}")
        return value
    
    def _set_cached_chunks(self, key: str, value: List[Dict]):
        """Cache retrieval results."""
        if self.settings.enable_retrieval_cache:
            _RETRIEVAL_CACHE[key] = (time.time(), value)
    
    def retrieve(
        self,
        question: str,
        ticker: str,
        search_mode: str = "vector",
        sources: str = "both",
        top_k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from Pinecone.
        OPTIMIZED: Uses cached embeddings and faster search.
        """
        try:
            # Check cache first
            cache_key = self._cache_key(question, ticker, search_mode)
            cached = self._get_cached_chunks(cache_key)
            if cached is not None:
                logger.info(f"✅ Using cached retrieval results for {ticker}")
                return cached
            
            client = self._get_pinecone_client()
            filter_dict = {"ticker": ticker}
            
            if sources != "both":
                filter_dict["source"] = sources
            
            # Perform search
            if search_mode == "hybrid":
                results = client.hybrid_search(
                    query=question,
                    top_k=top_k,
                    filter_dict=filter_dict
                )
            else:
                results = client.search(
                    query=question,
                    top_k=top_k,
                    filter_dict=filter_dict
                )
            
            # Cache results
            self._set_cached_chunks(cache_key, results or [])
            logger.info(f"📦 Retrieved {len(results or [])} chunks for {ticker}")
            return results or []
            
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    def _format_chunks(self, chunks: List[Dict], max_chunks: int = 3) -> str:
        """Format chunks for the prompt. OPTIMIZED: Minimal formatting, fewer tokens."""
        if not chunks:
            return "No relevant documents found."
        
        # Use list comprehension for speed
        formatted = [
            f"[{i}] {chunk.get('metadata', {}).get('form_type', '10-K')}: {chunk.get('text', '')[:300]}"
            for i, chunk in enumerate(chunks[:max_chunks], 1)
        ]
        
        return "\n".join(formatted)  # Single newline for compactness
    
    def _extract_citations(self, chunks: List[Dict], ticker: str) -> List[Dict]:
        """Extract citations from chunks."""
        citations = []
        for i, chunk in enumerate(chunks[:5]):
            metadata = chunk.get("metadata", {})
            citations.append({
                "ticker": ticker,
                "form_type": metadata.get("form_type", "10-K"),
                "year": metadata.get("year"),
                "chunk_index": i,
                "source": metadata.get("source", "sec")
            })
        return citations
    
    async def process(
        self,
        ticker: str,
        question: str,
        search_mode: str = "vector",
        sources: str = "both",
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a question with optimized single-LLM-call pipeline.
        
        Steps:
        1. Classify question (deterministic - no LLM)
        2. Retrieve chunks from Pinecone
        3. Generate answer (single LLM call)
        
        Args:
            ticker: Stock ticker
            question: User's question
            search_mode: Search mode (vector/hybrid)
            sources: Data sources
            overrides: Settings overrides
            
        Returns:
            Dict with answer, citations, and metadata
        """
        try:
            # Apply overrides
            if overrides:
                for key, val in overrides.items():
                    if val is not None and hasattr(self.settings, key):
                        setattr(self.settings, key, val)
            
            # Step 1: Classify question (instant - no LLM)
            task_type = self.router.classify(question)
            if task_type == "simple":
                return {
                    "answer": "Hello! I can help you analyze SEC filings. Ask me about financial metrics, risks, or business strategies.",
                    "citations": [],
                    "task_type": "simple",
                    "retrieval_cache_hit": False
                }
            
            # Step 2: Retrieve chunks (parallel-ready)
            chunks = self.retrieve(question, ticker, search_mode, sources)
            
            if not chunks:
                return {
                    "answer": f"I couldn't find relevant information about {ticker} in the SEC filings. Please try fetching the latest filings first.",
                    "citations": [],
                    "task_type": task_type,
                    "retrieval_cache_hit": False
                }
            
            # Step 3: Generate answer (single LLM call with optimized settings)
            try:
                llm = get_cached_llm(
                    model_provider=self.model_provider,
                    temperature=0.0,  # Deterministic for fastest response
                    max_tokens=300    # Reduced for faster generation
                )
                
                chunks_text = self._format_chunks(chunks, max_chunks=3)  # Reduced from 4
                
                chain = self.prompt | llm
                response = chain.invoke({
                    "question": question,
                    "ticker": ticker,
                    "chunks": chunks_text
                })
            except Exception as llm_error:
                error_msg = str(llm_error)
                logger.error(f"LLM invocation error: {error_msg}")
                logger.error(f"Model provider: {self.model_provider}")
                logger.error(f"Checking conditions - Has 401: {'401' in error_msg}, Has auth: {'authentication' in error_msg.lower()}")
                
                # Provide helpful error messages for API key issues
                if "401" in error_msg or "authentication" in error_msg.lower() or ("invalid" in error_msg.lower() and "key" in error_msg.lower()):
                    logger.error(f"Condition matched for API key error")
                    if self.model_provider == "openai":
                        logger.error("Returning OpenAI error message")
                        return {
                            "error": "Invalid OpenAI API Key",
                            "answer": "❌ OpenAI API key is invalid or expired. Please update OPENAI_API_KEY in backend/.env file. Get a valid key from https://platform.openai.com/api-keys",
                            "citations": []
                        }
                    elif self.model_provider == "anthropic":
                        logger.error("Returning Anthropic error message")
                        return {
                            "error": "Invalid Anthropic API Key",
                            "answer": "❌ Anthropic API key is invalid or expired. Please update ANTHROPIC_API_KEY in backend/.env file. Get a valid key from https://console.anthropic.com/settings/keys",
                            "citations": []
                        }
                # Re-raise if not an API key issue
                logger.error("Re-raising exception")
                raise
            
            answer = response.content if hasattr(response, "content") else str(response)
            citations = self._extract_citations(chunks, ticker)
            
            logger.info(f"✅ Generated answer for {ticker}: {len(answer)} chars")
            
            return {
                "answer": answer,
                "citations": citations,
                "task_type": task_type,
                "retrieved_chunks": chunks,
                "retrieval_cache_hit": False,
                "retrieval_flags": {
                    "enable_rerank": self.settings.enable_rerank,
                    "enable_query_rewrite": self.settings.enable_query_rewrite,
                    "enable_retrieval_cache": self.settings.enable_retrieval_cache,
                    "enable_section_boost": self.settings.enable_section_boost,
                    "reranker_model": getattr(self.settings, "reranker_model", "builtin"),
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"FastRAG error: {error_msg}")
            
            # Provide helpful error messages for API key issues
            if "401" in error_msg or "authentication" in error_msg.lower() or ("invalid" in error_msg.lower() and "key" in error_msg.lower()):
                if self.model_provider == "openai":
                    return {
                        "error": "Invalid OpenAI API Key",
                        "answer": "❌ OpenAI API key is invalid or expired. Please update OPENAI_API_KEY in backend/.env file. Get a valid key from https://platform.openai.com/api-keys",
                        "citations": []
                    }
                elif self.model_provider == "anthropic":
                    return {
                        "error": "Invalid Anthropic API Key",
                        "answer": "❌ Anthropic API key is invalid or expired. Please update ANTHROPIC_API_KEY in backend/.env file. Get a valid key from https://console.anthropic.com/settings/keys",
                        "citations": []
                    }
            
            return {
                "error": str(e),
                "answer": f"Error processing question: {e}",
                "citations": []
            }


async def run_fast_pipeline(
    ticker: str,
    question: str,
    model_provider: str = "openai",
    search_mode: str = "vector",
    sources: str = "both",
    retrieval_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the optimized fast RAG pipeline.
    
    This replaces the multi-agent LangGraph pipeline with a streamlined
    single-LLM-call approach for much faster responses.
    """
    agent = FastRAGAgent(model_provider=model_provider)
    return await agent.process(
        ticker=ticker,
        question=question,
        search_mode=search_mode,
        sources=sources,
        overrides=retrieval_overrides
    )


async def run_parallel_pipeline(
    tickers: List[str],
    question: str,
    model_provider: str = "openai",
    search_mode: str = "vector",
    sources: str = "both",
    retrieval_overrides: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Run the pipeline for multiple tickers in parallel.
    Each ticker is processed concurrently for maximum speed.
    """
    tasks = [
        run_fast_pipeline(
            ticker=ticker,
            question=question,
            model_provider=model_provider,
            search_mode=search_mode,
            sources=sources,
            retrieval_overrides=retrieval_overrides
        )
        for ticker in tickers
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions
    processed_results = []
    for ticker, result in zip(tickers, results):
        if isinstance(result, Exception):
            processed_results.append({
                "ticker": ticker,
                "error": str(result),
                "answer": f"Error processing {ticker}: {result}",
                "citations": []
            })
        else:
            result["ticker"] = ticker
            processed_results.append(result)
    
    return processed_results

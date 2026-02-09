"""
Retriever Agent: Retrieves relevant chunks from Pinecone using RAG.
"""
from typing import Dict, Any, List, Optional
from app.pinecone_client import get_pinecone_client
from app.config import get_settings
import logging
import time

# Simple in-process cache store (ticker+query scoped) used only when enabled
_RETRIEVAL_CACHE: dict = {}

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """
    Retrieves relevant document chunks from Pinecone based on the question.
    Applies filters based on ticker, source, and search mode.
    """
    
    def __init__(self):
        """Initialize the retriever agent."""
        self.pinecone_client = None
        self.settings = get_settings()
        self.last_cache_hit = False
    
    def _get_client(self):
        """Lazy load Pinecone client."""
        if self.pinecone_client is None:
            self.pinecone_client = get_pinecone_client()
        return self.pinecone_client
    
    def _rewrite_queries(self, question: str, ticker: str) -> List[str]:
        """Return list of queries; add lightweight expansion when enabled."""
        if not self.settings.enable_query_rewrite:
            return [question]

        # Deterministic heuristic expansion to avoid external LLM calls in tests
        expansions = []
        lower_q = question.lower()
        if ticker and ticker.lower() not in lower_q:
            expansions.append(f"{ticker} {question}")
        if "10-k" not in lower_q:
            expansions.append(f"{question} 10-K filing")
        if "risk" in lower_q:
            expansions.append(f"{question} risk factors")
        # De-duplicate while preserving order
        seen = set()
        queries = []
        for q in [question] + expansions:
            if q not in seen:
                seen.add(q)
                queries.append(q)
        return queries

    def _score(self, query: str, chunk: Dict[str, Any], task_type: str) -> float:
        """Lightweight relevance score using token overlap plus section boosts."""
        text = (chunk.get("text") or "").lower()
        metadata = chunk.get("metadata", {}) or {}
        tokens = set(query.lower().split())
        overlap = sum(1 for t in tokens if t and t in text)

        # Section-aware boost if enabled
        if self.settings.enable_section_boost:
            section = (metadata.get("section") or "").lower()
            if task_type == "risk_analysis" and "risk" in section:
                overlap += 2
            if task_type == "trend_analysis" and any(k in section for k in ["md&a", "management", "analysis"]):
                overlap += 1
        return overlap

    def _rerank(self, query: str, results: List[Dict[str, Any]], task_type: str, top_k: int) -> List[Dict[str, Any]]:
        if not self.settings.enable_rerank or not results:
            return results[:top_k]
        scored = [
            (self._score(query, r, task_type), r)
            for r in results
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[: top_k]]

    def _cache_key(self, question: str, ticker: str, sources: str, search_mode: str) -> str:
        return f"{ticker}|{sources}|{search_mode}|{question}"

    def _get_cached(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if not self.settings.enable_retrieval_cache:
            return None
        ttl = max(1, self.settings.retrieval_cache_ttl_seconds)
        entry = _RETRIEVAL_CACHE.get(key)
        if not entry:
            return None
        ts, value = entry
        if time.time() - ts > ttl:
            _RETRIEVAL_CACHE.pop(key, None)
            return None
        return value

    def _set_cached(self, key: str, value: List[Dict[str, Any]]):
        if not self.settings.enable_retrieval_cache:
            return
        _RETRIEVAL_CACHE[key] = (time.time(), value)

    def retrieve(
        self,
        question: str,
        ticker: str,
        sources: str = "both",
        search_mode: str = "vector",
        top_k: int = 6,
        task_type: str = "general",
        overrides: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from Pinecone.
        
        Args:
            question: User's question
            ticker: Stock ticker to filter on
            sources: Data sources to search ("sec", "user", or "both")
            search_mode: Search mode ("vector" or "hybrid")
            top_k: Number of results to return
            
        Returns:
            List of retrieved chunks with metadata
        """
        try:
            # Refresh settings each call so tests can monkeypatch get_settings safely
            base_settings = get_settings()
            if overrides:
                for key, val in overrides.items():
                    if val is None:
                        continue
                    if hasattr(base_settings, key):
                        setattr(base_settings, key, val)
            self.settings = base_settings
            client = self._get_client()

            # Build metadata filter
            filter_dict = {"ticker": ticker}

            # Add source filter if specified
            if sources != "both":
                filter_dict["source"] = sources

            cache_key = self._cache_key(question, ticker, sources, search_mode)
            cached = self._get_cached(cache_key)
            cache_hit = cached is not None
            self.last_cache_hit = cache_hit
            if cache_hit:
                logger.info("Returning cached retrieval result")
                return cached
            self.last_cache_hit = False

            queries = self._rewrite_queries(question, ticker)
            results: List[Dict[str, Any]] = []

            for q in queries:
                if search_mode == "hybrid":
                    found = client.hybrid_search(
                        query=q,
                        top_k=top_k,
                        filter_dict=filter_dict
                    )
                else:
                    found = client.search(
                        query=q,
                        top_k=top_k,
                        filter_dict=filter_dict
                    )
                results.extend(found or [])

            # De-duplicate by id if present
            deduped = []
            seen_ids = set()
            for r in results:
                rid = r.get("id") or id(r)
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                deduped.append(r)

            reranked = self._rerank(question, deduped, task_type or "general", top_k)
            self._set_cached(cache_key, reranked)
            logger.info(f"Retrieved {len(reranked)} chunks for ticker {ticker}")
            return reranked

        except Exception as e:
            logger.error(f"Error in retriever agent: {str(e)}")
            return []
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the state and retrieve relevant chunks.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with retrieved_chunks
        """
        question = state.get("question", "")
        ticker = state.get("ticker", "")
        sources = state.get("sources", "both")
        search_mode = state.get("search_mode", "vector")
        state_task_type = state.get("task_type", "general")
        
        # Adjust top_k based on task type - aggressively reduced for speed
        task_type = state.get("task_type", "general")
        top_k = 8 if task_type == "trend_analysis" else 6
        
        overrides = state.get("retrieval_overrides") or {}
        chunks = self.retrieve(
            question=question,
            ticker=ticker,
            sources=sources,
            search_mode=search_mode,
            top_k=top_k,
            task_type=state_task_type,
            overrides=overrides
        )

        # If vector search returns nothing, fall back to hybrid for better recall
        if not chunks and search_mode == "vector":
            logger.info("No chunks found with vector search; falling back to hybrid")
            chunks = self.retrieve(
                question=question,
                ticker=ticker,
                sources=sources,
                search_mode="hybrid",
                top_k=top_k,
                overrides=overrides
            )
        
        return {
            **state,
            "retrieved_chunks": chunks,
            "retrieval_flags": {
                "enable_rerank": self.settings.enable_rerank,
                "enable_query_rewrite": self.settings.enable_query_rewrite,
                "enable_retrieval_cache": self.settings.enable_retrieval_cache,
                "enable_section_boost": self.settings.enable_section_boost,
                "reranker_model": getattr(self.settings, "reranker_model", "builtin"),
            },
            "retrieval_cache_hit": getattr(self, "last_cache_hit", False)
        }

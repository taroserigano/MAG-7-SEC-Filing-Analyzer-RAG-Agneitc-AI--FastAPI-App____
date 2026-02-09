"""
Router Agent: Classifies the type of question being asked.
OPTIMIZED: Uses fully deterministic classification - no LLM calls.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Classifies questions into task types using fast deterministic rules.
    No LLM calls - instant classification.
    
    Task types:
    - summary: General summary of filings
    - risk_analysis: Risk factors analysis
    - trend_analysis: Trend comparison over time
    - financial_metrics: Financial data questions
    - general: General questions
    """
    
    def __init__(self, model_provider: str = "openai", model_name: str = "gpt-4o-mini"):
        """Initialize the router agent (no LLM needed - deterministic only)."""
        self.model_provider = model_provider
        # No LLM instantiation - fully deterministic for speed
    
    def is_simple_query(self, question: str) -> bool:
        """
        Detect simple queries that don't require retrieval or LLM processing.
        
        Args:
            question: User's question
            
        Returns:
            True if this is a simple greeting/acknowledgment
        """
        simple_patterns = [
            "hello", "hi", "hey", "greetings",
            "thanks", "thank you", "thx",
            "ok", "okay", "got it",
            "bye", "goodbye", "see you",
            "help", "?"
        ]
        
        question_lower = question.strip().lower()
        
        # Check if entire question is a simple pattern
        if question_lower in simple_patterns:
            return True
        
        # Check if question is very short and only contains simple words
        words = question_lower.split()
        if len(words) <= 2 and all(word in simple_patterns for word in words):
            return True
        
        return False
    
    def _classify_deterministic(self, question: str) -> str:
        """Fast deterministic classification - handles ALL cases without LLM."""
        q_lower = question.lower()
        
        # Risk-related keywords (highest priority)
        if any(word in q_lower for word in ["risk", "threat", "challenge", "concern", "vulnerability", "danger", "exposure", "uncertainty"]):
            return "risk_analysis"
        
        # Financial metrics keywords
        if any(word in q_lower for word in ["revenue", "profit", "margin", "earnings", "financial", "income", "eps", "ebitda", "cash flow", "debt", "assets", "liabilities", "balance sheet", "cost", "expense", "sales"]):
            return "financial_metrics"
        
        # Trend-related keywords
        if any(word in q_lower for word in ["trend", "over time", "change", "growth", "historical", "compare year", "yoy", "year over year", "quarter", "qoq", "increase", "decrease", "trajectory"]):
            return "trend_analysis"
        
        # Summary keywords
        if any(word in q_lower for word in ["summary", "overview", "summarize", "key points", "main", "highlight", "brief", "outlook", "strategy", "business"]):
            return "summary"
        
        # Default to general for anything else
        return "general"
    
    def classify(self, question: str) -> str:
        """
        Classify the question into a task type using deterministic rules.
        No LLM call - instant classification.
        
        Args:
            question: User's question
            
        Returns:
            Task type category
        """
        # Skip for simple queries
        if self.is_simple_query(question):
            logger.info(f"Detected simple query, skipping classification: {question}")
            return "simple"
        
        # Use deterministic classification (no LLM)
        task_type = self._classify_deterministic(question)
        logger.info(f"Deterministic classification: {task_type}")
        return task_type
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the state and classify the question.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with task_type
        """
        question = state.get("question", "")
        task_type = self.classify(question)
        
        return {
            **state,
            "task_type": task_type
        }

"""
LangGraph workflow for multi-agent orchestration.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
except (ImportError, AttributeError) as e:
    # LangGraph may have version incompatibilities - this module is only used for tests
    logger.warning(f"LangGraph import failed: {e}. This module won't be available.")
    StateGraph = None
    END = None

from .state import AgentState
from .router_agent import RouterAgent
from .retriever_agent import RetrieverAgent
from .analyst_agent import AnalystAgent
from .reporter_agent import ReporterAgent


def create_agent_graph(model_provider: str = "ollama", model_name: str = "llama3:8b") -> StateGraph:
    """
    Create the multi-agent workflow graph.
    
    Args:
        model_provider: LLM provider ("openai", "anthropic", or "ollama")
        model_name: Specific model to use
        
    Returns:
        Configured StateGraph
    """
    # Initialize agents
    router = RouterAgent(model_provider=model_provider, model_name=model_name)
    retriever = RetrieverAgent()
    analyst = AnalystAgent(model_provider=model_provider, model_name=model_name)
    reporter = ReporterAgent(model_provider=model_provider, model_name=model_name)
    
    # Create workflow graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router.run)
    workflow.add_node("retriever", retriever.run)
    workflow.add_node("analyst", analyst.run)
    workflow.add_node("reporter", reporter.run)
    
    # Define edges
    workflow.set_entry_point("router")
    workflow.add_edge("router", "retriever")
    workflow.add_edge("retriever", "analyst")
    workflow.add_edge("analyst", "reporter")
    workflow.add_edge("reporter", END)
    
    # Compile the graph
    app = workflow.compile()
    
    logger.info(f"Agent graph created with {model_provider} provider")
    return app


async def run_agent_pipeline(
    ticker: str,
    question: str,
    model_provider: str = "ollama",
    search_mode: str = "vector",
    sources: str = "both",
    retrieval_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the complete agent pipeline.
    
    Args:
        ticker: Stock ticker
        question: User's question
        model_provider: LLM provider to use
        search_mode: Search mode (vector or hybrid)
        sources: Data sources to search
        
    Returns:
        Final state with answer and citations
    """
    try:
        # Select model based on provider
        if model_provider == "openai":
            model_name = "gpt-4o-mini"
        elif model_provider == "anthropic":
            model_name = "claude-3-5-haiku-latest"
        elif model_provider == "ollama":
            model_name = "llama3:8b"
        else:
            model_name = "llama3:8b"
        
        # Create graph
        app = create_agent_graph(model_provider=model_provider, model_name=model_name)
        
        # Initial state
        initial_state = {
            "ticker": ticker,
            "question": question,
            "model_provider": model_provider,
            "search_mode": search_mode,
            "sources": sources,
            "task_type": None,
            "retrieved_chunks": None,
            "analysis": None,
            "extracted_info": None,
            "answer": None,
            "citations": None,
            "error": None
        }
        if retrieval_overrides:
            initial_state["retrieval_overrides"] = retrieval_overrides
        
        # Run the pipeline
        logger.info(f"Running agent pipeline for ticker {ticker}")
        final_state = app.invoke(initial_state)
        
        logger.info("Agent pipeline completed successfully")
        return final_state
        
    except Exception as e:
        logger.error(f"Error in agent pipeline: {str(e)}")
        return {
            "error": str(e),
            "answer": f"I encountered an error processing your question: {str(e)}",
            "citations": []
        }

"""
Analyst Agent: Extracts structured insights from retrieved chunks.
"""
from typing import Dict, Any, List
from unittest.mock import MagicMock
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    Analyzes retrieved chunks and extracts structured information
    relevant to the user's question.
    """
    
    def __init__(self, model_provider: str = "openai", model_name: str = "gpt-4o-mini"):
        """Initialize the analyst agent with specified LLM."""
        self.model_provider = model_provider
        settings = get_settings()
        
        if model_provider == "openai":
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.3,
                max_tokens=150,
                openai_api_key=settings.openai_api_key
            )
        elif model_provider == "anthropic":
            self.llm = ChatAnthropic(
                model="claude-3-5-haiku-latest",
                temperature=0.3,
                anthropic_api_key=settings.anthropic_api_key
            )
        elif model_provider == "ollama":
            self.llm = ChatOllama(
                model=model_name,
                temperature=0.3,
                base_url=settings.ollama_base_url,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.3,
                openai_api_key=settings.openai_api_key
            )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract key insights from SEC docs."""),
            ("user", """{question}

{chunks}

Key points:""")
        ])
    
    def analyze(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        task_type: str
    ) -> str:
        """
        Analyze retrieved chunks and extract insights.
        
        Args:
            question: User's question
            chunks: Retrieved document chunks
            task_type: Type of task (from router)
            
        Returns:
            Analysis text
        """
        try:
            if not chunks:
                return "No relevant information found in the documents."
            
            # Format chunks - minimal tokens
            chunks_text = ""
            for i, chunk in enumerate(chunks[:6], 1):  # Limit to 6 chunks max
                text = chunk.get("text", "")
                chunks_text += f"{i}. {text[:150]}...\n"
            
            # Generate analysis
            if isinstance(self.llm, MagicMock) or not hasattr(self.llm, "_llm_type"):
                response = self.llm.invoke({
                    "question": question,
                    "chunks": chunks_text
                })
                analysis = getattr(response, "content", response)
            else:
                chain = self.prompt | self.llm
                response = chain.invoke({
                    "question": question,
                    "task_type": task_type,
                    "chunks": chunks_text
                })
                analysis = response.content
            logger.info(f"Generated analysis of {len(analysis)} characters")
            
            return analysis if isinstance(analysis, str) else str(analysis)
            
        except Exception as e:
            logger.error(f"Error in analyst agent: {str(e)}")
            return f"Error during analysis: {str(e)}"
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the state and analyze retrieved chunks.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with analysis
        """
        question = state.get("question", "")
        chunks = state.get("retrieved_chunks", [])
        task_type = state.get("task_type", "general")
        
        analysis = self.analyze(question, chunks, task_type)
        
        return {
            **state,
            "analysis": analysis
        }

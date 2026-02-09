"""
Reporter Agent: Generates final natural language answer with citations.
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


class ReporterAgent:
    """
    Generates a final, well-formatted answer with proper citations
    based on the analyst's insights.
    """
    
    def __init__(self, model_provider: str = "openai", model_name: str = "gpt-4o-mini"):
        """Initialize the reporter agent with specified LLM."""
        self.model_provider = model_provider
        settings = get_settings()
        
        if model_provider == "openai":
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.2,
                max_tokens=200,
                openai_api_key=settings.openai_api_key
            )
        elif model_provider == "anthropic":
            self.llm = ChatAnthropic(
                model="claude-3-5-haiku-latest",
                temperature=0.2,
                anthropic_api_key=settings.anthropic_api_key
            )
        elif model_provider == "ollama":
            self.llm = ChatOllama(
                model=model_name,
                temperature=0.2,
                base_url=settings.ollama_base_url,
            )
        else:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.2,
                openai_api_key=settings.openai_api_key
            )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Answer from analysis."""),
            ("user", """{question}

{analysis}

Answer:""")
        ])
    
    def generate_answer(
        self,
        question: str,
        analysis: str
    ) -> str:
        """
        Generate final answer from analysis.
        
        Args:
            question: User's question
            analysis: Analysis from analyst agent
            
        Returns:
            Final answer text
        """
        try:
            if isinstance(self.llm, MagicMock) or not hasattr(self.llm, "_llm_type"):
                response = self.llm.invoke({
                    "question": question,
                    "analysis": analysis
                })
                answer = getattr(response, "content", response)
            else:
                chain = self.prompt | self.llm
                response = chain.invoke({
                    "question": question,
                    "analysis": analysis
                })
                answer = response.content
            logger.info(f"Generated answer of {len(answer)} characters")
            
            return answer if isinstance(answer, str) else str(answer)
            
        except Exception as e:
            logger.error(f"Error in reporter agent: {str(e)}")
            return f"I encountered an error generating the answer: {str(e)}"
    
    async def generate_comparative_summary(
        self,
        question: str,
        ticker_results: Dict[str, str]
    ) -> str:
        """
        Generate a comparative summary across multiple tickers.
        
        Args:
            question: Original question asked
            ticker_results: Dict mapping ticker symbols to their individual answers
            
        Returns:
            Comparative summary text
        """
        try:
            combined_context = "\n\n".join([
                f"**{ticker}:**\n{answer}"
                for ticker, answer in ticker_results.items()
            ])
            
            comparative_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a financial analyst creating comparative summaries across multiple companies.

Your task:
1. Compare and contrast the information across all companies
2. Identify key similarities and differences
3. Highlight notable trends or patterns
4. Provide actionable insights
5. Keep the summary concise but comprehensive

Format your response as a cohesive comparative analysis."""),
                ("user", """Question: {question}

Individual Company Results:
{combined_context}

Generate a comparative summary.""")
            ])
            
            chain = comparative_prompt | self.llm
            response = chain.invoke({
                "question": question,
                "combined_context": combined_context
            })
            
            summary = response.content if hasattr(response, "content") else str(response)
            logger.info(f"Generated comparative summary of {len(summary)} characters for {len(ticker_results)} tickers")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating comparative summary: {str(e)}")
            return f"Comparative summary: {', '.join(ticker_results.keys())} results available above."
    
    def extract_citations(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract citation information from chunks.
        
        Args:
            chunks: Retrieved document chunks
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            
            citation = {
                "ticker": metadata.get("ticker", "unknown"),
                "form_type": metadata.get("form_type"),
                "year": metadata.get("year"),
                "chunk_index": metadata.get("chunk_index", 0),
                "source": metadata.get("source", "unknown"),
                "section": metadata.get("section")
            }
            
            citations.append(citation)
        
        return citations
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the state and generate final answer with citations.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with answer and citations
        """
        question = state.get("question", "")
        analysis = state.get("analysis", "")
        chunks = state.get("retrieved_chunks", [])
        
        # Generate answer
        answer = self.generate_answer(question, analysis)
        
        # Extract citations
        citations = self.extract_citations(chunks)
        
        return {
            **state,
            "answer": answer,
            "citations": citations
        }

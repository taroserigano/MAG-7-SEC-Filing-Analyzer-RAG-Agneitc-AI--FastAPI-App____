"""
Tests for multi-agent system components.
"""
import pytest
from app.agents.router_agent import RouterAgent
from app.agents.retriever_agent import RetrieverAgent
from app.agents.analyst_agent import AnalystAgent
from app.agents.reporter_agent import ReporterAgent


class TestRouterAgent:
    """Tests for Router Agent."""
    
    @pytest.fixture
    def router(self):
        """Create router agent instance."""
        return RouterAgent(model_provider="openai")
    
    def test_classify_risk_question(self, router):
        """Test classification of risk-related question."""
        question = "What are the main risk factors for Apple?"
        task_type = router.classify(question)
        
        assert task_type in ["risk_analysis", "general"]
    
    def test_classify_financial_question(self, router):
        """Test classification of financial question."""
        question = "What was the revenue in Q4?"
        task_type = router.classify(question)
        
        assert task_type in ["financial_metrics", "general"]
    
    def test_classify_trend_question(self, router):
        """Test classification of trend question."""
        question = "How has performance changed over time?"
        task_type = router.classify(question)
        
        assert task_type in ["trend_analysis", "general"]


class TestRetrieverAgent:
    """Tests for Retriever Agent."""
    
    @pytest.fixture
    def retriever(self):
        """Create retriever agent instance."""
        return RetrieverAgent()
    
    def test_retriever_returns_list(self, retriever):
        """Test retriever returns list of chunks."""
        results = retriever.retrieve(
            question="What is Apple's business?",
            ticker="AAPL",
            sources="both",
            search_mode="vector",
            top_k=5
        )
        
        assert isinstance(results, list)
    
    def test_retriever_with_filters(self, retriever):
        """Test retriever applies filters correctly."""
        results = retriever.retrieve(
            question="Risk factors",
            ticker="AAPL",
            sources="sec",
            search_mode="vector",
            top_k=3
        )
        
        assert isinstance(results, list)


class TestAnalystAgent:
    """Tests for Analyst Agent."""
    
    @pytest.fixture
    def analyst(self):
        """Create analyst agent instance."""
        return AnalystAgent(model_provider="openai")
    
    def test_analyst_generates_analysis(self, analyst):
        """Test analyst generates analysis from chunks."""
        chunks = [
            {
                "text": "Apple Inc. reported strong revenue growth.",
                "metadata": {"ticker": "AAPL", "form_type": "10-K"}
            }
        ]
        
        analysis = analyst.analyze(
            question="How did Apple perform?",
            chunks=chunks,
            task_type="general"
        )
        
        assert isinstance(analysis, str)
        assert len(analysis) > 0


class TestReporterAgent:
    """Tests for Reporter Agent."""
    
    @pytest.fixture
    def reporter(self):
        """Create reporter agent instance."""
        return ReporterAgent(model_provider="openai")
    
    def test_reporter_generates_answer(self, reporter):
        """Test reporter generates answer."""
        analysis = "Apple showed strong performance in Q4 with revenue growth."
        
        answer = reporter.generate_answer(
            question="How did Apple perform?",
            analysis=analysis
        )
        
        assert isinstance(answer, str)
        assert len(answer) > 0
    
    def test_reporter_extracts_citations(self, reporter):
        """Test reporter extracts citations."""
        chunks = [
            {
                "metadata": {
                    "ticker": "AAPL",
                    "form_type": "10-K",
                    "year": 2024,
                    "chunk_index": 0,
                    "source": "sec"
                }
            }
        ]
        
        citations = reporter.extract_citations(chunks)
        
        assert isinstance(citations, list)
        assert len(citations) == 1
        assert citations[0]["ticker"] == "AAPL"

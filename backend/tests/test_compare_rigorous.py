"""
Rigorous integration tests for the compare endpoint.
"""
import pathlib
import sys
import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


@pytest.fixture
def mock_agent_pipeline(monkeypatch):
    """Mock the agent pipeline to return predictable results."""
    call_log = []
    
    async def fake_pipeline(ticker, question, **kwargs):
        call_log.append(ticker)
        return {
            "answer": f"Analysis for {ticker}: {question[:30]}...",
            "retrieval_flags": {
                "enable_rerank": kwargs.get("retrieval_overrides", {}).get("enable_rerank", False),
                "enable_query_rewrite": kwargs.get("retrieval_overrides", {}).get("enable_query_rewrite", False),
                "enable_retrieval_cache": kwargs.get("retrieval_overrides", {}).get("enable_retrieval_cache", False),
                "enable_section_boost": kwargs.get("retrieval_overrides", {}).get("enable_section_boost", False),
                "reranker_model": kwargs.get("retrieval_overrides", {}).get("reranker_model", "builtin"),
            },
            "cache_hit": ticker in ["AAPL", "MSFT"],
        }
    
    monkeypatch.setattr("app.agents.graph.run_agent_pipeline", fake_pipeline, raising=False)
    return call_log


class TestCompareValidation:
    """Test input validation for compare endpoint."""
    
    def test_empty_tickers_list(self, client: TestClient):
        """Test that empty tickers list is rejected."""
        response = client.post("/api/compare", json={"tickers": [], "question": "Compare"})
        assert response.status_code == 400
        assert "At least two tickers" in response.json()["detail"]
    
    def test_single_ticker(self, client: TestClient):
        """Test that single ticker is rejected."""
        response = client.post("/api/compare", json={"tickers": ["AAPL"], "question": "Compare"})
        assert response.status_code == 400
        assert "At least two tickers" in response.json()["detail"]
    
    def test_duplicate_tickers_normalized(self, client: TestClient, mock_agent_pipeline):
        """Test that duplicate tickers are deduplicated."""
        response = client.post("/api/compare", json={
            "tickers": ["aapl", "AAPL", " aapl ", "MSFT"],
            "question": "Compare revenue"
        })
        assert response.status_code == 200
        data = response.json()
        # Should only call AAPL and MSFT once each
        assert len(data["results"]) == 2
        tickers = {r["ticker"] for r in data["results"]}
        assert tickers == {"AAPL", "MSFT"}
    
    def test_whitespace_only_tickers_filtered(self, client: TestClient, mock_agent_pipeline):
        """Test that whitespace-only tickers are filtered out."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "  ", "", "MSFT"],
            "question": "Compare"
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2


class TestCompareResults:
    """Test compare results structure and content."""
    
    def test_two_tickers_basic(self, client: TestClient, mock_agent_pipeline):
        """Test basic two-ticker comparison."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "NVDA"],
            "question": "Compare recent performance"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "combined_answer" in data
        assert "results" in data
        assert len(data["results"]) == 2
        
        # Check each result
        for result in data["results"]:
            assert "ticker" in result
            assert "answer" in result
            assert "flags_summary" in result
            assert "cache_hit" in result
            assert result["ticker"] in ["AAPL", "NVDA"]
            assert len(result["answer"]) > 0
        
        # Check combined answer
        assert "AAPL:" in data["combined_answer"]
        assert "NVDA:" in data["combined_answer"]
    
    def test_three_tickers(self, client: TestClient, mock_agent_pipeline):
        """Test three-ticker comparison."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT", "GOOGL"],
            "question": "Compare AI strategy"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 3
        tickers = {r["ticker"] for r in data["results"]}
        assert tickers == {"AAPL", "MSFT", "GOOGL"}
        
        # All three should appear in combined answer
        assert "AAPL:" in data["combined_answer"]
        assert "MSFT:" in data["combined_answer"]
        assert "GOOGL:" in data["combined_answer"]
    
    def test_mag7_comparison(self, client: TestClient, mock_agent_pipeline):
        """Test comparing all MAG7 stocks."""
        mag7 = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA"]
        response = client.post("/api/compare", json={
            "tickers": mag7,
            "question": "Compare market cap and growth"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 7
        result_tickers = {r["ticker"] for r in data["results"]}
        assert result_tickers == set(mag7)
    
    def test_cache_hit_info(self, client: TestClient, mock_agent_pipeline):
        """Test that cache_hit info is properly returned."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT", "UNKNOWN"],
            "question": "Compare"
        })
        assert response.status_code == 200
        data = response.json()
        
        # AAPL and MSFT should be cache hits (per mock)
        for result in data["results"]:
            if result["ticker"] in ["AAPL", "MSFT"]:
                assert result["cache_hit"] is True
            else:
                assert result["cache_hit"] is False


class TestCompareFlags:
    """Test retrieval flags handling."""
    
    def test_flags_passed_to_pipeline(self, client: TestClient, mock_agent_pipeline):
        """Test that retrieval flags are passed to pipeline."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare",
            "enable_rerank": True,
            "enable_query_rewrite": True,
            "enable_retrieval_cache": True,
            "enable_section_boost": True,
            "reranker_model": "cohere"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check flags in results
        for result in data["results"]:
            flags = result["flags_summary"]
            assert "rerank=on" in flags
            assert "rewrite=on" in flags
            assert "cache=on" in flags
            assert "section_boost=on" in flags
            assert "reranker=cohere" in flags
    
    def test_default_flags(self, client: TestClient, mock_agent_pipeline):
        """Test default flag values."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check defaults
        for result in data["results"]:
            flags = result["flags_summary"]
            assert "rerank=off" in flags
            assert "rewrite=off" in flags
            assert "cache=off" in flags
            assert "section_boost=off" in flags
            assert "reranker=builtin" in flags


class TestCompareExecution:
    """Test compare execution flow."""
    
    def test_sequential_execution(self, client: TestClient, mock_agent_pipeline):
        """Test that tickers are processed sequentially."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT", "GOOGL"],
            "question": "Compare"
        })
        assert response.status_code == 200
        
        # Check that all tickers were called in order
        assert mock_agent_pipeline == ["AAPL", "MSFT", "GOOGL"]
    
    def test_question_passed_to_all(self, client: TestClient, mock_agent_pipeline):
        """Test that same question is used for all tickers."""
        question = "What are the main revenue sources?"
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "NVDA"],
            "question": question
        })
        assert response.status_code == 200
        data = response.json()
        
        # Each answer should reference the question
        for result in data["results"]:
            assert question[:20] in result["answer"]


class TestCompareEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_missing_question(self, client: TestClient):
        """Test that missing question is handled."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"]
        })
        # Should fail validation (422)
        assert response.status_code == 422
    
    def test_very_long_question(self, client: TestClient, mock_agent_pipeline):
        """Test handling of very long question."""
        long_question = "Compare " + "analysis " * 500
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": long_question
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
    
    def test_special_characters_in_ticker(self, client: TestClient, mock_agent_pipeline):
        """Test handling of special characters in ticker."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "BRK.B", "MSFT"],
            "question": "Compare"
        })
        assert response.status_code == 200
        data = response.json()
        # BRK.B should be normalized to BRK.B
        tickers = {r["ticker"] for r in data["results"]}
        assert "BRK.B" in tickers or "BRKB" in tickers
    
    def test_lowercase_ticker_normalization(self, client: TestClient, mock_agent_pipeline):
        """Test that lowercase tickers are normalized to uppercase."""
        response = client.post("/api/compare", json={
            "tickers": ["aapl", "nvda"],
            "question": "Compare"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should return uppercase
        for result in data["results"]:
            assert result["ticker"].isupper()
            assert result["ticker"] in ["AAPL", "NVDA"]


class TestCompareModelProviders:
    """Test different model providers."""
    
    def test_openai_provider(self, client: TestClient, mock_agent_pipeline):
        """Test with OpenAI provider."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare",
            "model_provider": "openai"
        })
        assert response.status_code == 200
    
    def test_ollama_provider(self, client: TestClient, mock_agent_pipeline):
        """Test with Ollama provider."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare",
            "model_provider": "ollama"
        })
        assert response.status_code == 200
    
    def test_default_provider(self, client: TestClient, mock_agent_pipeline):
        """Test default provider."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare"
        })
        assert response.status_code == 200


class TestCompareSearchModes:
    """Test different search modes."""
    
    def test_vector_search(self, client: TestClient, mock_agent_pipeline):
        """Test vector search mode."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare",
            "search_mode": "vector"
        })
        assert response.status_code == 200
    
    def test_hybrid_search(self, client: TestClient, mock_agent_pipeline):
        """Test hybrid search mode."""
        response = client.post("/api/compare", json={
            "tickers": ["AAPL", "MSFT"],
            "question": "Compare",
            "search_mode": "hybrid"
        })
        assert response.status_code == 200

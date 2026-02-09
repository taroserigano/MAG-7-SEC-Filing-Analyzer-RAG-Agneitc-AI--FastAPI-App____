"""
Integration tests for complete workflows.
"""
import pytest
import time
from fastapi import status


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.slow
    def test_fetch_and_chat_workflow(self, client, sample_ticker):
        """Test complete workflow: fetch SEC data then chat."""
        # Step 1: Fetch SEC filings
        fetch_response = client.post("/api/fetch-sec", json={
            "ticker": sample_ticker,
            "forms": ["10-K"]
        })
        
        assert fetch_response.status_code == status.HTTP_200_OK
        fetch_data = fetch_response.json()
        assert fetch_data["chunks_stored"] > 0
        
        # Wait for indexing
        time.sleep(2)
        
        # Step 2: Chat about the data
        chat_response = client.post("/api/chat", json={
            "ticker": sample_ticker,
            "question": "What does this company do?",
            "model_provider": "openai",
            "search_mode": "vector",
            "sources": "sec"
        })
        
        assert chat_response.status_code == status.HTTP_200_OK
        chat_data = chat_response.json()
        assert len(chat_data["answer"]) > 0
        assert len(chat_data["citations"]) > 0
    
    @pytest.mark.slow
    def test_upload_and_chat_workflow(self, client, sample_ticker, tmp_path):
        """Test workflow: upload document then chat."""
        # Step 1: Upload document
        test_file = tmp_path / "company_info.txt"
        test_file.write_text(
            f"{sample_ticker} is a technology company known for innovation."
        )
        
        with open(test_file, "rb") as f:
            upload_response = client.post(
                "/api/upload",
                files={"file": ("company_info.txt", f, "text/plain")},
                data={"ticker": sample_ticker}
            )
        
        assert upload_response.status_code == status.HTTP_200_OK
        
        # Wait for indexing
        time.sleep(2)
        
        # Step 2: Chat about uploaded data
        chat_response = client.post("/api/chat", json={
            "ticker": sample_ticker,
            "question": "Tell me about this company",
            "model_provider": "openai",
            "search_mode": "vector",
            "sources": "user"
        })
        
        assert chat_response.status_code == status.HTTP_200_OK
        chat_data = chat_response.json()
        assert len(chat_data["answer"]) > 0


class TestMultiAgentPipeline:
    """Test multi-agent pipeline integration."""
    
    @pytest.mark.slow
    def test_different_question_types(self, client, sample_ticker):
        """Test pipeline handles different question types."""
        questions = [
            ("What are the risks?", "risk_analysis"),
            ("What was the revenue?", "financial_metrics"),
            ("How has it changed?", "trend_analysis"),
        ]
        
        for question, expected_type in questions:
            response = client.post("/api/chat", json={
                "ticker": sample_ticker,
                "question": question,
                "model_provider": "openai",
                "search_mode": "vector",
                "sources": "both"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "answer" in data
            assert len(data["answer"]) > 0

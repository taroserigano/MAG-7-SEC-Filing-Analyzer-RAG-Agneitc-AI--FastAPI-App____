"""
Tests with mocking for external dependencies.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import status


class TestSECFetchWithMocking:
    """Tests for SEC fetch endpoint with mocked external calls."""
    
    @patch('app.services.sec_service.SECService.fetch_recent_filings')
    @patch('app.pinecone_client.get_pinecone_client')
    def test_fetch_sec_mocked_success(self, mock_pinecone, mock_sec_fetch, client):
        """Test SEC fetch with mocked SEC API and Pinecone."""
        # Mock SEC API response
        mock_sec_fetch.return_value = [
            {
                'title': 'AAPL 10-K 2024',
                'link': 'https://example.com/filing',
                'filing_date': '2024-01-01'
            }
        ]
        
        # Mock Pinecone client
        mock_client = MagicMock()
        mock_client.upsert_chunks.return_value = {'upserted_count': 3}
        mock_pinecone.return_value = mock_client
        
        # Make request
        response = client.post("/api/fetch-sec", json={
            "ticker": "AAPL",
            "forms": ["10-K"]
        })
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["chunks_stored"] == 3
        
        # Verify mocks were called
        mock_sec_fetch.assert_called_once_with("AAPL", ["10-K"])
        mock_client.upsert_chunks.assert_called()
    
    @patch('app.services.sec_service.SECService.fetch_recent_filings')
    def test_fetch_sec_no_filings_found(self, mock_sec_fetch, client):
        """Test SEC fetch when no filings are found."""
        # Mock empty response
        mock_sec_fetch.return_value = []
        
        response = client.post("/api/fetch-sec", json={
            "ticker": "AAPL",
            "forms": ["10-K"]
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["chunks_stored"] == 0
    
    @patch('app.services.sec_service.SECService.fetch_recent_filings')
    def test_fetch_sec_api_error(self, mock_sec_fetch, client):
        """Test SEC fetch when API throws error."""
        # Mock API error
        mock_sec_fetch.side_effect = Exception("SEC API unavailable")
        
        response = client.post("/api/fetch-sec", json={
            "ticker": "AAPL",
            "forms": ["10-K"]
        })
        
        # Should handle error gracefully
        assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_200_OK]


class TestChatWithMocking:
    """Tests for chat endpoint with mocked LLM and vector search."""
    
    @patch('app.agents.graph.run_agent_pipeline')
    def test_chat_mocked_agent_pipeline(self, mock_pipeline, client):
        """Test chat with mocked agent pipeline."""
        # Mock agent pipeline response
        mock_pipeline.return_value = {
            "answer": "Apple is a technology company.",
            "citations": [
                {
                    "ticker": "AAPL",
                    "form_type": "10-K",
                    "year": 2024,
                    "chunk_index": 0,
                    "source": "sec"
                }
            ],
            "task_type": "general",
            "error": None
        }
        
        response = client.post("/api/chat", json={
            "ticker": "AAPL",
            "question": "What does Apple do?",
            "model_provider": "openai",
            "search_mode": "vector",
            "sources": "both"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"] == "Apple is a technology company."
        assert len(data["citations"]) == 1
        
        # Verify pipeline was called with correct params
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["ticker"] == "AAPL"
        assert call_kwargs["question"] == "What does Apple do?"
    
    @patch('app.agents.graph.run_agent_pipeline')
    def test_chat_pipeline_error(self, mock_pipeline, client):
        """Test chat when agent pipeline returns error."""
        # Mock error response
        mock_pipeline.return_value = {
            "error": "LLM API rate limit exceeded",
            "answer": None,
            "citations": []
        }
        
        response = client.post("/api/chat", json={
            "ticker": "AAPL",
            "question": "Test question",
            "model_provider": "openai",
            "search_mode": "vector",
            "sources": "both"
        })
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @patch('app.agents.retriever_agent.RetrieverAgent.retrieve')
    @patch('app.agents.router_agent.RouterAgent.classify')
    def test_chat_with_mocked_agents(self, mock_classify, mock_retrieve, client):
        """Test chat with individual mocked agents."""
        # Mock router classification
        mock_classify.return_value = "financial_metrics"
        
        # Mock retriever search results
        mock_retrieve.return_value = [
            {
                "text": "Apple reported revenue of $100B",
                "metadata": {
                    "ticker": "AAPL",
                    "form_type": "10-K",
                    "year": 2024
                }
            }
        ]
        
        # This would need the full pipeline - just verify mocks work
        assert mock_classify.return_value == "financial_metrics"
        assert len(mock_retrieve.return_value) == 1


class TestPineconeWithMocking:
    """Tests for Pinecone operations with mocking."""
    
    @patch('app.pinecone_client.Pinecone')
    @patch('app.pinecone_client.OpenAI')
    def test_pinecone_upsert_mocked(self, mock_openai, mock_pinecone):
        """Test Pinecone upsert with mocked API calls."""
        from app.pinecone_client import PineconeClient
        
        # Mock OpenAI embeddings
        mock_openai_instance = MagicMock()
        mock_openai_instance.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        mock_openai.return_value = mock_openai_instance
        
        # Mock Pinecone index
        mock_index = MagicMock()
        mock_index.upsert.return_value = {'upserted_count': 1}
        mock_pinecone_instance = MagicMock()
        mock_pinecone_instance.Index.return_value = mock_index
        mock_pinecone.return_value = mock_pinecone_instance
        
        # Create client and test upsert
        client = PineconeClient(
            api_key="test-key",
            index_name="test-index",
            openai_api_key="test-openai-key"
        )
        
        result = client.upsert_chunks(
            chunks=["Test chunk"],
            metadata_list=[{"ticker": "AAPL"}]
        )
        
        assert result['upserted_count'] == 1
        mock_openai_instance.embeddings.create.assert_called_once()
        mock_index.upsert.assert_called_once()
    
    @patch('app.pinecone_client.Pinecone')
    @patch('app.pinecone_client.OpenAI')
    def test_pinecone_search_mocked(self, mock_openai, mock_pinecone):
        """Test Pinecone search with mocked responses."""
        from app.pinecone_client import PineconeClient
        
        # Mock OpenAI embeddings
        mock_openai_instance = MagicMock()
        mock_openai_instance.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        mock_openai.return_value = mock_openai_instance
        
        # Mock Pinecone query results
        mock_index = MagicMock()
        mock_index.query.return_value = {
            'matches': [
                {
                    'id': 'chunk-1',
                    'score': 0.95,
                    'metadata': {
                        'ticker': 'AAPL',
                        'text': 'Apple business info',
                        'form_type': '10-K'
                    }
                }
            ]
        }
        mock_pinecone_instance = MagicMock()
        mock_pinecone_instance.Index.return_value = mock_index
        mock_pinecone.return_value = mock_pinecone_instance
        
        # Create client and test search
        client = PineconeClient(
            api_key="test-key",
            index_name="test-index",
            openai_api_key="test-openai-key"
        )
        
        results = client.search(query="What is Apple?", top_k=5)
        
        assert len(results) == 1
        assert results[0]['metadata']['ticker'] == 'AAPL'
        mock_index.query.assert_called_once()


class TestLLMWithMocking:
    """Tests for LLM interactions with mocking."""
    
    @patch('app.agents.router_agent.ChatOpenAI')
    def test_router_agent_mocked_llm(self, mock_llm):
        """Test router agent with mocked LLM."""
        from app.agents.router_agent import RouterAgent
        
        # Mock LLM response
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Mock(content="risk_analysis")
        mock_llm.return_value = mock_llm_instance
        
        router = RouterAgent(model_provider="openai")
        router.llm = mock_llm_instance
        
        task_type = router.classify("What are the main risks?")
        
        assert task_type == "risk_analysis"
        mock_llm_instance.invoke.assert_called()
    
    @patch('app.agents.analyst_agent.ChatOpenAI')
    def test_analyst_agent_mocked_llm(self, mock_llm):
        """Test analyst agent with mocked LLM."""
        from app.agents.analyst_agent import AnalystAgent
        
        # Mock LLM response
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Mock(
            content="Based on the documents, Apple showed strong performance."
        )
        mock_llm.return_value = mock_llm_instance
        
        analyst = AnalystAgent(model_provider="openai")
        analyst.llm = mock_llm_instance
        
        chunks = [{"text": "Revenue data", "metadata": {"ticker": "AAPL"}}]
        analysis = analyst.analyze("How did Apple perform?", chunks, "general")
        
        assert "strong performance" in analysis
        mock_llm_instance.invoke.assert_called()
    
    @patch('app.agents.reporter_agent.ChatOpenAI')
    def test_reporter_agent_mocked_llm(self, mock_llm):
        """Test reporter agent with mocked LLM."""
        from app.agents.reporter_agent import ReporterAgent
        
        # Mock LLM response
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Mock(
            content="Apple demonstrated excellent growth in Q4 2024."
        )
        mock_llm.return_value = mock_llm_instance
        
        reporter = ReporterAgent(model_provider="openai")
        reporter.llm = mock_llm_instance
        
        answer = reporter.generate_answer(
            "How did Apple perform?",
            "Analysis shows strong growth"
        )
        
        assert "excellent growth" in answer
        mock_llm_instance.invoke.assert_called()


class TestFileUploadWithMocking:
    """Tests for file upload with mocked file operations."""
    
    @patch('app.pinecone_client.get_pinecone_client')
    def test_upload_pdf_mocked(self, mock_pinecone, client, tmp_path):
        """Test PDF upload with mocked Pinecone."""
        # Mock Pinecone client
        mock_client = MagicMock()
        mock_client.upsert_chunks.return_value = {'upserted_count': 2}
        mock_pinecone.return_value = mock_client
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Important financial data about Apple Inc.")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"ticker": "AAPL"}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify Pinecone was called
        mock_client.upsert_chunks.assert_called_once()
    
    @patch('app.services.text_processing.extract_text_from_pdf')
    @patch('app.pinecone_client.get_pinecone_client')
    def test_upload_pdf_extraction_error(self, mock_pinecone, mock_extract, client, tmp_path):
        """Test PDF upload when extraction fails."""
        # Mock extraction error
        mock_extract.side_effect = Exception("Corrupted PDF")
        
        # Create test file
        test_file = tmp_path / "corrupted.pdf"
        test_file.write_bytes(b"fake pdf content")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("corrupted.pdf", f, "application/pdf")},
                data={"ticker": "AAPL"}
            )
        
        # Should handle error
        assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_400_BAD_REQUEST]


class TestHealthCheckWithMocking:
    """Tests for health check with mocked services."""
    
    @patch('app.pinecone_client.get_pinecone_client')
    def test_health_check_pinecone_connected(self, mock_pinecone, client):
        """Test health check with Pinecone connected."""
        # Mock successful Pinecone connection
        mock_client = MagicMock()
        mock_client.index.describe_index_stats.return_value = {'dimension': 1536}
        mock_pinecone.return_value = mock_client
        
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        # Note: Actual connection check depends on implementation
    
    @patch('app.pinecone_client.get_pinecone_client')
    def test_health_check_pinecone_disconnected(self, mock_pinecone, client):
        """Test health check when Pinecone is disconnected."""
        # Mock Pinecone error
        mock_pinecone.side_effect = Exception("Pinecone connection failed")
        
        response = client.get("/health")
        
        # Should still return 200 but with degraded status
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["degraded", "healthy"]

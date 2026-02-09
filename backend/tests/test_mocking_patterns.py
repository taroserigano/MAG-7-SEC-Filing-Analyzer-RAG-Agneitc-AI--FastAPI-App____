"""
Advanced mocking examples and patterns.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call, PropertyMock
from datetime import datetime
from fastapi import status


class TestMockingPatterns:
    """Examples of different mocking patterns."""
    
    def test_basic_mock(self):
        """Basic mock object usage."""
        # Create a mock
        mock_service = Mock()
        
        # Configure return value
        mock_service.get_data.return_value = {"key": "value"}
        
        # Call the mock
        result = mock_service.get_data()
        
        # Assert
        assert result == {"key": "value"}
        mock_service.get_data.assert_called_once()
    
    def test_mock_with_side_effect(self):
        """Mock with side_effect for multiple calls."""
        mock_service = Mock()
        
        # Different return values for successive calls
        mock_service.fetch.side_effect = [
            {"result": "first"},
            {"result": "second"},
            {"result": "third"}
        ]
        
        assert mock_service.fetch() == {"result": "first"}
        assert mock_service.fetch() == {"result": "second"}
        assert mock_service.fetch() == {"result": "third"}
        assert mock_service.fetch.call_count == 3
    
    def test_mock_with_exception(self):
        """Mock that raises an exception."""
        mock_service = Mock()
        mock_service.risky_operation.side_effect = ValueError("Something went wrong")
        
        with pytest.raises(ValueError, match="Something went wrong"):
            mock_service.risky_operation()
    
    def test_magic_mock_with_context_manager(self):
        """MagicMock supports context managers."""
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = "file contents"
        
        with mock_file as f:
            content = f.read()
        
        assert content == "file contents"
        mock_file.__enter__.assert_called_once()
        mock_file.__exit__.assert_called_once()
    
    def test_mock_chaining(self):
        """Mock with chained method calls."""
        mock_db = MagicMock()
        mock_db.collection.find.return_value.limit.return_value = [
            {"id": 1, "name": "test"}
        ]
        
        results = mock_db.collection.find({"status": "active"}).limit(10)
        
        assert len(results) == 1
        assert results[0]["name"] == "test"
    
    def test_assert_called_with(self):
        """Verify mock was called with specific arguments."""
        mock_service = Mock()
        mock_service.process("data", flag=True)
        
        # Verify exact call
        mock_service.process.assert_called_once_with("data", flag=True)
        
        # Verify any call
        mock_service.process.assert_any_call("data", flag=True)
    
    def test_assert_call_order(self):
        """Verify order of multiple mock calls."""
        mock_service = Mock()
        
        mock_service.step1()
        mock_service.step2()
        mock_service.step3()
        
        # Verify call order
        expected_calls = [call.step1(), call.step2(), call.step3()]
        assert mock_service.mock_calls == expected_calls


class TestPatchDecorator:
    """Examples of @patch decorator usage."""
    
    @patch('app.services.sec_service.requests')
    def test_patch_external_library(self, mock_requests):
        """Patch external library (requests)."""
        # Configure mock
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        # Test code that uses requests
        # This would be your actual service code
        assert mock_requests.get.return_value.status_code == 200
    
    @patch('app.pinecone_client.OpenAI')
    @patch('app.pinecone_client.Pinecone')
    def test_multiple_patches(self, mock_pinecone, mock_openai):
        """Multiple patches (note: decorators apply bottom-to-top)."""
        # Configure both mocks
        mock_openai.return_value = MagicMock()
        mock_pinecone.return_value = MagicMock()
        
        # Both are available
        assert mock_openai is not None
        assert mock_pinecone is not None
    
    def test_patch_object(self):
        """Patch specific method on an object."""
        obj = Mock()
        obj.method_to_patch = Mock(return_value="original")
        
        with patch.object(obj, 'method_to_patch', return_value="patched"):
            # Test code using the patched method
            assert obj.method_to_patch() == "patched"


class TestContextManagerPatching:
    """Examples of patching with context managers."""
    
    def test_patch_context_manager(self):
        """Use patch as context manager."""
        with patch('app.services.sec_service.SECService') as MockSECService:
            # Configure mock
            mock_instance = MockSECService.return_value
            mock_instance.fetch_recent_filings.return_value = [{"filing": "data"}]
            
            # Test code
            service = MockSECService()
            result = service.fetch_recent_filings("AAPL", ["10-K"])
            
            assert result == [{"filing": "data"}]
            mock_instance.fetch_recent_filings.assert_called_once_with("AAPL", ["10-K"])
    
    def test_patch_dict(self):
        """Patch dictionary values."""
        original_dict = {"key": "original"}
        
        with patch.dict(original_dict, {"key": "modified", "new": "value"}):
            assert original_dict["key"] == "modified"
            assert original_dict["new"] == "value"
        
        # Restored after context
        assert original_dict["key"] == "original"
        assert "new" not in original_dict
    
    def test_patch_environment_variables(self):
        """Patch environment variables."""
        import os
        
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            assert os.environ["TEST_VAR"] == "test_value"
        
        # Cleaned up after context
        assert "TEST_VAR" not in os.environ


class TestAsyncMocking:
    """Examples of mocking async code."""
    
    @pytest.mark.asyncio
    async def test_async_mock(self):
        """Mock async function."""
        mock_async_func = AsyncMock(return_value="async result")
        
        result = await mock_async_func()
        
        assert result == "async result"
        mock_async_func.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Mock async context manager."""
        mock_async_cm = MagicMock()
        mock_async_cm.__aenter__ = AsyncMock(return_value="entered")
        mock_async_cm.__aexit__ = AsyncMock()
        
        async with mock_async_cm as value:
            assert value == "entered"
        
        mock_async_cm.__aenter__.assert_awaited_once()
        mock_async_cm.__aexit__.assert_awaited_once()


class TestSpyPattern:
    """Spy pattern - partial mocking."""
    
    def test_spy_real_method_tracking(self):
        """Track calls to real methods."""
        class RealService:
            def calculate(self, x, y):
                return x + y
        
        service = RealService()
        
        # Wrap with Mock to spy on calls
        with patch.object(service, 'calculate', wraps=service.calculate) as spy:
            result = service.calculate(2, 3)
            
            # Real method was called
            assert result == 5
            
            # But we can verify the call
            spy.assert_called_once_with(2, 3)


class TestMockingBestPractices:
    """Best practices and common patterns."""
    
    def test_verify_mock_not_called(self):
        """Verify mock was NOT called."""
        mock_service = Mock()
        
        # Do something that shouldn't call the mock
        # ...
        
        mock_service.dangerous_operation.assert_not_called()
    
    def test_reset_mock(self):
        """Reset mock between tests."""
        mock_service = Mock()
        
        mock_service.operation()
        assert mock_service.operation.call_count == 1
        
        # Reset
        mock_service.reset_mock()
        
        assert mock_service.operation.call_count == 0
    
    def test_configure_mock_spec(self):
        """Use spec to restrict mock to actual interface."""
        class RealService:
            def real_method(self):
                pass
        
        # Mock with spec - only allows real methods
        mock_service = Mock(spec=RealService)
        
        # This works
        mock_service.real_method()
        
        # This would raise AttributeError
        # mock_service.fake_method()  # Uncomment to see error
    
    def test_mock_property(self):
        """Mock a property."""
        mock_obj = Mock()
        
        # Configure property
        type(mock_obj).my_property = PropertyMock(return_value="property value")
        
        assert mock_obj.my_property == "property value"
    
    def test_mock_with_spec_set(self):
        """spec_set prevents setting attributes not in original."""
        class RealClass:
            existing_attr = "value"
        
        mock_obj = Mock(spec_set=RealClass)
        
        # Can set existing attribute
        mock_obj.existing_attr = "new value"
        
        # Would raise AttributeError for non-existent attribute
        # mock_obj.fake_attr = "test"  # Uncomment to see error


class TestMockingComplexScenarios:
    """Complex real-world mocking scenarios."""
    
    @patch('app.agents.graph.create_agent_graph')
    @patch('app.pinecone_client.get_pinecone_client')
    def test_full_chat_workflow_mocked(self, mock_pinecone, mock_graph, client):
        """Test complete chat workflow with all dependencies mocked."""
        # Mock Pinecone
        mock_pc_client = MagicMock()
        mock_pc_client.search.return_value = [
            {
                "text": "Apple business info",
                "metadata": {"ticker": "AAPL", "form_type": "10-K"}
            }
        ]
        mock_pinecone.return_value = mock_pc_client
        
        # Mock agent graph
        mock_graph_instance = MagicMock()
        mock_graph_instance.invoke.return_value = {
            "answer": "Apple is a tech company",
            "citations": [{"ticker": "AAPL", "form_type": "10-K", "year": 2024}],
            "error": None
        }
        mock_graph.return_value = mock_graph_instance
        
        # Make request
        response = client.post("/api/chat", json={
            "ticker": "AAPL",
            "question": "What is Apple?",
            "model_provider": "openai",
            "search_mode": "vector",
            "sources": "both"
        })
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
    
    def test_mock_with_dynamic_behavior(self):
        """Mock with behavior that changes based on input."""
        def side_effect_func(ticker):
            if ticker == "AAPL":
                return {"name": "Apple Inc."}
            elif ticker == "MSFT":
                return {"name": "Microsoft Corp."}
            else:
                raise ValueError(f"Unknown ticker: {ticker}")
        
        mock_service = Mock()
        mock_service.get_company.side_effect = side_effect_func
        
        assert mock_service.get_company("AAPL") == {"name": "Apple Inc."}
        assert mock_service.get_company("MSFT") == {"name": "Microsoft Corp."}
        
        with pytest.raises(ValueError, match="Unknown ticker: INVALID"):
            mock_service.get_company("INVALID")

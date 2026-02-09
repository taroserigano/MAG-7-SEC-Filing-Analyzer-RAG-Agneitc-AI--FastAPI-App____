"""
Pytest configuration and fixtures for MAG7 SEC Filings Analyzer tests.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    # Import lazily to avoid pulling heavy dependencies (Pinecone, transformers)
    # when tests do not need the API layer.
    from app.main import app  # local import keeps unrelated unit tests fast

    return TestClient(app)


@pytest.fixture
def sample_ticker():
    """Sample ticker for testing."""
    return "AAPL"


@pytest.fixture
def sample_question():
    """Sample question for chat testing."""
    return "What are the main risk factors?"


@pytest.fixture
def sample_chat_request(sample_ticker, sample_question):
    """Sample chat request payload."""
    return {
        "ticker": sample_ticker,
        "question": sample_question,
        "model_provider": "openai",
        "search_mode": "vector",
        "sources": "both"
    }


@pytest.fixture
def sample_sec_request(sample_ticker):
    """Sample SEC fetch request payload."""
    return {
        "ticker": sample_ticker,
        "forms": ["10-K"]
    }


@pytest.fixture
def mock_sec_service(tmp_path):
    """Mock SEC service with temporary cache directory."""
    from app.services.sec_service import SECService
    
    # Create temp cache dir
    cache_dir = tmp_path / "sec_cache"
    cache_dir.mkdir()
    
    # Create SECService with temp cache dir
    return SECService(cache_dir=str(cache_dir))


@pytest.fixture
def mock_sec_service_with_cache(mock_sec_service):
    """Mock SEC service with pre-populated cache files."""
    cache_dir = mock_sec_service.cache_dir
    
    # Create sample cached files for AAPL
    sample_md_content = """# Apple Inc. 2024 Form 10-K

## Company Overview
Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.

## Financial Highlights
- Total net sales: $391.0 billion
- Net income: $93.7 billion
- Operating income: $123.2 billion

## Risk Factors
The Company is subject to various legal proceedings and claims."""
    
    sample_txt_content = """Apple Inc. 2024 Form 10-K

Company Overview
Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.

Financial Highlights
- Total net sales: $391.0 billion
- Net income: $93.7 billion
- Operating income: $123.2 billion

Risk Factors
The Company is subject to various legal proceedings and claims."""
    
    # Write files
    (cache_dir / "AAPL_10-K_2024.md").write_text(sample_md_content)
    (cache_dir / "AAPL_10-K_2024.txt").write_text(sample_txt_content)
    
    return mock_sec_service

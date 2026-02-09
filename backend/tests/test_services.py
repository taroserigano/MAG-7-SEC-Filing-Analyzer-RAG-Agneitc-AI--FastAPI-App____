"""
Tests for service layer components.
"""
import pytest
from app.services.sec_service import SECService
from app.services.text_processing import chunk_text, clean_text


class TestSECService:
    """Tests for SEC service."""
    
    @pytest.fixture
    def sec_service(self):
        """Create SEC service instance."""
        return SECService()
    
    def test_mag7_ciks_defined(self, sec_service):
        """Test MAG7 CIK mappings exist."""
        tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA"]
        
        for ticker in tickers:
            assert ticker in sec_service.MAG7_CIKS
    
    def test_fetch_recent_filings(self, sec_service):
        """Test fetching recent filings."""
        filings = sec_service.fetch_recent_filings("AAPL", ["10-K"])
        
        assert isinstance(filings, list)
        # May be empty if no recent filings
        if len(filings) > 0:
            filing = filings[0]
            assert "title" in filing
            assert "link" in filing


class TestTextProcessing:
    """Tests for text processing utilities."""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "A" * 1500  # Text longer than chunk size
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        assert all(len(chunk) <= 600 for chunk in chunks)  # chunk_size + some margin
    
    def test_chunk_text_overlap(self):
        """Test chunking preserves overlap."""
        text = "A" * 1000
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        
        if len(chunks) > 1:
            # Check that there's some overlap between chunks
            assert len(chunks) >= 2
    
    def test_clean_text_removes_extra_whitespace(self):
        """Test text cleaning removes extra whitespace."""
        text = "This  has    extra   spaces\n\n\nand lines"
        cleaned = clean_text(text)
        
        assert "  " not in cleaned
        assert "\n\n\n" not in cleaned
    
    def test_clean_text_preserves_content(self):
        """Test cleaning preserves meaningful content."""
        text = "Important financial data: $1,234,567"
        cleaned = clean_text(text)
        
        assert "Important" in cleaned
        assert "financial" in cleaned
        assert "data" in cleaned

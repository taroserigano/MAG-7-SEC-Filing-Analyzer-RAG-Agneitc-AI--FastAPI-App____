"""
Integration tests for SEC preview endpoint with actual network calls
"""
import pytest
import requests
import time


def wait_for_backend(max_retries=10):
    """Wait for backend to be ready"""
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
    return False


def test_backend_health():
    """Test that backend is running and healthy"""
    assert wait_for_backend(), "Backend is not running on port 8000"
    
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Backend health check passed")


def test_preview_endpoint_cors():
    """Test that CORS headers are properly set"""
    response = requests.get(
        "http://localhost:8000/api/sec-preview/AAPL?format=markdown",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    # CORS headers should be present
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]
    print("✅ CORS headers present")


def test_preview_aapl_markdown():
    """Test preview endpoint for AAPL in markdown format"""
    response = requests.get("http://localhost:8000/api/sec-preview/AAPL?format=markdown")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["format"] == "markdown"
    assert len(data["content"]) > 1000
    assert "Apple" in data["content"]
    print(f"✅ AAPL markdown preview: {len(data['content'])} characters")


def test_preview_aapl_text():
    """Test preview endpoint for AAPL in text format"""
    response = requests.get("http://localhost:8000/api/sec-preview/AAPL?format=text")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["format"] == "text"
    assert len(data["content"]) > 1000
    print(f"✅ AAPL text preview: {len(data['content'])} characters")


def test_preview_not_cached():
    """Test preview for uncached ticker returns 404"""
    response = requests.get("http://localhost:8000/api/sec-preview/INVALID?format=markdown")
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data
    assert "INVALID" in data["detail"]
    print("✅ Uncached ticker returns 404")


def test_preview_invalid_format():
    """Test preview with invalid format returns 400"""
    response = requests.get("http://localhost:8000/api/sec-preview/AAPL?format=invalid")
    assert response.status_code == 400
    print("✅ Invalid format returns 400")


def test_preview_frontend_fetch_simulation():
    """Simulate exact frontend fetch request"""
    # This is exactly how the frontend fetches
    try:
        response = requests.get(
            "http://localhost:8000/api/sec-preview/AAPL?format=markdown",
            headers={
                "Origin": "http://localhost:5173",
                "Accept": "application/json"
            },
            timeout=5
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0
        print("✅ Frontend fetch simulation successful")
    except requests.exceptions.ConnectionError:
        pytest.fail("❌ Connection error - backend not reachable")
    except requests.exceptions.Timeout:
        pytest.fail("❌ Request timeout")


if __name__ == "__main__":
    print("Running integration tests...\n")
    
    print("1. Testing backend health...")
    test_backend_health()
    
    print("\n2. Testing CORS headers...")
    test_preview_endpoint_cors()
    
    print("\n3. Testing AAPL markdown preview...")
    test_preview_aapl_markdown()
    
    print("\n4. Testing AAPL text preview...")
    test_preview_aapl_text()
    
    print("\n5. Testing uncached ticker...")
    test_preview_not_cached()
    
    print("\n6. Testing invalid format...")
    test_preview_invalid_format()
    
    print("\n7. Testing frontend fetch simulation...")
    test_preview_frontend_fetch_simulation()
    
    print("\n✅ All integration tests passed!")

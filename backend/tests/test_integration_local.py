"""
Lightweight integration-style tests with local mocks to cover upload, chat, and SEC fetch paths
without hitting external services.
"""
import io
import pytest
from fastapi import status


class FakePinecone:
    def __init__(self):
        self.upserts = []
        self.search_calls = []

    def is_connected(self):
        return True

    def upsert_chunks(self, chunks, metadata_list, namespace=""):
        self.upserts.append({"chunks": chunks, "metadata": metadata_list, "namespace": namespace})
        return {"upserted_count": len(chunks)}

    def search(self, query, top_k=5, filter_dict=None, namespace=""):
        self.search_calls.append({"query": query, "filter": filter_dict, "namespace": namespace})
        return [
            {
                "id": "fake-id",
                "score": 0.42,
                "metadata": {
                    "ticker": filter_dict.get("ticker") if filter_dict else "unknown",
                    "source": filter_dict.get("source") if filter_dict else "sec",
                    "chunk_index": 0,
                    "text": "capacity tight; lead times 20-22 weeks; margin supported by HGX mix",
                },
                "text": "capacity tight; lead times 20-22 weeks; margin supported by HGX mix",
            }
        ]

    def hybrid_search(self, query, top_k=5, filter_dict=None, keyword=None, namespace=""):
        return self.search(query=query, top_k=top_k, filter_dict=filter_dict, namespace=namespace)


class FakeSECService:
    def __init__(self, *args, **kwargs):
        pass

    def fetch_recent_filings(self, ticker, form_types=None, count=3):
        return [
            {
                "ticker": ticker,
                "form_type": form_types[0] if form_types else "10-K",
                "filing_date": "2024-12-31",
                "title": "Test Filing",
                "link": "http://example.com/filing",
                "year": 2024,
            }
        ]

    def fetch_filing_text(self, filing_url):
        return "This is a filing body about demand and supply."

    def extract_sections(self, text, form_type):
        return {"full_text": text}


@pytest.fixture
def fake_pinecone(monkeypatch):
    from app import main
    from app import pinecone_client

    fake = FakePinecone()
    monkeypatch.setattr(main, "get_pinecone_client", lambda: fake)
    monkeypatch.setattr(pinecone_client, "get_pinecone_client", lambda: fake)
    return fake


@pytest.fixture
def fake_sec(monkeypatch):
    import app.main

    monkeypatch.setattr(app.main, "SECService", lambda: FakeSECService())
    return FakeSECService()


@pytest.fixture
def fake_agent_pipeline(monkeypatch):
    import app.agents.graph

    async def _fake_pipeline(**kwargs):
        return {
            "answer": "capacity tight; lead times ~20-22 weeks; margins supported by HGX mix",
            "citations": [
                {
                    "ticker": kwargs.get("ticker", "NVDA"),
                    "form_type": None,
                    "year": None,
                    "chunk_index": 0,
                    "source": kwargs.get("sources", "user"),
                }
            ],
        }

    monkeypatch.setattr(app.agents.graph, "run_agent_pipeline", _fake_pipeline)
    return _fake_pipeline


class TestUploadFlow:
    def test_upload_sets_ticker_metadata(self, client, fake_pinecone):
        payload = io.BytesIO(b"NVDA AI Data Center Brief")
        response = client.post(
            "/api/upload",
            files={"file": ("nvda_brief.md", payload, "text/markdown")},
            data={"ticker": "NVDA"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True
        assert fake_pinecone.upserts
        metadata = fake_pinecone.upserts[-1]["metadata"][0]
        assert metadata["ticker"] == "NVDA"
        assert metadata["source"] == "user"


class TestChatFlow:
    def test_chat_uses_user_source_and_returns_citation(self, client, fake_pinecone, fake_agent_pipeline):
        payload = {
            "ticker": "NVDA",
            "question": "Summarize supply and demand signals",
            "model_provider": "ollama",
            "search_mode": "vector",
            "sources": "user",
        }
        response = client.post("/api/chat", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["citations"]
        cite = data["citations"][0]
        assert cite["ticker"] == "NVDA"
        assert cite["source"] == "user"
        assert "lead times" in data["answer"].lower()


class TestSECFetchFlow:
    def test_fetch_sec_uses_cache_and_upserts(self, client, fake_pinecone, fake_sec):
        body = {"ticker": "AAPL", "forms": ["10-K"]}
        response = client.post("/api/fetch-sec", json=body)

        assert response.status_code == status.HTTP_200_OK
        assert fake_pinecone.upserts
        assert fake_pinecone.search_calls
        assert fake_pinecone.search_calls[0]["filter"] == {"filing_id": "AAPL_10-K_2024-12-31"}

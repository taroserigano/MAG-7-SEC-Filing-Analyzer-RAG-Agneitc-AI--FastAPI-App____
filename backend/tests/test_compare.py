import pathlib
import sys
import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def test_compare_requires_two_tickers(client: TestClient):
    payload = {
        "tickers": ["AAPL"],
        "question": "Compare",
    }
    response = client.post("/api/compare", json=payload)
    assert response.status_code == 400
    assert "At least two tickers" in response.json()["detail"] or "Provide two or more" in response.json()["detail"]


def test_compare_returns_results(monkeypatch, client: TestClient):
    calls = []

    async def fake_run_agent_pipeline(**kwargs):
        calls.append(kwargs["ticker"])
        return {
            "answer": f"Answer for {kwargs['ticker']}",
            "retrieval_flags": {
                "enable_rerank": False,
                "enable_query_rewrite": False,
                "enable_retrieval_cache": True,
                "enable_section_boost": False,
                "reranker_model": "builtin",
            },
            "cache_hit": True,
        }

    monkeypatch.setattr("app.agents.graph.run_agent_pipeline", fake_run_agent_pipeline, raising=False)

    payload = {
        "tickers": ["AAPL", "NVDA"],
        "question": "Compare growth",
        "model_provider": "openai",
        "search_mode": "vector",
        "sources": "both",
    }

    response = client.post("/api/compare", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["results"]) == 2
    tickers = {r["ticker"] for r in data["results"]}
    assert tickers == {"AAPL", "NVDA"}
    assert "AAPL: Answer for AAPL" in data["combined_answer"]
    assert all(r["cache_hit"] for r in data["results"])
    assert calls == ["AAPL", "NVDA"]

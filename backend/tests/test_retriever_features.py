import types


def make_settings(**overrides):
    defaults = dict(
        enable_rerank=False,
        enable_query_rewrite=False,
        enable_retrieval_cache=False,
        retrieval_cache_ttl_seconds=300,
        rerank_top_k=10,
        enable_section_boost=False,
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def test_rerank_reorders_results(monkeypatch):
    import app.agents.retriever_agent as ra
    from app.agents.retriever_agent import RetrieverAgent

    monkeypatch.setattr(ra, "_RETRIEVAL_CACHE", {})
    monkeypatch.setattr(ra, "get_settings", lambda: make_settings(enable_rerank=True, rerank_top_k=1))

    class FakeClient:
        def search(self, query, top_k, filter_dict):
            return [
                {"id": "b", "text": "growth margin expansion"},
                {"id": "a", "text": "unrelated content"},
            ]

        def hybrid_search(self, query, top_k, filter_dict):
            return []

    monkeypatch.setattr(ra, "get_pinecone_client", lambda: FakeClient())

    agent = RetrieverAgent()
    results = agent.retrieve("margin", "AAPL", top_k=2, task_type="general")
    assert results[0]["id"] == "b"  # rerank should surface the overlapping chunk first


def test_retrieval_cache_prevents_duplicate_queries(monkeypatch):
    import app.agents.retriever_agent as ra
    from app.agents.retriever_agent import RetrieverAgent

    monkeypatch.setattr(ra, "_RETRIEVAL_CACHE", {})
    monkeypatch.setattr(ra, "get_settings", lambda: make_settings(enable_retrieval_cache=True, retrieval_cache_ttl_seconds=100))

    class CountingClient:
        def __init__(self):
            self.calls = 0

        def search(self, query, top_k, filter_dict):
            self.calls += 1
            return [{"id": "x", "text": "cached result"}]

        def hybrid_search(self, query, top_k, filter_dict):
            return []

    client = CountingClient()
    monkeypatch.setattr(ra, "get_pinecone_client", lambda: client)

    agent = RetrieverAgent()
    first = agent.retrieve("demand", "AAPL", top_k=5)
    second = agent.retrieve("demand", "AAPL", top_k=5)

    assert client.calls == 1  # second call should hit cache
    assert first == second


def test_overrides_enable_rerank_without_global_flag(monkeypatch):
    import app.agents.retriever_agent as ra
    from app.agents.retriever_agent import RetrieverAgent

    monkeypatch.setattr(ra, "_RETRIEVAL_CACHE", {})
    monkeypatch.setattr(ra, "get_settings", lambda: make_settings(enable_rerank=False))

    class FakeClient:
        def search(self, query, top_k, filter_dict):
            return [
                {"id": "a", "text": "unrelated content"},
                {"id": "b", "text": "margin expansion"},
            ]

        def hybrid_search(self, query, top_k, filter_dict):
            return []

    monkeypatch.setattr(ra, "get_pinecone_client", lambda: FakeClient())

    agent = RetrieverAgent()
    results = agent.retrieve(
        "margin",
        "AAPL",
        overrides={"enable_rerank": True, "enable_query_rewrite": False},
        top_k=2,
    )

    assert results[0]["id"] == "b"

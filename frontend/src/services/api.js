// Prefer explicit backend base; fall back to local dev backend to avoid hitting the Vite dev server.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

// Helper function to add timeout to fetch requests
const fetchWithTimeout = async (url, options = {}, timeout = 180000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw error;
  }
};

export const apiClient = {
  async healthCheck() {
    const response = await fetchWithTimeout(`${API_BASE_URL}/health`, {}, 3000);
    if (!response.ok) {
      throw new Error("Health check failed");
    }
    return response.json();
  },

  async fetchSECFilings(ticker, forms) {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/api/fetch-sec`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ticker, forms }),
      },
      30000,
    );
    if (!response.ok) {
      throw new Error("Failed to fetch SEC filings");
    }
    return response.json();
  },

  async uploadFile(file, ticker) {
    const formData = new FormData();
    formData.append("file", file);
    if (ticker) {
      formData.append("ticker", ticker);
    }

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error("Failed to upload file");
    }
    return response.json();
  },

  async chat({
    ticker,
    question,
    modelProvider,
    searchMode,
    sources,
    enable_rerank,
    enable_query_rewrite,
    enable_retrieval_cache,
    enable_section_boost,
    reranker_model,
  }) {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/api/chat`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ticker,
          question,
          model_provider: modelProvider ?? "ollama",
          search_mode: searchMode ?? "vector",
          sources: sources ?? "both",
          enable_rerank: enable_rerank ?? false,
          enable_query_rewrite: enable_query_rewrite ?? false,
          enable_retrieval_cache: enable_retrieval_cache ?? false,
          enable_section_boost: enable_section_boost ?? false,
          reranker_model: reranker_model ?? "builtin",
        }),
      },
      180000,
    );
    if (!response.ok) {
      throw new Error("Chat request failed");
    }
    return response.json();
  },

  async chatStream(payload) {
    const {
      ticker,
      question,
      modelProvider,
      searchMode,
      sources,
      enable_rerank,
      enable_query_rewrite,
      enable_retrieval_cache,
      enable_section_boost,
      reranker_model,
    } = payload;

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ticker,
        question,
        model_provider: modelProvider ?? "ollama",
        search_mode: searchMode ?? "vector",
        sources: sources ?? "both",
        enable_rerank: enable_rerank ?? false,
        enable_query_rewrite: enable_query_rewrite ?? false,
        enable_retrieval_cache: enable_retrieval_cache ?? false,
        enable_section_boost: enable_section_boost ?? false,
        reranker_model: reranker_model ?? "builtin",
        stream: true,
      }),
    });
    if (!response.ok || !response.body) {
      throw new Error("Chat stream request failed");
    }
    const reader = response.body.getReader();
    return { reader, metadata: { flags_summary: "", cache_hit: false } };
  },

  async compare({
    tickers,
    question,
    modelProvider,
    searchMode,
    sources,
    enable_rerank,
    enable_query_rewrite,
    enable_retrieval_cache,
    enable_section_boost,
    reranker_model,
  }) {
    // Compare can take longer when calling live LLMs; allow up to 10 minutes before timing out.
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/api/compare`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tickers,
          question,
          model_provider: modelProvider ?? "openai",
          search_mode: searchMode ?? "vector",
          sources: sources ?? "both",
          enable_rerank: enable_rerank ?? false,
          enable_query_rewrite: enable_query_rewrite ?? false,
          enable_retrieval_cache: enable_retrieval_cache ?? false,
          enable_section_boost: enable_section_boost ?? false,
          reranker_model: reranker_model ?? "builtin",
        }),
      },
      600000,
    );
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Compare request failed: ${errorText}`);
    }
    return response.json();
  },

  async dataAvailability(ticker) {
    const response = await fetch(
      `${API_BASE_URL}/api/data-availability?ticker=${encodeURIComponent(ticker)}`,
    );
    if (!response.ok) {
      throw new Error("Data availability check failed");
    }
    return response.json();
  },
};

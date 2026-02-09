import { useState, useCallback, useMemo } from "react";
import {
  useHealthCheck,
  useChat,
  useFetchSECFilings,
  useCompare,
} from "./hooks/useAPI";
import { TickerSelector } from "./components/TickerSelector";
import { ControlPanel } from "./components/ControlPanel";
import { ChatWindow } from "./components/ChatWindow";
import { ChatInput } from "./components/ChatInput";
import { ComparePanel } from "./components/ComparePanel";
import { apiClient } from "./services/api";
import "./App.css";

function App() {
  const { data: healthStatus } = useHealthCheck();
  const [selectedTickers, setSelectedTickers] = useState(["AAPL"]);
  const [multiSelectMode, setMultiSelectMode] = useState(false);
  const [modelProvider, setModelProvider] = useState("openai");
  const [searchMode, setSearchMode] = useState("vector");
  const sources = "both";
  const [enableRerank, setEnableRerank] = useState(false);
  const [enableQueryRewrite, setEnableQueryRewrite] = useState(false);
  const [enableRetrievalCache, setEnableRetrievalCache] = useState(true);
  const [enableSectionBoost, setEnableSectionBoost] = useState(false);

  const [messages, setMessages] = useState([]);

  const primaryTicker = useMemo(
    () => selectedTickers[0] || "",
    [selectedTickers],
  );
  const isCompareMode = useMemo(
    () => multiSelectMode && selectedTickers.length >= 2,
    [multiSelectMode, selectedTickers],
  );

  const chatMutation = useChat();
  const fetchSECMutation = useFetchSECFilings();
  const compareMutation = useCompare();

  const handleSendMessage = useCallback(
    async (question) => {
      // Check if we're in compare mode
      if (isCompareMode) {
        await handleCompare({ tickers: selectedTickers, question });
        return;
      }

      if (!primaryTicker) {
        alert("Please select a ticker first");
        return;
      }

      // Add user message
      const userMessage = {
        role: "user",
        content: question,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      const commonPayload = {
        ticker: primaryTicker,
        question,
        modelProvider,
        searchMode,
        enable_rerank: enableRerank,
        enable_query_rewrite: enableQueryRewrite,
        enable_retrieval_cache: enableRetrievalCache,
        enable_section_boost: enableSectionBoost,
        reranker_model: "builtin",
        sources,
      };

      // Send to backend
      try {
        const response = await chatMutation.mutateAsync(commonPayload);

        // Add assistant message
        const assistantMessage = {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          timestamp: new Date().toISOString(),
          flagsSummary: response.flags_summary,
          cacheHit: response.cache_hit,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        const errorMessage = {
          role: "assistant",
          content: `Error: ${error.message}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    },
    [
      isCompareMode,
      primaryTicker,
      modelProvider,
      searchMode,
      enableRerank,
      enableQueryRewrite,
      enableRetrievalCache,
      enableSectionBoost,
      sources,
      selectedTickers,
      chatMutation,
      compareMutation,
    ],
  );

  const handleFetchSEC = useCallback(async () => {
    if (!primaryTicker) {
      alert("Please select a ticker first");
      return;
    }

    try {
      await fetchSECMutation.mutateAsync({
        ticker: primaryTicker,
        forms: ["10-K", "10-Q"],
      });
      alert("SEC filings fetched successfully!");
    } catch (error) {
      alert(`Error fetching SEC filings: ${error.message}`);
    }
  }, [primaryTicker, fetchSECMutation]);

  const handleCompare = useCallback(
    async ({ tickers, question }) => {
      // Add user message for compare queries
      const userMessage = {
        role: "user",
        content: question,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        const response = await compareMutation.mutateAsync({
          tickers,
          question,
          modelProvider,
          searchMode,
          enable_rerank: enableRerank,
          enable_query_rewrite: enableQueryRewrite,
          enable_retrieval_cache: enableRetrievalCache,
          enable_section_boost: enableSectionBoost,
          reranker_model: "builtin",
          sources,
        });

        const assistantMessage = {
          role: "assistant",
          content: response.combined_answer,
          citations: [],
          timestamp: new Date().toISOString(),
          flagsSummary: response.results?.[0]?.flags_summary || "",
          isCompare: true,
          compareTickers: tickers,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        const errorMessage = {
          role: "assistant",
          content: `Compare error: ${error.message}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    },
    [
      modelProvider,
      searchMode,
      enableRerank,
      enableQueryRewrite,
      enableRetrievalCache,
      enableSectionBoost,
      sources,
      compareMutation,
    ],
  );

  const isSystemHealthy = useMemo(
    () => healthStatus?.status === "healthy",
    [healthStatus],
  );

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-icon">📊</div>
          <div>
            <h1>MAG7 SEC Filings Analyzer</h1>
            <p>AI-powered analysis using RAG and multi-agent orchestration</p>
          </div>
        </div>
        {healthStatus && (
          <div
            className={`health-indicator ${isSystemHealthy ? "healthy" : "unhealthy"}`}
          >
            {isSystemHealthy ? "System Online" : "System Offline"}
          </div>
        )}
      </header>

      <main className="app-main">
        <div className="sidebar">
          <div className="glass-card">
            <TickerSelector
              selectedTickers={selectedTickers}
              onTickerChange={setSelectedTickers}
              multiSelectMode={multiSelectMode}
              onMultiSelectModeChange={setMultiSelectMode}
            />
          </div>

          {isCompareMode && (
            <div className="compare-mode-notice">
              <span className="compare-icon">⚡</span>
              <div>
                <strong>Compare Mode Active</strong>
                <p>Comparing {selectedTickers.join(" vs ")}</p>
              </div>
            </div>
          )}

          <div className="glass-card action-section">
            <button
              className="fetch-btn"
              onClick={handleFetchSEC}
              disabled={!primaryTicker || fetchSECMutation.isPending}
            >
              {fetchSECMutation.isPending
                ? "⏳ Fetching..."
                : "🔄 Fetch SEC Filings"}
            </button>
          </div>

          <div className="glass-card">
            <ControlPanel
              modelProvider={modelProvider}
              onModelProviderChange={setModelProvider}
              searchMode={searchMode}
              onSearchModeChange={setSearchMode}
              enableRerank={enableRerank}
              onToggleRerank={setEnableRerank}
              enableQueryRewrite={enableQueryRewrite}
              onToggleQueryRewrite={setEnableQueryRewrite}
              enableRetrievalCache={enableRetrievalCache}
              onToggleRetrievalCache={setEnableRetrievalCache}
              enableSectionBoost={enableSectionBoost}
              onToggleSectionBoost={setEnableSectionBoost}
            />
          </div>

          <ComparePanel
            onCompare={handleCompare}
            isLoading={compareMutation.isPending}
          />
        </div>

        <div className="chat-container">
          <ChatWindow messages={messages} />
          <ChatInput
            onSend={handleSendMessage}
            isLoading={chatMutation.isPending || compareMutation.isPending}
            disabled={!isSystemHealthy || selectedTickers.length === 0}
            placeholder={
              isCompareMode
                ? `Compare ${selectedTickers.join(" vs ")}...`
                : "Ask a question about SEC filings..."
            }
          />
        </div>
      </main>
    </div>
  );
}

export default App;

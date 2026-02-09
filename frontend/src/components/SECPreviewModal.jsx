import { useState, useEffect } from "react";
import "./SECPreviewModal.css";

export function SECPreviewModal({ ticker, onClose }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [format, setFormat] = useState("markdown");

  const formatContent = (raw) => {
    if (!raw) return raw;
    const normalized = raw.replace(/\r\n/g, "\n");

    // If the text already has reasonable breaks, keep them.
    if (
      normalized.includes("\n") &&
      normalized.split("\n").some((line) => line.length < 160)
    ) {
      return normalized;
    }

    // Add line breaks after sentence terminators followed by a capital/paren.
    let withBreaks = normalized.replace(/([.!?;])\s+(?=[A-Z(])/g, "$1\n");

    // Add space before section headers like Item 1A.
    withBreaks = withBreaks.replace(/\b(Item\s+\d+[A-Z]?)\./gi, "\n\n$1.");

    // Soft wrap long lines to ~110 chars while keeping words intact.
    const wrapLine = (line) => {
      if (line.length <= 120) return line.trim();
      const chunks = line.match(/.{1,110}(?:\s+|$)/g) || [line];
      return chunks.map((c) => c.trim()).join("\n");
    };

    const wrapped = withBreaks
      .split("\n")
      .map((line) => wrapLine(line))
      .join("\n");

    return wrapped.replace(/\n{3,}/g, "\n\n");
  };

  useEffect(() => {
    if (!ticker) {
      setError("⚠️ No ticker selected. Please select a ticker first.");
      setLoading(false);
      return;
    }

    const fetchPreview = async (retryCount = 0) => {
      setLoading(true);
      setError(null);

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

        const response = await fetch(
          `http://localhost:8001/api/sec-preview/${ticker}?format=${format}`,
          {
            signal: controller.signal,
          },
        );
        clearTimeout(timeoutId);

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(
              `Filing not found for ${ticker}. Please fetch the filing first.`,
            );
          }
          const errorData = await response
            .json()
            .catch(() => ({ detail: response.statusText }));
          throw new Error(
            errorData.detail ||
              `HTTP ${response.status}: ${response.statusText}`,
          );
        }

        const data = await response.json();
        const formatted = formatContent(data.content || "No content available");
        setContent(formatted);
        setLoading(false);
      } catch (err) {
        console.error("Preview fetch error:", err);
        console.error("Error name:", err.name);
        console.error("Error message:", err.message);

        // Retry on network errors (up to 2 retries)
        if (
          (err.name === "TypeError" ||
            err.message === "Failed to fetch" ||
            err.name === "AbortError") &&
          retryCount < 2
        ) {
          console.log(`Retrying... attempt ${retryCount + 1}`);
          setTimeout(
            () => fetchPreview(retryCount + 1),
            1000 * (retryCount + 1),
          ); // Exponential backoff
          return;
        }

        // Check if it's a network error (TypeError or fetch failed)
        if (
          err.name === "TypeError" ||
          err.message === "Failed to fetch" ||
          err.name === "AbortError"
        ) {
          setError(
            "⚠️ Cannot connect to backend server. Please ensure the backend is running on port 8000.",
          );
        } else if (
          err.message.includes("Filing not found") ||
          err.message.includes("not found")
        ) {
          setError(`⚠️ ${err.message}`);
        } else {
          setError(`⚠️ Error: ${err.message}`);
        }
        setContent("");
        setLoading(false);
      }
    };

    fetchPreview();
  }, [ticker, format]);

  const handleBackdropClick = (e) => {
    if (e.target.className === "sec-preview-modal-backdrop") {
      onClose();
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content);
    alert("Content copied to clipboard!");
  };

  return (
    <div className="sec-preview-modal-backdrop" onClick={handleBackdropClick}>
      <div className="sec-preview-modal">
        <div className="sec-preview-header">
          <div className="sec-preview-title">
            <h2>SEC Filing Preview: {ticker}</h2>
            <div className="format-toggle">
              <button
                className={format === "markdown" ? "active" : ""}
                onClick={() => setFormat("markdown")}
              >
                Markdown
              </button>
              <button
                className={format === "text" ? "active" : ""}
                onClick={() => setFormat("text")}
              >
                Plain Text
              </button>
            </div>
          </div>
          <div className="sec-preview-actions">
            <button
              onClick={copyToClipboard}
              disabled={loading || error}
              className="copy-btn"
            >
              📋 Copy
            </button>
            <button onClick={onClose} className="close-btn">
              ✕
            </button>
          </div>
        </div>

        <div className="sec-preview-body">
          {loading && (
            <div className="preview-loading">
              <div className="spinner"></div>
              <p>Loading SEC filing...</p>
            </div>
          )}

          {error && (
            <div className="preview-error">
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontFamily: "inherit",
                  margin: 0,
                }}
              >
                {error}
              </pre>
            </div>
          )}

          {!loading && !error && (
            <pre className="preview-content">{content}</pre>
          )}
        </div>

        <div className="sec-preview-footer">
          <span className="content-stats">
            {!loading &&
              !error &&
              `${content.length.toLocaleString()} characters`}
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Chat window displaying messages
 */
import React, { memo, useEffect, useRef } from "react";
import "./ChatWindow.css";

// Render minimal markdown: convert **bold** to <strong> and preserve newlines.
function renderContent(content) {
  if (!content) return "";
  const bolded = content.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return bolded.replace(/\n/g, "<br />");
}

export const ChatWindow = memo(function ChatWindow({ messages }) {
  const chatEndRef = useRef(null);
  const chatWindowRef = useRef(null);

  // Auto-scroll when messages change
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages]);

  return (
    <div className="chat-window" ref={chatWindowRef}>
      {messages.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">💬</div>
          <h3>Start a Conversation</h3>
          <p>
            Ask questions about SEC filings from MAG7 companies. Select a ticker
            and start exploring financial insights.
          </p>
        </div>
      ) : (
        messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-header">
              <span className="message-role">
                {msg.role === "user" ? "You" : "AI Assistant"}
              </span>
              {msg.timestamp && (
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              )}
            </div>
            <div
              className="message-content"
              dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }}
            />
            {msg.flagsSummary && (
              <div className="message-flags">
                ✨ {msg.flagsSummary}
                {msg.cacheHit ? " • cached" : ""}
              </div>
            )}
            {msg.citations && msg.citations.length > 0 && (
              <div className="citations">
                <div className="citations-header">Sources</div>
                <div className="citations-list">
                  {msg.citations.slice(0, 3).map((citation, citIdx) => (
                    <div key={citIdx} className="citation">
                      <span className="citation-ticker">{citation.ticker}</span>
                      {citation.form_type && (
                        <span className="citation-form">
                          {citation.form_type}
                        </span>
                      )}
                      {citation.year && (
                        <span className="citation-year">{citation.year}</span>
                      )}
                    </div>
                  ))}
                  {msg.citations.length > 3 && (
                    <div className="citations-more">
                      +{msg.citations.length - 3} more
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))
      )}
      <div ref={chatEndRef} />
    </div>
  );
});

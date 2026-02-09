import React, { useState, memo } from 'react';
import './ComparePanel.css';

const MAG7 = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NVDA', 'TSLA'];

export const ComparePanel = memo(function ComparePanel({ onCompare, isLoading }) {
  const [selectedTickers, setSelectedTickers] = useState(['AAPL', 'MSFT']);
  const [customTicker, setCustomTicker] = useState('');
  const [question, setQuestion] = useState('Compare recent risk factors');

  const toggleTicker = (ticker) => {
    setSelectedTickers((prev) =>
      prev.includes(ticker) ? prev.filter((t) => t !== ticker) : [...prev, ticker]
    );
  };

  const addCustomTicker = () => {
    const value = customTicker.trim().toUpperCase();
    if (!value) return;
    if (!selectedTickers.includes(value)) {
      setSelectedTickers((prev) => [...prev, value]);
    }
    setCustomTicker('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const unique = Array.from(new Set(selectedTickers.map((t) => t.trim().toUpperCase()).filter(Boolean)));
    if (unique.length < 2) {
      alert('Select at least two tickers');
      return;
    }
    onCompare({ tickers: unique, question });
  };


  return (
    <div className="compare-panel">
      <h3>Compare Companies</h3>
      <form onSubmit={handleSubmit} className="compare-form">
        <div className="ticker-grid">
          {MAG7.map((t) => (
            <label key={t} className="ticker-pill">
              <input
                type="checkbox"
                checked={selectedTickers.includes(t)}
                onChange={() => toggleTicker(t)}
              />
              {t}
            </label>
          ))}
        </div>

        <div className="custom-row">
          <input
            type="text"
            placeholder="Add custom ticker (e.g., NFLX)"
            value={customTicker}
            onChange={(e) => setCustomTicker(e.target.value)}
          />
          <button type="button" onClick={addCustomTicker} className="secondary" disabled={isLoading}>
            Add
          </button>
        </div>

        <label className="compare-question">
          Question
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
          />
        </label>

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Comparing...' : 'Compare'}
        </button>
      </form>
    </div>
  );
});

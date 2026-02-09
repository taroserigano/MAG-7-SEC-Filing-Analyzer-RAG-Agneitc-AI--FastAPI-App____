/**
 * Ticker selector for MAG7 stocks with multi-select support
 */
import React, { useState, memo } from 'react';
import './TickerSelector.css';

const MAG7_STOCKS = [
  { ticker: 'AAPL', name: 'Apple' },
  { ticker: 'MSFT', name: 'Microsoft' },
  { ticker: 'AMZN', name: 'Amazon' },
  { ticker: 'GOOGL', name: 'Google' },
  { ticker: 'META', name: 'Meta' },
  { ticker: 'NVDA', name: 'NVIDIA' },
  { ticker: 'TSLA', name: 'Tesla' },
];

export const TickerSelector = memo(function TickerSelector({ selectedTickers, onTickerChange, multiSelectMode, onMultiSelectModeChange }) {
  const handleSelect = (ticker) => {
    const isSelected = selectedTickers.includes(ticker);
    
    if (multiSelectMode) {
      // Multi-select: toggle selection
      const next = isSelected
        ? selectedTickers.filter((t) => t !== ticker)
        : [...selectedTickers, ticker];
      onTickerChange(next);
    } else {
      // Single-select: replace selection
      onTickerChange([ticker]);
    }
  };

  return (
    <div className="ticker-selector">
      <div className="ticker-header">
        <h3>Select Company</h3>
        <label className="multi-select-toggle">
          <input
            type="checkbox"
            checked={multiSelectMode}
            onChange={(e) => onMultiSelectModeChange(e.target.checked)}
          />
          <span>Multi-select</span>
        </label>
      </div>
      
      {multiSelectMode && selectedTickers.length > 0 && (
        <div className="selection-summary">
          {selectedTickers.length} {selectedTickers.length === 1 ? 'company' : 'companies'} selected
        </div>
      )}
      
      <div className="ticker-grid" role={multiSelectMode ? "group" : "radiogroup"} aria-label="MAG7 companies">
        {MAG7_STOCKS.map(({ ticker, name }) => {
          const isActive = selectedTickers.includes(ticker);
          return (
            <button
              key={ticker}
              type="button"
              className={`ticker-btn ${isActive ? 'active' : ''} ${multiSelectMode ? 'multi-mode' : ''}`}
              data-ticker={ticker}
              data-active={isActive}
              aria-pressed={isActive}
              onClick={() => handleSelect(ticker)}
            >
              {multiSelectMode && (
                <span className="selection-indicator">
                  {isActive ? '✓' : ''}
                </span>
              )}
              <span className="ticker-code">{ticker}</span>
              <span className="ticker-name">{name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
});

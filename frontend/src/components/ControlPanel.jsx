/**
 * Control panel for model and search settings
 */
import React, { memo } from 'react';
import './ControlPanel.css';

export const ControlPanel = memo(function ControlPanel({ 
  modelProvider, 
  onModelProviderChange, 
  searchMode, 
  onSearchModeChange,
  enableRerank,
  onToggleRerank,
  enableQueryRewrite,
  onToggleQueryRewrite,
  enableRetrievalCache,
  onToggleRetrievalCache,
  enableSectionBoost,
  onToggleSectionBoost,

}) {
  return (
    <div className="control-panel">
      <div className="control-group">
        <label>Model Provider</label>
        <select value={modelProvider} onChange={(e) => onModelProviderChange(e.target.value)}>
          <option value="openai">OpenAI (GPT-4)</option>
          <option value="anthropic">Anthropic (Claude)</option>
          <option value="ollama">Ollama (Local)</option>
        </select>
      </div>

      <div className="control-group">
        <label>Search Mode</label>
        <select value={searchMode} onChange={(e) => onSearchModeChange(e.target.value)}>
          <option value="vector">Vector Search</option>
          <option value="hybrid">Hybrid Search</option>
        </select>
      </div>

      <div className="control-group checkbox-group">
        <label>Retrieval Flags</label>
        <label className="checkbox-row">
          <input type="checkbox" checked={enableRerank} onChange={(e) => onToggleRerank(e.target.checked)} />
          <span>Rerank</span>
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={enableQueryRewrite} onChange={(e) => onToggleQueryRewrite(e.target.checked)} />
          <span>Query Rewrite</span>
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={enableRetrievalCache} onChange={(e) => onToggleRetrievalCache(e.target.checked)} />
          <span>Retrieval Cache</span>
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={enableSectionBoost} onChange={(e) => onToggleSectionBoost(e.target.checked)} />
          <span>Section Boost</span>
        </label>
      </div>
    </div>
  );
});

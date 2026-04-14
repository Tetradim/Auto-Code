/**
 * Settings Dashboard
 * Configuration management for Edge
 */
import React, { useEffect, useState } from 'react';
import { Settings, Save, RefreshCw, Database, Zap, Shield, Globe, AlertCircle } from 'lucide-react';

interface ConfigSection {
  name: string;
  key: string;
  fields: {
    key: string;
    label: string;
    type: 'text' | 'number' | 'boolean' | 'select';
    value: any;
    options?: string[];
    description?: string;
  }[];
}

const CONFIG_SECTIONS: ConfigSection[] = [
  {
    name: 'Data Source',
    key: 'data',
    fields: [
      { key: 'source', label: 'Data Source', type: 'select', value: 'mock', options: ['mock', 'yfinance', 'binance'], description: 'Where to fetch market data' },
      { key: 'api_key', label: 'API Key', type: 'text', value: '', description: 'Optional API key for premium data' },
    ]
  },
  {
    name: 'Risk Management',
    key: 'risk',
    fields: [
      { key: 'max_position_size', label: 'Max Position Size (%)', type: 'number', value: 10, description: 'Maximum position size as % of portfolio' },
      { key: 'stop_loss_pct', label: 'Stop Loss (%)', type: 'number', value: 5, description: 'Default stop loss percentage' },
      { key: 'take_profit_pct', label: 'Take Profit (%)', type: 'number', value: 15, description: 'Default take profit percentage' },
      { key: 'max_consecutive_losses', label: 'Max Consecutive Losses', type: 'number', value: 3, description: 'Stop trading after this many losses' },
    ]
  },
  {
    name: 'Paper Trading',
    key: 'paper',
    fields: [
      { key: 'initial_cash', label: 'Initial Cash ($)', type: 'number', value: 100000, description: 'Starting cash for paper trading' },
      { key: 'slippage_pct', label: 'Slippage (%)', type: 'number', value: 0.05, description: 'Simulated slippage per trade' },
      { key: 'commission_pct', label: 'Commission (%)', type: 'number', value: 0.1, description: 'Simulated commission per trade' },
      { key: 'latency_ms', label: 'Latency (ms)', type: 'number', value: 100, description: 'Simulated order execution latency' },
    ]
  },
  {
    name: 'Rate Limiting',
    key: 'rate_limit',
    fields: [
      { key: 'requests_per_second', label: 'Requests/Second', type: 'number', value: 10, description: 'Max API requests per second' },
      { key: 'max_retries', label: 'Max Retries', type: 'number', value: 3, description: 'Max retry attempts on failure' },
      { key: 'base_delay', label: 'Base Delay (s)', type: 'number', value: 1, description: 'Base delay for exponential backoff' },
    ]
  }
];

export function SettingsDashboard() {
  const [sections, setSections] = useState(CONFIG_SECTIONS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Load saved config from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('edge_config');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Update sections with saved values
        setSections(sections.map(section => ({
          ...section,
          fields: section.fields.map(field => ({
            ...field,
            value: parsed[section.key]?.[field.key] ?? field.value
          }))
        })));
      } catch (e) {
        console.error('Failed to load saved config');
      }
    }
  }, []);

  const handleFieldChange = (sectionKey: string, fieldKey: string, value: any) => {
    setSections(sections.map(section => {
      if (section.key !== sectionKey) return section;
      return {
        ...section,
        fields: section.fields.map(field => 
          field.key === fieldKey ? { ...field, value } : field
        )
      };
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    
    // Save to localStorage
    const config: Record<string, Record<string, any>> = {};
    sections.forEach(section => {
      config[section.key] = {};
      section.fields.forEach(field => {
        config[section.key][field.key] = field.value;
      });
    });
    
    localStorage.setItem('edge_config', JSON.stringify(config));
    
    // Also try to save to backend
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
    } catch (e) {
      // Silently fail - localStorage is enough
    }
    
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    setSections(CONFIG_SECTIONS);
    localStorage.removeItem('edge_config');
    setSaved(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gray-800">
            <Settings className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Settings</h2>
            <p className="text-sm text-gray-400">Configure Edge behavior</p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              saved 
                ? 'bg-emerald-500 text-white' 
                : saving 
                  ? 'bg-gray-600 text-gray-400'
                  : 'bg-emerald-500 hover:bg-emerald-600 text-white'
            }`}
          >
            {saving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : saved ? (
              <Save className="w-4 h-4" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saved ? 'Saved!' : 'Save Settings'}
          </button>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-300">
          <p className="font-medium">Settings are stored locally</p>
          <p className="text-blue-400/70">Your configuration is saved to your browser and persists across sessions.</p>
        </div>
      </div>

      {/* Config Sections */}
      <div className="space-y-6">
        {sections.map((section) => (
          <div key={section.key} className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              {section.key === 'data' && <Database className="w-5 h-5 text-emerald-400" />}
              {section.key === 'risk' && <Shield className="w-5 h-5 text-red-400" />}
              {section.key === 'paper' && <Zap className="w-5 h-5 text-amber-400" />}
              {section.key === 'rate_limit' && <Globe className="w-5 h-5 text-blue-400" />}
              {section.name}
            </h3>
            
            <div className="space-y-4">
              {section.fields.map((field) => (
                <div key={field.key} className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {field.label}
                    </label>
                    {field.description && (
                      <p className="text-xs text-gray-500">{field.description}</p>
                    )}
                  </div>
                  
                  <div className="w-48">
                    {field.type === 'select' && (
                      <select
                        value={field.value}
                        onChange={(e) => handleFieldChange(section.key, field.key, e.target.value)}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                      >
                        {field.options?.map((opt) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    )}
                    
                    {field.type === 'number' && (
                      <input
                        type="number"
                        value={field.value}
                        onChange={(e) => handleFieldChange(section.key, field.key, parseFloat(e.target.value) || 0)}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                      />
                    )}
                    
                    {field.type === 'text' && (
                      <input
                        type="text"
                        value={field.value}
                        onChange={(e) => handleFieldChange(section.key, field.key, e.target.value)}
                        placeholder="Optional"
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                      />
                    )}
                    
                    {field.type === 'boolean' && (
                      <button
                        onClick={() => handleFieldChange(section.key, field.key, !field.value)}
                        className={`w-full py-2 rounded-lg text-sm font-medium transition-colors ${
                          field.value 
                            ? 'bg-emerald-500 text-white' 
                            : 'bg-gray-700 text-gray-400'
                        }`}
                      >
                        {field.value ? 'Enabled' : 'Disabled'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
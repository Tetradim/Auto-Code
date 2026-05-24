/**
 * Settings Dashboard
 * Configuration management for Edge
 */
import React, { useEffect, useState } from 'react';
import { Settings, Save, RefreshCw, Database, Zap, Shield, Globe, AlertCircle, TrendingUp, ShieldAlert, BarChart3, CheckCircle, XCircle } from 'lucide-react';

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

interface ProviderInfo {
  key: string;
  label: string;
  quote: boolean;
  ohlcv: boolean;
  requires_key: boolean;
  configured: boolean;
  enabled: boolean;
  intraday?: boolean;
  eod?: boolean;
  free_tier: string;
  notes: string;
}

const MARKET_DATA_OPTIONS = [
  'yfinance',
  'finnhub',
  'polygon',
  'alpha_vantage',
  'twelve_data',
];

const isSecretField = (key: string) => {
  const normalized = key.toLowerCase();
  return normalized.includes('api_key') || normalized.includes('secret') || normalized.includes('token');
};

const CONFIG_SECTIONS: ConfigSection[] = [
  {
    name: 'Data Source',
    key: 'data',
    fields: [
      { key: 'source', label: 'Primary Data Source', type: 'select', value: 'yfinance', options: MARKET_DATA_OPTIONS, description: 'Preferred intraday market-data source. Backend fallback order is controlled by MARKET_DATA_PROVIDER_ORDER.' },
      { key: 'fallback_order', label: 'Fallback Order', type: 'text', value: 'yfinance,finnhub,polygon,alpha_vantage,twelve_data', description: 'Comma-separated intraday provider order for backend env MARKET_DATA_PROVIDER_ORDER. EOD-only sources are ignored for live ticks.' },
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
    name: 'Greek Analysis',
    key: 'greeks',
    fields: [
      { key: 'delta', label: 'Delta Analysis', type: 'boolean', value: false, description: 'Direction & Probability - measures sensitivity to price movements' },
      { key: 'theta', label: 'Theta Analysis', type: 'boolean', value: false, description: 'Time Decay - measures daily value erosion' },
      { key: 'vega', label: 'Vega Analysis', type: 'boolean', value: false, description: 'Volatility Sensitivity - measures IV impact' },
      { key: 'gamma', label: 'Gamma Analysis', type: 'boolean', value: false, description: 'Delta Acceleration - measures rate of delta change' },
      { key: 'rho', label: 'Rho Analysis', type: 'boolean', value: false, description: 'Interest Rate Sensitivity - bond yield impact' },
      { key: 'gex', label: 'GEX (Gamma Exposure)', type: 'boolean', value: false, description: 'Aggregate market maker gamma' },
      { key: 'vex', label: 'VEX (Vega Exposure)', type: 'boolean', value: false, description: 'Aggregate volatility exposure' },
    ]
  },
  {
    name: 'Advanced Options',
    key: 'advanced',
    fields: [
      { key: 'iv_tracking', label: 'IV Percentile Tracking', type: 'boolean', value: false, description: 'Track IV relative to historical percentiles' },
      { key: 'spike_protection', label: 'Volatility Spike Protection', type: 'boolean', value: true, description: 'Detect and warn on IV spikes >50% above normal' },
      { key: 'short_interest', label: 'Short Interest Analysis', type: 'boolean', value: false, description: 'Days to cover & squeeze potential analysis' },
    ]
  },
  {
    name: 'Chart Options',
    key: 'charts',
    fields: [
      { key: 'chart_type', label: 'Default Chart Type', type: 'select', value: 'line', options: ['area', 'bar', 'line', 'candlestick', 'heatmap'], description: 'Default visualization type' },
      { key: 'dashboard_layout', label: 'Dashboard Layout', type: 'select', value: 'grid', options: ['grid', 'list', 'heatmap'], description: 'Card layout arrangement' },
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
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [providerOrder, setProviderOrder] = useState<string[]>([]);

  // Load saved config from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('edge_config');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const sanitized = Object.fromEntries(
          Object.entries(parsed).map(([sectionKey, values]) => [
            sectionKey,
            Object.fromEntries(
              Object.entries((values as Record<string, any>) || {}).filter(([fieldKey]) => !isSecretField(fieldKey))
            ),
          ])
        );
        if (JSON.stringify(sanitized) !== saved) {
          localStorage.setItem('edge_config', JSON.stringify(sanitized));
        }
        // Update sections with saved values
        setSections(sections.map(section => ({
          ...section,
          fields: section.fields.map(field => ({
            ...field,
            value: sanitized[section.key]?.[field.key] ?? field.value
          }))
        })));
      } catch (e) {
        console.error('Failed to load saved config');
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadProviders = async () => {
      try {
        const response = await fetch('/api/market-data/providers');
        if (!response.ok) return;
        const data = await response.json();
        if (cancelled) return;
        setProviders(data.providers || []);
        setProviderOrder(data.fallback_order || []);
      } catch (e) {
        // Provider metadata is informational only; keep Settings usable offline.
      }
    };
    loadProviders();
    const id = window.setInterval(loadProviders, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
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
        if (isSecretField(field.key)) return;
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
          <p className="text-blue-400/70">Your non-secret configuration is saved to your browser and persists across sessions. API keys are not saved here; configure them as backend environment variables.</p>
        </div>
      </div>

      {/* Market Data Providers */}
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-emerald-400" />
          Market Data Providers
        </h3>
        <p className="text-sm text-gray-400 mb-4">
          Edge monitors market data only. API keys are configured on the backend as environment variables; this panel only shows provider availability.
        </p>
        <div className="space-y-3">
          {providers.length === 0 && (
            <div className="text-sm text-gray-500">Provider metadata unavailable until the backend is running.</div>
          )}
          {providers.map((provider) => (
            <div key={provider.key} className="flex items-start justify-between gap-4 rounded-lg border border-gray-700 bg-gray-900/50 p-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white">{provider.label}</span>
                  {providerOrder.includes(provider.key) && (
                    <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">intraday fallback</span>
                  )}
                  {provider.eod && !provider.intraday && (
                    <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">EOD/backfill only</span>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">{provider.free_tier}</p>
                <p className="mt-1 text-xs text-gray-500">{provider.notes}</p>
              </div>
              <div className="flex items-center gap-2 text-sm">
                {provider.configured ? (
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                ) : (
                  <XCircle className="h-4 w-4 text-gray-500" />
                )}
                <span className={provider.configured ? 'text-emerald-300' : 'text-gray-500'}>
                  {provider.requires_key ? (provider.configured ? 'key configured' : 'needs env key') : 'no key'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Config Sections */}
      <div className="space-y-6">
        {sections.map((section) => (
          <div key={section.key} className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              {section.key === 'data' && <Database className="w-5 h-5 text-emerald-400" />}
              {section.key === 'risk' && <Shield className="w-5 h-5 text-red-400" />}
              {section.key === 'greeks' && <TrendingUp className="w-5 h-5 text-purple-400" />}
              {section.key === 'advanced' && <ShieldAlert className="w-5 h-5 text-amber-400" />}
              {section.key === 'charts' && <BarChart3 className="w-5 h-5 text-blue-400" />}
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

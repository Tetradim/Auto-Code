import React, { useState, useEffect } from 'react';
import { X, Play } from 'lucide-react';
import { api } from '@/lib/api';
import BacktestResultsChart from './BacktestResultsChart';

// Default providers - alpaca first for real-time, yfinance as fallback
const DEFAULT_PROVIDERS = ['alpaca', 'yfinance'];
const ALL_PROVIDERS = ['alpaca', 'polygon', 'finnhub', 'yfinance'];

interface TickerConfigModalProps {
  symbol: string;
  isOpen: boolean;
  onClose: () => void;
  onRefresh?: () => void;
}

interface BacktestResult {
  equity_curve: { time: string; equity: number }[];
  trades: any[];
  final_capital: number;
  total_return_pct: number;
  win_rate: number;
  max_drawdown_pct: number;
  symbol: string;
  monte_carlo?: {
    simulations: number;
    median_final_equity: number;
    worst_case_equity: number;
    probability_of_profit: number;
    mean_max_drawdown: number;
  };
}

export const TickerConfigModal: React.FC<TickerConfigModalProps> = ({
  symbol,
  isOpen,
  onClose,
  onRefresh,
}) => {
  const [localConfig, setLocalConfig] = useState({
    price_providers: DEFAULT_PROVIDERS,
    metrics: {
      orb: true,
      atr: true,
      signal: true,
      volume: true,
      price: true,
      breakouts: true,
    },
    risk: {
      max_consecutive_losses: 3,
      max_drawdown_pct: 10.0,
      trailing_stop_profit_threshold: 2.0,
    },
  });
  const [saving, setSaving] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const [backtestResults, setBacktestResults] = useState<BacktestResult | null>(null);
  const [runningBacktest, setRunningBacktest] = useState(false);

  // Load existing config when modal opens
  useEffect(() => {
    if (isOpen && symbol) {
      setInitialLoad(true);
      api.getTickerConfig(symbol).then((config) => {
        setLocalConfig({
          price_providers: config?.price_providers || DEFAULT_PROVIDERS,
          metrics: config?.metrics || {
            orb: true,
            atr: true,
            signal: true,
            volume: true,
            price: true,
            breakouts: true,
          },
          risk: config?.risk || {
            max_consecutive_losses: 3,
            max_drawdown_pct: 10.0,
            trailing_stop_profit_threshold: 2.0,
          },
        });
        setInitialLoad(false);
      }).catch(() => {
        setLocalConfig({
          price_providers: DEFAULT_PROVIDERS,
          metrics: {
            orb: true,
            atr: true,
            signal: true,
            volume: true,
            price: true,
            breakouts: true,
          },
          risk: {
            max_consecutive_losses: 3,
            max_drawdown_pct: 10.0,
            trailing_stop_profit_threshold: 2.0,
          },
        });
        setInitialLoad(false);
      });
    }
  }, [isOpen, symbol]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save price providers config
      await api.updateTickerConfig(symbol, {
        price_providers: localConfig.price_providers,
        metrics: localConfig.metrics,
        risk: localConfig.risk,
      });

      onClose();
      onRefresh?.();
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setSaving(false);
    }
  };

  const toggleProvider = (provider: string) => {
    let updated = [...(localConfig.price_providers || DEFAULT_PROVIDERS)];

    if (updated.includes(provider)) {
      updated = updated.filter((p) => p !== provider);
    } else {
      updated.push(provider);
    }

    // Always keep at least one provider
    if (updated.length === 0) {
      updated = ['yfinance'];
    }

    setLocalConfig({ ...localConfig, price_providers: updated });
  };

  if (!isOpen) return null;

  // Drag-to-reorder handlers
  const handleDragStart = (e: React.DragEvent, index: number) => {
    e.dataTransfer.setData('text/plain', index.toString());
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, toIndex: number) => {
    e.preventDefault();
    const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
    if (fromIndex === toIndex || isNaN(fromIndex)) return;

    const newOrder = [...localConfig.price_providers];
    const [moved] = newOrder.splice(fromIndex, 1);
    newOrder.splice(toIndex, 0, moved);

    setLocalConfig({ ...localConfig, price_providers: newOrder });
  };

  const removeProvider = (provider: string) => {
    const newList = localConfig.price_providers.filter(p => p !== provider);
    if (newList.length === 0) newList.push('yfinance');
    setLocalConfig({ ...localConfig, price_providers: newList });
  };

  const addProvider = (provider: string) => {
    if (!localConfig.price_providers.includes(provider)) {
      setLocalConfig({
        ...localConfig,
        price_providers: [...localConfig.price_providers, provider],
      });
    }
  };

  const runBacktest = async () => {
    setRunningBacktest(true);
    try {
      // Default to last 30 days
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0];

      const result = await api.runBacktest(symbol, startDate, endDate, 10000);
      setBacktestResults(result);
    } catch (error) {
      console.error('Backtest failed:', error);
    } finally {
      setRunningBacktest(false);
    }
  };

  const runOptimization = async () => {
    setRunningBacktest(true);
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 60 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0];
      
      // Sample parameter grid for optimization
      const paramGrid = {
        slippage_pct: [0.03, 0.05, 0.1],
        commission_pct: [0.05, 0.1, 0.15],
        num_simulations: [500, 1000],
      };

      const result = await api.optimizeStrategy(symbol, startDate, endDate, paramGrid, 10000);
      setBacktestResults(result.best_results);
    } catch (error) {
      console.error('Optimization failed:', error);
    } finally {
      setRunningBacktest(false);
    }
  };

  // Available providers not yet added
  const availableProviders = ALL_PROVIDERS.filter(
    p => !localConfig.price_providers.includes(p)
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg bg-zinc-900 rounded-2xl border border-zinc-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-700">
          <h2 className="text-lg font-semibold text-white">
            Configure {symbol}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {initialLoad ? (
            <div className="text-sm text-zinc-400">Loading...</div>
          ) : (
            <>
              {/* Price Providers - Drag to Reorder */}
              <div className="space-y-4 border-t border-zinc-700 pt-6">
                <label className="text-sm font-medium text-white flex items-center justify-between">
                  Price Data Providers{' '}
                  <span className="text-xs text-zinc-500">(drag to reorder priority)</span>
                </label>

                <div className="bg-zinc-900 p-4 rounded-2xl space-y-2">
                  {localConfig.price_providers.map((provider: string, index: number) => (
                    <div
                      key={provider}
                      draggable
                      onDragStart={(e) => handleDragStart(e, index)}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDrop(e, index)}
                      className="flex items-center gap-3 bg-zinc-800 p-3 rounded-xl cursor-move hover:bg-zinc-700 group"
                    >
                      <span className="text-zinc-400">≡</span>
                      <span className="capitalize flex-1">{provider}</span>
                      <button
                        type="button"
                        onClick={() => removeProvider(provider)}
                        className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-500"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>

                {/* Available providers to add */}
                <div className="flex flex-wrap gap-2">
                  {availableProviders.map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => addProvider(p)}
                      className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-xl text-sm capitalize"
                    >
                      + {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Risk Parameters */}
              <div className="space-y-4 border-t border-zinc-700 pt-6">
                <label className="text-sm font-medium text-white">
                  Risk Parameters
                </label>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Max Consecutive Losses</label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={localConfig.risk.max_consecutive_losses}
                      onChange={(e) => setLocalConfig({
                        ...localConfig,
                        risk: { ...localConfig.risk, max_consecutive_losses: parseInt(e.target.value) || 3 },
                      })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-zinc-500 mt-1">Emergency exit after N consecutive losses</p>
                  </div>

                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Max Drawdown %</label>
                    <input
                      type="number"
                      min={0.1}
                      max={100}
                      step={0.1}
                      value={localConfig.risk.max_drawdown_pct}
                      onChange={(e) => setLocalConfig({
                        ...localConfig,
                        risk: { ...localConfig.risk, max_drawdown_pct: parseFloat(e.target.value) || 10 },
                      })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-zinc-500 mt-1">Exit when drawdown exceeds this %</p>
                  </div>

                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Trailing Stop Profit %</label>
                    <input
                      type="number"
                      min={0.1}
                      max={50}
                      step={0.1}
                      value={localConfig.risk.trailing_stop_profit_threshold}
                      onChange={(e) => setLocalConfig({
                        ...localConfig,
                        risk: { ...localConfig.risk, trailing_stop_profit_threshold: parseFloat(e.target.value) || 2 },
                      })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                    <p className="text-xs text-zinc-500 mt-1">Enable trailing stop after profit %</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Backtest Results */}
        {backtestResults && (
          <div className="px-6 pb-4">
            <BacktestResultsChart results={backtestResults} />
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-between items-center gap-3 px-6 py-4 border-t border-zinc-700">
          <div className="flex gap-2">
            <button
              onClick={runBacktest}
              disabled={runningBacktest}
              className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <Play size={14} />
              {runningBacktest ? 'Running...' : 'Run Backtest'}
            </button>
            <button
              onClick={runOptimization}
              disabled={runningBacktest}
              className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition-colors disabled:opacity-50"
              title="Grid Search Auto-Optimization"
            >
              {runningBacktest ? 'Optimizing...' : 'Optimize'}
            </button>
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || initialLoad}
              className="px-4 py-2 text-sm bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
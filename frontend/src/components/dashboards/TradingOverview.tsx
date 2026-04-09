import React, { useEffect, useState, useRef } from 'react';
import { Activity, TrendingUp, AlertCircle, Zap, AlertTriangle, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { MetricCard } from '../cards/MetricCard';
import { TickerCard } from '../cards/TickerCard';
import { ChartCard } from '../cards/ChartCard';
import { DecisionFeed } from './DecisionFeed';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';
import {
  generateMockTickerList,
  generateMockDecisions,
  DEFAULT_MOCK_SYMBOLS,
} from '@/lib/mockData';
import type { TickerData, DecisionEntry } from '@/types';

// ── Market Breadth bar ─────────────────────────────────────────────────

interface Breadth {
  bullish: number;
  bearish: number;
  neutral: number;
  bullish_pct: number;
  bearish_pct: number;
  total: number;
}

const BreadthBar: React.FC<{ breadth: Breadth }> = ({ breadth }) => (
  <div data-testid="breadth-bar" className="space-y-2">
    <div className="flex justify-between text-xs text-gray-400 mb-1">
      <span className="text-green-400">{breadth.bullish_pct}% Bullish ({breadth.bullish})</span>
      <span className="text-gray-500">{breadth.neutral} Neutral</span>
      <span className="text-red-400">{breadth.bearish_pct}% Bearish ({breadth.bearish})</span>
    </div>
    <div className="flex h-2.5 rounded-full overflow-hidden bg-gray-800">
      <div
        className="bg-green-500 transition-all duration-700"
        style={{ width: `${breadth.bullish_pct}%` }}
      />
      <div
        className="bg-gray-600 transition-all duration-700"
        style={{ width: `${100 - breadth.bullish_pct - breadth.bearish_pct}%` }}
      />
      <div
        className="bg-red-500 transition-all duration-700"
        style={{ width: `${breadth.bearish_pct}%` }}
      />
    </div>
  </div>
);

// ── Add Ticker form ────────────────────────────────────────────────────

interface AddTickerProps {
  onAdd: (symbol: string) => Promise<void>;
  disabled?: boolean;
}

const AddTickerForm: React.FC<AddTickerProps> = ({ onAdd, disabled }) => {
  const [value, setValue] = useState('');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const sym = value.trim().toUpperCase();
    if (!sym || !/^[A-Z]{1,6}$/.test(sym)) {
      setError('Enter a valid symbol (1–6 letters)');
      return;
    }
    setError('');
    setAdding(true);
    try {
      await onAdd(sym);
      setValue('');
    } catch (err) {
      setError('Failed to add ticker — try again');
    } finally {
      setAdding(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-3" data-testid="add-ticker-form">
      <input
        type="text"
        value={value}
        onChange={(e) => { setValue(e.target.value.toUpperCase()); setError(''); }}
        placeholder="e.g. TSLA"
        maxLength={6}
        disabled={disabled || adding}
        data-testid="add-ticker-input"
        className="w-36 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white
          placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors
          disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || adding || !value.trim()}
        data-testid="add-ticker-button"
        className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500/20 text-emerald-400 border
          border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30
          disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        <Plus className="w-4 h-4" />
        {adding ? 'Adding…' : 'Add'}
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </form>
  );
};

// ── Main component ─────────────────────────────────────────────────────

export const TradingOverview: React.FC = () => {
  const {
    tickers, stats,
    setTickers, removeTicker, setStats,
    mockMode,
    correlationAlerts, addCorrelationAlert,
  } = useStore();

  const [breakoutData] = useState([
    { timestamp: '10:00', value: 2 },
    { timestamp: '10:30', value: 5 },
    { timestamp: '11:00', value: 3 },
    { timestamp: '11:30', value: 7 },
    { timestamp: '12:00', value: 4 },
    { timestamp: '12:30', value: 6 },
  ]);

  const [tickerConfigs, setTickerConfigs] = useState<Record<string, any>>({});
  const [breadth, setBreadth] = useState<Breadth>({
    bullish: 0, bearish: 0, neutral: 0, bullish_pct: 0, bearish_pct: 0, total: 1,
  });
  const [decisions, setDecisions] = useState<DecisionEntry[]>([]);

  const mockPricesRef = useRef<TickerData[]>([]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, mockMode ? 2000 : 5000);
    return () => clearInterval(interval);
  }, [mockMode]);

  const loadData = async () => {
    try {
      if (mockMode) {
        const symbols =
          mockPricesRef.current.length > 0
            ? mockPricesRef.current.map((t) => t.symbol)
            : DEFAULT_MOCK_SYMBOLS;
        const mockTickers = generateMockTickerList(symbols);
        mockPricesRef.current = mockTickers;
        setTickers(mockTickers);

        // Mock breadth
        const bulls = mockTickers.filter((t) => t.trend === 'bullish').length;
        const bears = mockTickers.filter((t) => t.trend === 'bearish').length;
        const total = mockTickers.length;
        setBreadth({
          bullish: bulls, bearish: bears, neutral: total - bulls - bears, total,
          bullish_pct: parseFloat(((bulls / total) * 100).toFixed(1)),
          bearish_pct: parseFloat(((bears / total) * 100).toFixed(1)),
        });

        // Accumulate mock decisions
        const newDecs = generateMockDecisions(symbols, 0.35);
        if (newDecs.length > 0) {
          setDecisions((prev) => [...newDecs, ...prev].slice(0, 20));
        }
        return;
      }

      // Live data
      const [tickersRes, statsRes, corrRes, decsRes] = await Promise.allSettled([
        api.getTickers(),
        api.getStats(),
        api.getCorrelation(),
        api.getDecisions(),
      ]);

      if (tickersRes.status === 'fulfilled') {
        const raw: any[] = tickersRes.value.tickers || [];
        const mapped: TickerData[] = raw.map((t: any) =>
          typeof t === 'string' ? { symbol: t, enabled: true } : t,
        );
        setTickers(mapped);
      }

      if (statsRes.status === 'fulfilled') setStats(statsRes.value);

      if (corrRes.status === 'fulfilled') {
        const cd = corrRes.value;
        if ((cd.clusters || []).length > 0 && correlationAlerts.length === 0) {
          (cd.clusters as any[]).forEach((c: any) => addCorrelationAlert(c));
        }
        if (cd.breadth) setBreadth(cd.breadth);
      }

      if (decsRes.status === 'fulfilled') {
        setDecisions(decsRes.value.decisions || []);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  // ── Add / Remove ticker ─────────────────────────────────────────────

  const handleAddTicker = async (symbol: string) => {
    if (mockMode) {
      // Local-only add in mock mode
      if (!tickers.find((t) => t.symbol === symbol)) {
        const { generateMockTicker } = await import('@/lib/mockData');
        setTickers([...tickers, generateMockTicker(symbol)]);
        mockPricesRef.current = [...mockPricesRef.current, generateMockTicker(symbol)];
      }
    } else {
      await api.addTicker(symbol);
      await loadData();
    }
  };

  const handleRemoveTicker = async (symbol: string) => {
    if (mockMode) {
      removeTicker(symbol);
      mockPricesRef.current = mockPricesRef.current.filter((t) => t.symbol !== symbol);
    } else {
      await api.removeTicker(symbol);
      removeTicker(symbol);
    }
  };

  const handleMetricToggle = async (symbol: string, metric: string) => {
    const current = tickerConfigs[symbol] || {
      orb: true, atr: true, signal: true, volume: true, price: true, breakouts: true,
    };
    const updated = { ...current, [metric]: !current[metric] };
    setTickerConfigs({ ...tickerConfigs, [symbol]: updated });
    if (!mockMode) {
      try { await api.updateTickerConfig(symbol, { metrics: updated }); }
      catch (err) { console.error(err); }
    }
  };

  const activeTickers = tickers.filter((t) => t.enabled);
  const avgSignalStrength =
    activeTickers.length > 0
      ? activeTickers.reduce((s, t) => s + (t.signal_strength || 0), 0) / activeTickers.length
      : 0;

  return (
    <div className="space-y-6" data-testid="trading-overview">
      {/* Metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Active Tickers" value={activeTickers.length}
          subtitle="Currently monitored" icon={Activity} color="blue" trend="neutral" />
        <MetricCard title="ORB Breakouts" value={27}
          subtitle="Today" icon={TrendingUp} color="green" change="+12.5%" trend="up" />
        <MetricCard title="Avg Signal" value={avgSignalStrength.toFixed(1)}
          subtitle="Across all tickers" icon={Zap} color={avgSignalStrength >= 0 ? 'green' : 'red'} />
        <MetricCard
          title="System Status"
          value={mockMode ? 'Mock Mode' : stats?.running ? 'Running' : 'Stopped'}
          subtitle={mockMode ? 'Simulated data' : stats?.paused ? 'Paused' : 'Active'}
          icon={AlertCircle}
          color={mockMode ? 'yellow' : stats?.running ? 'green' : 'red'}
        />
      </div>

      {/* Market Breadth */}
      <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90
        to-gray-800/50 backdrop-blur-sm shadow-xl p-6" data-testid="market-breadth-panel">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Market Breadth</h3>
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded-full">
            90-second window
          </span>
        </div>
        <BreadthBar breadth={breadth} />
        {breadth.total <= 1 && !mockMode && (
          <p className="mt-2 text-xs text-gray-500 italic">
            No directional signals in current window — awaiting BUY / STOP_BUYING events
          </p>
        )}
        <AnimatePresence>
          {correlationAlerts.slice(0, 3).map((alert, i) => (
            <motion.div
              key={`${alert.timestamp}-${i}`}
              initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }} transition={{ delay: i * 0.1 }}
              className={`mt-3 flex items-start gap-3 rounded-lg p-3 border text-sm
                ${alert.direction === 'BULLISH'
                  ? 'bg-green-500/10 border-green-500/30 text-green-300'
                  : 'bg-red-500/10 border-red-500/30 text-red-300'}`}
              data-testid="correlation-alert"
            >
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
              <div>
                <span className="font-semibold">
                  {alert.count}-symbol {alert.direction} cluster detected
                </span>
                <span className="text-gray-400 ml-2">
                  [{alert.symbols.join(', ')}] — score {alert.score}
                </span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Decision Feed */}
      <DecisionFeed decisions={decisions} live={!mockMode} />

      {/* ORB chart */}
      <ChartCard title="ORB Breakout Activity" data={breakoutData}
        type="area" color="#22c55e" height={250} />

      {/* Active Tickers section */}
      <div>
        {/* Header row with Add Ticker */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">Active Tickers</h2>
            {mockMode && (
              <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30
                px-2 py-1 rounded-full">
                Simulated · 2s
              </span>
            )}
          </div>
          <AddTickerForm onAdd={handleAddTicker} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          <AnimatePresence>
            {activeTickers.map((ticker) => (
              <motion.div
                key={ticker.symbol}
                layout
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.88, transition: { duration: 0.2 } }}
              >
                <TickerCard
                  symbol={ticker.symbol}
                  enabled={ticker.enabled}
                  currentPrice={ticker.current_price}
                  signalStrength={ticker.signal_strength}
                  trend={ticker.trend}
                  orbHigh={ticker.orb_levels?.['15m']?.high}
                  orbLow={ticker.orb_levels?.['15m']?.low}
                  atr={ticker.atr}
                  volumeRatio={ticker.volume_ratio}
                  metricToggles={tickerConfigs[ticker.symbol]}
                  onToggle={() => {}}
                  onConfigure={() => {}}
                  onMetricToggle={(metric) => handleMetricToggle(ticker.symbol, metric)}
                  onRemove={() => handleRemoveTicker(ticker.symbol)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {activeTickers.length === 0 && (
          <div className="text-center py-12" data-testid="no-tickers-placeholder">
            <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No active tickers</p>
            <p className="text-gray-500 text-sm">Use the input above to add a ticker</p>
          </div>
        )}
      </div>
    </div>
  );
};

import React, { useEffect, useState, useRef } from 'react';
import { Activity, TrendingUp, AlertCircle, Zap, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { MetricCard } from '../cards/MetricCard';
import { TickerCard } from '../cards/TickerCard';
import { ChartCard } from '../cards/ChartCard';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';
import { generateMockTickerList, DEFAULT_MOCK_SYMBOLS } from '@/lib/mockData';
import { TickerData } from '@/types';

// ── Correlation Breadth bar ────────────────────────────────────────────

interface Breadth {
  bullish: number;
  bearish: number;
  neutral: number;
  bullish_pct: number;
  bearish_pct: number;
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

// ── Main component ─────────────────────────────────────────────────────

export const TradingOverview: React.FC = () => {
  const { tickers, stats, setTickers, setStats, mockMode, correlationAlerts, addCorrelationAlert } =
    useStore();

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
    bullish: 0, bearish: 0, neutral: 0, bullish_pct: 0, bearish_pct: 0,
  });

  // Track mock prices between refreshes
  const mockPricesRef = useRef<TickerData[]>([]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, mockMode ? 2000 : 5000);
    return () => clearInterval(interval);
  }, [mockMode]);

  const loadData = async () => {
    try {
      if (mockMode) {
        // Use simulated data — refresh prices each call
        const symbols =
          mockPricesRef.current.length > 0
            ? mockPricesRef.current.map((t) => t.symbol)
            : DEFAULT_MOCK_SYMBOLS;
        const mockTickers = generateMockTickerList(symbols);
        mockPricesRef.current = mockTickers;
        setTickers(mockTickers);

        // Simulated market breadth
        const bulls = mockTickers.filter((t) => t.trend === 'bullish').length;
        const bears = mockTickers.filter((t) => t.trend === 'bearish').length;
        const total = mockTickers.length;
        setBreadth({
          bullish: bulls,
          bearish: bears,
          neutral: total - bulls - bears,
          bullish_pct: parseFloat(((bulls / total) * 100).toFixed(1)),
          bearish_pct: parseFloat(((bears / total) * 100).toFixed(1)),
        });
        return;
      }

      // Live data
      const [tickersResp, statsResp, corrResp] = await Promise.allSettled([
        api.getTickers(),
        api.getStats(),
        api.getCorrelation(),
      ]);

      if (tickersResp.status === 'fulfilled') {
        const raw: any[] = tickersResp.value.tickers || [];
        const mapped: TickerData[] = raw.map((t: any) =>
          typeof t === 'string' ? { symbol: t, enabled: true } : t,
        );
        setTickers(mapped);
      }

      if (statsResp.status === 'fulfilled') {
        setStats(statsResp.value);
      }

      if (corrResp.status === 'fulfilled') {
        const corrData = corrResp.value;
        // Add any new clusters to the alert store
        const incoming: any[] = corrData.clusters || [];
        if (incoming.length > 0 && correlationAlerts.length === 0) {
          incoming.forEach((c: any) => addCorrelationAlert(c));
        }
        if (corrData.breadth) setBreadth(corrData.breadth);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleMetricToggle = async (symbol: string, metric: string) => {
    const currentConfig = tickerConfigs[symbol] || {
      orb: true, atr: true, signal: true, volume: true, price: true, breakouts: true,
    };
    const newConfig = { ...currentConfig, [metric]: !currentConfig[metric] };
    setTickerConfigs({ ...tickerConfigs, [symbol]: newConfig });
    if (!mockMode) {
      try {
        await api.updateTickerConfig(symbol, { metrics: newConfig });
      } catch (err) {
        console.error(`Failed to update ${symbol} config:`, err);
      }
    }
  };

  const activeTickers = tickers.filter((t) => t.enabled);
  const totalBreakouts = breakoutData.reduce((sum, d) => sum + d.value, 0);
  const avgSignalStrength =
    activeTickers.length > 0
      ? activeTickers.reduce((sum, t) => sum + (t.signal_strength || 0), 0) / activeTickers.length
      : 0;

  return (
    <div className="space-y-6" data-testid="trading-overview">
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Active Tickers"
          value={activeTickers.length}
          subtitle="Currently monitored"
          icon={Activity}
          color="blue"
          trend="neutral"
        />
        <MetricCard
          title="ORB Breakouts"
          value={totalBreakouts}
          subtitle="Today"
          icon={TrendingUp}
          color="green"
          change="+12.5%"
          trend="up"
        />
        <MetricCard
          title="Avg Signal"
          value={avgSignalStrength.toFixed(1)}
          subtitle="Across all tickers"
          icon={Zap}
          color={avgSignalStrength >= 0 ? 'green' : 'red'}
        />
        <MetricCard
          title="System Status"
          value={mockMode ? 'Mock Mode' : stats?.running ? 'Running' : 'Stopped'}
          subtitle={mockMode ? 'Simulated data' : stats?.paused ? 'Paused' : 'Active'}
          icon={AlertCircle}
          color={mockMode ? 'yellow' : stats?.running ? 'green' : 'red'}
        />
      </div>

      {/* Market Breadth / Correlation Panel */}
      <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50
        backdrop-blur-sm shadow-xl p-6" data-testid="market-breadth-panel">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Market Breadth</h3>
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded-full">
            90-second window
          </span>
        </div>
        <BreadthBar breadth={breadth} />

        {/* Correlation cluster alerts */}
        <AnimatePresence>
          {correlationAlerts.slice(0, 3).map((alert, i) => (
            <motion.div
              key={`${alert.timestamp}-${i}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ delay: i * 0.1 }}
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

      {/* ORB Breakout Activity Chart */}
      <ChartCard
        title="ORB Breakout Activity"
        data={breakoutData}
        type="area"
        color="#22c55e"
        height={250}
      />

      {/* Ticker Cards Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-white">Active Tickers</h2>
          {mockMode && (
            <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30
              px-2 py-1 rounded-full">
              Simulated prices — updates every 2s
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {activeTickers.map((ticker) => (
            <TickerCard
              key={ticker.symbol}
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
              onToggle={() => console.log('Toggle', ticker.symbol)}
              onConfigure={() => console.log('Configure', ticker.symbol)}
              onMetricToggle={(metric) => handleMetricToggle(ticker.symbol, metric)}
            />
          ))}
        </div>

        {activeTickers.length === 0 && (
          <div className="text-center py-12" data-testid="no-tickers-placeholder">
            <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No active tickers</p>
            <p className="text-gray-500 text-sm">Add tickers to start monitoring</p>
          </div>
        )}
      </div>
    </div>
  );
};

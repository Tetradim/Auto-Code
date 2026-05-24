/**
 * Short Squeeze Dashboard Component
 * 
 * Provides real-time short interest monitoring with squeeze detection,
 * days-to-cover analysis, and risk assessment.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';

// ============================================================================
// Types
// ============================================================================

export interface ShortInterestData {
  symbol: string;
  shortInterest: number;
  shortInterestPct: number;
  avgDailyVolume: number;
  daysToCover: number;
  borrowRate: number;
  squeezeScore: number;
  squeezeRisk: 'minimal' | 'low' | 'moderate' | 'high' | 'extreme';
  volumeRatio: number;
  costBasis: number;
  timestamp: string;
}

export interface SqueezeSignal {
  level: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: string;
}

interface ShortSqueezeProps {
  symbols?: string[];
  refreshInterval?: number;
  showSignals?: boolean;
  showHistory?: boolean;
}

// ============================================================================
// Risk Colors
// ============================================================================

const RISK_COLORS = {
  minimal: '#22c55e',  // Green
  low: '#84cc16',     // Lime
  moderate: '#eab308', // Yellow
  high: '#f97316',   // Orange
  extreme: '#ef4444', // Red
};

const RiskBadge: React.FC<{ risk: string }> = ({ risk }) => (
  <span 
    className="px-2 py-1 rounded text-xs font-semibold"
    style={{ 
      backgroundColor: `${RISK_COLORS[risk as keyof typeof RISK_COLORS]}20`,
      color: RISK_COLORS[risk as keyof typeof RISK_COLORS],
      border: `1px solid ${RISK_COLORS[risk as keyof typeof RISK_COLORS]}40`
    }}
  >
    {risk.toUpperCase()}
  </span>
);

// ============================================================================
// Metric Card Component
// ============================================================================

const MetricCard: React.FC<{
  label: string;
  value: string | number;
  subValue?: string;
  trend?: 'up' | 'down' | 'stable';
  alert?: boolean;
}> = ({ label, value, subValue, trend }) => (
  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">{label}</div>
    <div className="text-2xl font-bold text-white">{value}</div>
    {subValue && (
      <div className={`text-xs mt-1 ${
        trend === 'up' ? 'text-red-400' : 
        trend === 'down' ? 'text-green-400' : 
        'text-slate-500'
      }`}>
        {subValue}
        {trend && (
          <span className="ml-1">
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
          </span>
        )}
      </div>
    )}
  </div>
);

// ============================================================================
// Signal List Component
// ============================================================================

const SignalList: React.FC<{ signals: SqueezeSignal[] }> = ({ signals }) => (
  <div className="space-y-2">
    {signals.map((signal, idx) => (
      <div 
        key={idx}
        className="flex items-start gap-2 p-3 rounded-lg"
        style={{
          backgroundColor: signal.level === 'critical' ? '#ef444415' :
                         signal.level === 'warning' ? '#f9731615' :
                         '#22c55e15',
          borderLeft: `3px solid ${
            signal.level === 'critical' ? '#ef4444' :
            signal.level === 'warning' ? '#f97316' :
            '#22c55e'
          }`
        }}
      >
        <span className="text-lg">
          {signal.level === 'critical' ? '🔴' : 
           signal.level === 'warning' ? '🟠' : '🟢'}
        </span>
        <div>
          <div className="text-sm text-slate-200">{signal.message}</div>
          <div className="text-xs text-slate-500">
            {new Date(signal.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    ))}
  </div>
);

// ============================================================================
// Main Dashboard Component
// ============================================================================

export const ShortSqueezeDashboard: React.FC<ShortSqueezeProps> = ({
  symbols = ['SPY', 'QQQ', 'IWM', 'TSLA', 'GME', 'AMC'],
  refreshInterval = 30000,
  showSignals = true,
  showHistory = true,
}) => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>(symbols[0]);
  const [data, setData] = useState<ShortInterestData | null>(null);
  const [history, setHistory] = useState<ShortInterestData[]>([]);
  const [signals, setSignals] = useState<SqueezeSignal[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch short interest data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      // In production, this would call the backend API
      // For demo, generate sample data
      const demoData: ShortInterestData = {
        symbol: selectedSymbol,
        shortInterest: Math.random() * 50000000 + 10000000,
        shortInterestPct: Math.random() * 30 + 5,
        avgDailyVolume: Math.random() * 100000000 + 20000000,
        daysToCover: Math.random() * 15 + 1,
        borrowRate: Math.random() * 2,
        squeezeScore: Math.random() * 100,
        squeezeRisk: ['minimal', 'low', 'moderate', 'high', 'extreme'][Math.floor(Math.random() * 5)] as any,
        volumeRatio: Math.random() * 2,
        costBasis: 150 + Math.random() * 50,
        timestamp: new Date().toISOString(),
      };
      setData(demoData);
      
      // Generate history
      const historyData = Array.from({ length: 30 }, (_, i) => ({
        ...demoData,
        daysToCover: demoData.daysToCover + (Math.random() - 0.5) * 5,
        shortInterestPct: demoData.shortInterestPct + (Math.random() - 0.5) * 10,
        squeezeScore: Math.max(0, Math.min(100, demoData.squeezeScore + (Math.random() - 0.5) * 30)),
        timestamp: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
      })).reverse();
      setHistory(historyData);
      
      // Generate signals based on data
      const newSignals: SqueezeSignal[] = [];
      if (demoData.daysToCover > 5) {
        newSignals.push({
          level: demoData.daysToCover > 10 ? 'critical' : 'warning',
          message: `${demoData.daysToCover.toFixed(1)} days to cover - ${demoData.daysToCover > 10 ? 'EXTREME' : 'HIGH'} squeeze risk`,
          timestamp: new Date().toISOString(),
        });
      }
      if (demoData.shortInterestPct > 20) {
        newSignals.push({
          level: demoData.shortInterestPct > 30 ? 'critical' : 'warning',
          message: `Short interest at ${demoData.shortInterestPct.toFixed(1)}% of float`,
          timestamp: new Date().toISOString(),
        });
      }
      if (demoData.borrowRate > 0.5) {
        newSignals.push({
          level: demoData.borrowRate > 1 ? 'critical' : 'warning',
          message: `Borrow fee ${(demoData.borrowRate * 100).toFixed(0)}% - expensive to short`,
          timestamp: new Date().toISOString(),
        });
      }
      setSignals(newSignals);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol]);

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  // Format large numbers
  const formatNumber = (num: number): string => {
    if (num >= 1000000000) return `${(num / 1000000000).toFixed(1)}B`;
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toFixed(0);
  };

  return (
    <div className="p-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            📊 Short Squeeze Dashboard
          </h1>
          <p className="text-slate-400 text-sm">Real-time squeeze detection & risk analysis</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-slate-800 text-white px-4 py-2 rounded-lg border border-slate-700"
          >
            {symbols.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button 
            onClick={fetchData}
            disabled={loading}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white font-medium"
          >
            {loading ? '⟳' : '↻'} Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard 
          label="Days to Cover"
          value={data?.daysToCover?.toFixed(1) || '--'}
          subValue={data ? `${data.daysToCover > 5 ? 'HIGH RISK' : 'Normal'}` : undefined}
          trend={data && data.daysToCover > 5 ? 'up' : 'stable'}
        />
        <MetricCard 
          label="Short Interest"
          value={data ? formatNumber(data.shortInterest) : '--'}
          subValue={data ? `${data.shortInterestPct.toFixed(1)}% of float` : undefined}
        />
        <MetricCard 
          label="Borrow Fee"
          value={data ? `${(data.borrowRate * 100).toFixed(1)}%` : '--'}
          subValue={data ? (data.borrowRate > 0.5 ? 'Expensive!' : 'Normal') : undefined}
          alert={Boolean(data && data.borrowRate > 0.5)}
        />
        <MetricCard 
          label="Squeeze Score"
          value={data?.squeezeScore?.toFixed(0) || '--'}
          subValue="/ 100"
          trend={data && data.squeezeScore > 50 ? 'up' : 'stable'}
        />
      </div>

      {/* Risk Assessment */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Current Risk */}
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Current Risk</h3>
          <div className="flex items-center gap-4">
            <div className="text-5xl font-bold" style={{ 
              color: data ? RISK_COLORS[data.squeezeRisk as keyof typeof RISK_COLORS] : '#22c55e' 
            }}>
              {data?.squeezeScore?.toFixed(0) || '--'}
            </div>
            <div>
              <RiskBadge risk={data?.squeezeRisk || 'minimal'} />
              <div className="text-xs text-slate-500 mt-2">/ 100</div>
            </div>
          </div>
        </div>

        {/* Volume Analysis */}
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Volume Analysis</h3>
          <div className="space-y-3">
            <div>
              <div className="text-xs text-slate-400">Avg Daily Volume</div>
              <div className="text-xl font-bold text-white">
                {data ? formatNumber(data.avgDailyVolume) : '--'}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Volume Ratio</div>
              <div className="text-xl font-bold text-white">
                {data?.volumeRatio?.toFixed(2) || '--'}x
              </div>
            </div>
          </div>
        </div>

        {/* Cost Basis */}
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Cost Basis</h3>
          <div className="space-y-3">
            <div>
              <div className="text-xs text-slate-400">Avg Short Price</div>
              <div className="text-xl font-bold text-white">
                ${data?.costBasis?.toFixed(2) || '--'}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">vs. Current</div>
              <div className="text-xl" style={{ 
                color: '#64748b'
              }}>
                --
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Signals */}
      {showSignals && signals.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">⚡ Squeeze Signals</h3>
          <SignalList signals={signals} />
        </div>
      )}

      {/* History Chart */}
      {showHistory && history.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Days to Cover History</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#64748b"
                  tickFormatter={(v) => new Date(v).toLocaleDateString()}
                />
                <YAxis stroke="#64748b" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                  labelFormatter={(v) => new Date(v).toLocaleDateString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="daysToCover" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 text-center text-xs text-slate-600">
        Short interest data refreshed every {refreshInterval / 1000}s • Data delayed 15min
      </div>
    </div>
  );
};

export default ShortSqueezeDashboard;

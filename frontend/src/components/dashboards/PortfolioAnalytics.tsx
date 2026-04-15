/**
 * Portfolio Analytics Dashboard
 * Shows portfolio composition, risk metrics, and rebalancing suggestions
 */
import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import { Wallet, TrendingUp, TrendingDown, AlertTriangle, RefreshCw, BarChart2, Scale } from 'lucide-react';

interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  market_value: number;
  weight: number;
  unrealized_pnl: number;
  realized_pnl: number;
}

interface PortfolioMetrics {
  total_equity: number;
  cash: number;
  cash_pct: number;
  buying_power: number;
  positions: Position[];
  position_count: number;
}

const COLORS = ['#4ade80', '#22d3ee', '#f472b6', '#fbbf24', '#a78bfa', '#fb923c'];

export function PortfolioAnalytics() {
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchPortfolio = async () => {
    try {
      const response = await fetch('/api/paper/portfolio');
      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
        setError(null);
      }
    } catch (err) {
      // Silently fail - paper trading may not be active
      setError('Paper trading not connected');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center gap-3 text-gray-400">
          <Wallet className="w-5 h-5" />
          <span>Portfolio Analytics</span>
        </div>
        <p className="text-gray-500 mt-4 text-sm">
          Paper trading session not active. Start a paper trading session to see portfolio analytics.
        </p>
      </div>
    );
  }

  const positionChartData = metrics.positions.map((p: Position) => ({
    name: p.symbol,
    value: p.market_value,
    weight: p.weight
  }));

  const pnlData = metrics.positions.map((p: Position) => ({
    name: p.symbol,
    unrealized: p.unrealized_pnl,
    realized: p.realized_pnl
  }));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <Wallet className="w-4 h-4" />
            <span className="text-sm">Total Equity</span>
          </div>
          <p className="text-2xl font-bold text-white">${metrics.total_equity.toLocaleString()}</p>
        </div>
        
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <Scale className="w-4 h-4" />
            <span className="text-sm">Cash</span>
          </div>
          <p className="text-2xl font-bold text-white">${metrics.cash.toLocaleString()}</p>
          <p className="text-xs text-gray-500">{metrics.cash_pct.toFixed(1)}% of portfolio</p>
        </div>
        
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <TrendingUp className="w-4 h-4" />
            <span className="text-sm">Positions</span>
          </div>
          <p className="text-2xl font-bold text-white">{metrics.position_count}</p>
          <p className="text-xs text-gray-500">${metrics.buying_power.toLocaleString()} buying power</p>
        </div>
        
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm">Diversification</span>
          </div>
          <p className={`text-2xl font-bold ${metrics.position_count > 3 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {metrics.position_count > 5 ? 'Good' : metrics.position_count > 2 ? 'Fair' : 'Low'}
          </p>
          <p className="text-xs text-gray-500">Min 5 recommended</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Allocation Pie Chart */}
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Portfolio Allocation</h3>
          {positionChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={positionChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {positionChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: any) => `$${(value as number)?.toLocaleString()}`}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No positions open
            </div>
          )}
        </div>

        {/* PnL Bar Chart */}
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Position P&L</h3>
          {pnlData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pnlData}>
                <XAxis dataKey="name" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                  formatter={(value: any) => `$${(value as number)?.toFixed(2)}`}
                />
                <Legend />
                <Bar dataKey="unrealized" name="Unrealized" fill="#4ade80" />
                <Bar dataKey="realized" name="Realized" fill="#22d3ee" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No positions for P&L
            </div>
          )}
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Open Positions</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                <th className="pb-3 font-medium">Symbol</th>
                <th className="pb-3 font-medium">Quantity</th>
                <th className="pb-3 font-medium">Avg Cost</th>
                <th className="pb-3 font-medium">Market Value</th>
                <th className="pb-3 font-medium">Weight</th>
                <th className="pb-3 font-medium">Unrealized P&L</th>
                <th className="pb-3 font-medium">Realized P&L</th>
              </tr>
            </thead>
            <tbody>
              {metrics.positions.map((pos) => (
                <tr key={pos.symbol} className="border-b border-gray-700/50 text-sm">
                  <td className="py-3 text-white font-medium">{pos.symbol}</td>
                  <td className="py-3 text-gray-300">{pos.quantity.toFixed(2)}</td>
                  <td className="py-3 text-gray-300">${pos.avg_cost.toFixed(2)}</td>
                  <td className="py-3 text-gray-300">${pos.market_value.toFixed(2)}</td>
                  <td className="py-3 text-gray-300">{pos.weight.toFixed(1)}%</td>
                  <td className={`py-3 ${pos.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${pos.unrealized_pnl.toFixed(2)}
                  </td>
                  <td className={`py-3 ${pos.realized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${pos.realized_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
              {metrics.positions.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    No open positions
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
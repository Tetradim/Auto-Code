import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  Legend,
} from 'recharts';

interface BacktestResult {
  equity_curve: { time: string; equity: number }[];
  trades: {
    entry_time: string;
    exit_time: string;
    entry_price: number;
    exit_price: number;
    pnl_pct: number;
  }[];
  final_capital: number;
  total_return_pct: number;
  win_rate: number;
  max_drawdown_pct: number;
  symbol: string;
}

const BacktestResultsChart: React.FC<{ results: BacktestResult }> = ({ results }) => {
  // Calculate drawdown for area shading
  const chartData = results.equity_curve.map((point) => point);
  
  let peak = results.equity_curve[0]?.equity || 10000;
  const dataWithDD = chartData.map((point) => {
    peak = Math.max(peak, point.equity);
    const dd = ((peak - point.equity) / peak) * 100;
    return { ...point, drawdown: Math.round(dd * 100) / 100 };
  });

  return (
    <div className="w-full bg-zinc-900 rounded-3xl p-6 border border-zinc-800">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-white">
          Backtest Results – {results.symbol}
        </h3>
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-zinc-400">Final Capital:</span>
            <span className="ml-2 font-mono text-green-400">
              ${results.final_capital.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-zinc-400">Total Return:</span>
            <span
              className={`ml-2 font-mono ${
                results.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {results.total_return_pct}%
            </span>
          </div>
          <div>
            <span className="text-zinc-400">Win Rate:</span>
            <span className="ml-2 font-mono text-white">{results.win_rate}%</span>
          </div>
          <div>
            <span className="text-zinc-400">Max DD:</span>
            <span className="ml-2 font-mono text-orange-400">
              -{results.max_drawdown_pct}%
            </span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={420}>
        <LineChart
          data={dataWithDD}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="time"
            tickFormatter={(t) => new Date(t).toLocaleDateString()}
            stroke="#a1a1aa"
          />
          <YAxis
            yAxisId="equity"
            stroke="#22c55e"
            tickFormatter={(v) => `$${v}`}
          />
          <YAxis
            yAxisId="drawdown"
            orientation="right"
            stroke="#f59e0b"
            tickFormatter={(v) => `${v}%`}
          />

          {/* Equity Curve */}
          <Line
            yAxisId="equity"
            type="monotone"
            dataKey="equity"
            stroke="#22c55e"
            strokeWidth={3}
            dot={false}
            name="Equity"
          />

          {/* Drawdown Area */}
          <Area
            yAxisId="drawdown"
            type="monotone"
            dataKey="drawdown"
            stroke="none"
            fill="#f59e0b"
            fillOpacity={0.2}
            name="Drawdown %"
          />

          <Tooltip
            contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3b82f6' }}
            labelStyle={{ color: '#a1a1aa' }}
            formatter={(value: number, name: string) => [
              name === 'equity' ? `$${value.toLocaleString()}` : `${value}%`,
              name === 'equity' ? 'Equity' : 'Drawdown',
            ]}
          />
          <Legend />
        </LineChart>
      </ResponsiveContainer>

      {/* Quick Trade List */}
      <div className="mt-8">
        <h4 className="text-sm font-medium text-zinc-400 mb-3">
          Trades ({results.trades.length})
        </h4>
        <div className="max-h-64 overflow-auto text-xs font-mono">
          {results.trades.length === 0 ? (
            <div className="text-zinc-500 py-2">No trades executed</div>
          ) : (
            results.trades.map((trade, i) => (
              <div
                key={i}
                className="flex justify-between py-2 border-b border-zinc-800 last:border-0"
              >
                <span className={trade.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {trade.pnl_pct >= 0 ? 'WIN' : 'LOSS'}
                </span>
                <span className="text-zinc-400">
                  {new Date(trade.entry_time).toLocaleDateString()} →{' '}
                  {new Date(trade.exit_time).toLocaleDateString()}
                </span>
                <span
                  className={trade.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}
                >
                  {trade.pnl_pct.toFixed(2)}%
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Monte Carlo Risk Analysis */}
      {results.monte_carlo && (
        <div className="mt-10 bg-zinc-900 rounded-3xl p-6 border border-zinc-800">
          <h3 className="text-lg font-semibold mb-6">
            Monte Carlo Risk Analysis ({results.monte_carlo.simulations} simulations)
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Median Outcome</div>
              <div className="text-3xl font-mono text-white mt-2">
                ${results.monte_carlo.median_final_equity.toLocaleString()}
              </div>
            </div>
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">5% Worst Case</div>
              <div className="text-3xl font-mono text-red-400 mt-2">
                ${results.monte_carlo.worst_case_equity.toLocaleString()}
              </div>
            </div>
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Profit Probability</div>
              <div className="text-3xl font-mono text-green-400 mt-2">
                {results.monte_carlo.probability_of_profit}%
              </div>
            </div>
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Avg Max Drawdown</div>
              <div className="text-3xl font-mono text-orange-400 mt-2">
                -{results.monte_carlo.mean_max_drawdown}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BacktestResultsChart;
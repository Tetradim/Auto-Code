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
  monte_carlo?: {
    status?: string;
    method?: string;
    confidence_level?: number;
    simulations: number;
    median_final_equity: number;
    worst_case_equity: number;
    best_case_equity?: number;
    probability_of_profit: number;
    probability_of_ruin?: number;
    mean_max_drawdown: number;
    value_at_risk?: number;
    value_at_risk_pct?: number;
    conditional_value_at_risk?: number;
    conditional_value_at_risk_pct?: number;
    max_drawdown_percentiles?: {
      p50: number;
      p95: number;
      p99: number;
    };
    saved_chart_set?: {
      run_id: string;
      chart_count: number;
      manifest_path: string;
      charts: { name: string; path: string; api_path?: string }[];
    };
  };
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
            formatter={(value: any, name: any) => [
              name === 'equity' ? `$${value?.toLocaleString()}` : `${value}%`,
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
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h3 className="text-lg font-semibold">
                Monte Carlo Risk Analysis ({results.monte_carlo.simulations} simulations)
              </h3>
              <div className="text-xs text-zinc-500 mt-1">
                {(results.monte_carlo.method || 'bootstrap').replace('_', ' ')} method at{' '}
                {Math.round((results.monte_carlo.confidence_level || 0.95) * 100)}% confidence
              </div>
            </div>
            {results.monte_carlo.status && (
              <span className="text-xs uppercase tracking-wide text-zinc-400 border border-zinc-700 rounded px-2 py-1">
                {results.monte_carlo.status}
              </span>
            )}
          </div>
          
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
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Value at Risk</div>
              <div className="text-3xl font-mono text-red-300 mt-2">
                ${(results.monte_carlo.value_at_risk || 0).toLocaleString()}
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                {(results.monte_carlo.value_at_risk_pct || 0).toFixed(2)}%
              </div>
            </div>
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Expected Shortfall</div>
              <div className="text-3xl font-mono text-red-300 mt-2">
                ${(results.monte_carlo.conditional_value_at_risk || 0).toLocaleString()}
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                {(results.monte_carlo.conditional_value_at_risk_pct || 0).toFixed(2)}%
              </div>
            </div>
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Ruin Probability</div>
              <div className="text-3xl font-mono text-orange-300 mt-2">
                {results.monte_carlo.probability_of_ruin || 0}%
              </div>
            </div>
            <div className="bg-zinc-800 p-5 rounded-2xl">
              <div className="text-zinc-400 text-sm">Drawdown p95</div>
              <div className="text-3xl font-mono text-orange-300 mt-2">
                -{results.monte_carlo.max_drawdown_percentiles?.p95 || 0}%
              </div>
            </div>
          </div>

          {results.monte_carlo.saved_chart_set && (
            <div className="mt-6 border border-zinc-800 rounded-2xl p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-white">Saved Chart Bundle</h4>
                  <div className="text-xs text-zinc-500 mt-1">
                    {results.monte_carlo.saved_chart_set.chart_count} chart datasets saved for{' '}
                    {results.monte_carlo.saved_chart_set.run_id}
                  </div>
                </div>
                <code className="text-xs text-zinc-400 break-all text-right">
                  {results.monte_carlo.saved_chart_set.manifest_path}
                </code>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-4">
                {results.monte_carlo.saved_chart_set.charts.map((chart) => (
                  <div key={chart.name} className="text-xs bg-zinc-800 rounded-lg p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="text-zinc-200">{chart.name.replace(/_/g, ' ')}</div>
                      {chart.api_path && (
                        <a
                          href={chart.api_path}
                          target="_blank"
                          rel="noreferrer"
                          className="shrink-0 text-blue-300 hover:text-blue-200"
                        >
                          Open JSON
                        </a>
                      )}
                    </div>
                    {chart.api_path && (
                      <div className="text-blue-400 break-all mt-1">{chart.api_path}</div>
                    )}
                    <div className="text-zinc-500 break-all mt-1">{chart.path}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BacktestResultsChart;

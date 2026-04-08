import React, { useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, Percent } from 'lucide-react';
import { MetricCard } from '../cards/MetricCard';
import { ChartCard } from '../cards/ChartCard';
import { motion } from 'framer-motion';

export const PnLTracking: React.FC = () => {
  const [pnlHistory] = useState([
    { timestamp: '09:30', value: 0 },
    { timestamp: '10:00', value: 125 },
    { timestamp: '10:30', value: 230 },
    { timestamp: '11:00', value: 180 },
    { timestamp: '11:30', value: 310 },
    { timestamp: '12:00', value: 425 },
    { timestamp: '12:30', value: 380 },
    { timestamp: '13:00', value: 490 },
  ]);

  const [drawdownHistory] = useState([
    { timestamp: '09:30', value: 0 },
    { timestamp: '10:00', value: -2.5 },
    { timestamp: '10:30', value: -1.8 },
    { timestamp: '11:00', value: -3.2 },
    { timestamp: '11:30', value: -1.5 },
    { timestamp: '12:00', value: -0.8 },
    { timestamp: '12:30', value: -2.1 },
    { timestamp: '13:00', value: -1.2 },
  ]);

  const [tickerPnL] = useState([
    { symbol: 'SPY', realized: 245.50, unrealized: 32.10, totalTrades: 12 },
    { symbol: 'QQQ', realized: 189.30, unrealized: -15.25, totalTrades: 8 },
    { symbol: 'NVDA', realized: 310.75, unrealized: 48.60, totalTrades: 15 },
    { symbol: 'AAPL', realized: -54.20, unrealized: 12.30, totalTrades: 6 },
  ]);

  const totalRealized = tickerPnL.reduce((sum, t) => sum + t.realized, 0);
  const totalUnrealized = tickerPnL.reduce((sum, t) => sum + t.unrealized, 0);
  const totalPnL = totalRealized + totalUnrealized;
  const currentDrawdown = Math.min(...drawdownHistory.map(d => d.value));
  const maxDrawdown = -3.2; // Mock data

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total P&L"
          value={`$${totalPnL.toFixed(2)}`}
          subtitle="Realized + Unrealized"
          icon={DollarSign}
          color={totalPnL >= 0 ? 'green' : 'red'}
          trend={totalPnL >= 0 ? 'up' : 'down'}
          change={`${totalPnL >= 0 ? '+' : ''}${((totalPnL / 10000) * 100).toFixed(2)}%`}
        />
        <MetricCard
          title="Realized P&L"
          value={`$${totalRealized.toFixed(2)}`}
          subtitle="Closed positions"
          icon={TrendingUp}
          color={totalRealized >= 0 ? 'green' : 'red'}
        />
        <MetricCard
          title="Unrealized P&L"
          value={`$${totalUnrealized.toFixed(2)}`}
          subtitle="Open positions"
          icon={TrendingDown}
          color={totalUnrealized >= 0 ? 'green' : 'red'}
        />
        <MetricCard
          title="Max Drawdown"
          value={`${currentDrawdown.toFixed(2)}%`}
          subtitle="Current session"
          icon={Percent}
          color={Math.abs(currentDrawdown) > 5 ? 'red' : 'yellow'}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard
          title="Cumulative P&L"
          data={pnlHistory}
          type="area"
          color="#22c55e"
          height={300}
        />
        <ChartCard
          title="Drawdown %"
          data={drawdownHistory}
          type="area"
          color="#ef4444"
          height={300}
        />
      </div>

      {/* Per-Ticker P&L Table */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-4">Per-Ticker Performance</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {tickerPnL.map((ticker) => {
            const total = ticker.realized + ticker.unrealized;
            return (
              <motion.div
                key={ticker.symbol}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50
                  backdrop-blur-sm shadow-xl hover:shadow-2xl transition-all duration-300"
              >
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-2xl font-bold text-white">{ticker.symbol}</h3>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium
                      ${total >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {total >= 0 ? '+' : ''}{total.toFixed(2)}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center pb-3 border-b border-gray-700/50">
                      <span className="text-sm text-gray-400">Realized P&L</span>
                      <span className={`text-lg font-semibold ${
                        ticker.realized >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        ${ticker.realized.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pb-3 border-b border-gray-700/50">
                      <span className="text-sm text-gray-400">Unrealized P&L</span>
                      <span className={`text-lg font-semibold ${
                        ticker.unrealized >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        ${ticker.unrealized.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-400">Total Trades</span>
                      <span className="text-lg font-semibold text-white">{ticker.totalTrades}</span>
                    </div>
                  </div>

                  {/* P&L Bar */}
                  <div className="mt-4">
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${
                          total >= 0 
                            ? 'bg-gradient-to-r from-green-500 to-green-400' 
                            : 'bg-gradient-to-r from-red-500 to-red-400'
                        }`}
                        style={{ width: `${Math.min(Math.abs(total / 500) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

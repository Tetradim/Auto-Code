import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, DollarSign, Target } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface TickerCardProps {
  symbol: string;
  enabled: boolean;
  currentPrice?: number;
  signalStrength?: number;
  trend?: string;
  orbHigh?: number;
  orbLow?: number;
  atr?: number;
  volumeRatio?: number;
  priceHistory?: Array<{ value: number }>;
  onToggle?: () => void;
  onConfigure?: () => void;
}

export const TickerCard: React.FC<TickerCardProps> = ({
  symbol,
  enabled,
  currentPrice,
  signalStrength = 0,
  trend = 'neutral',
  orbHigh,
  orbLow,
  atr,
  volumeRatio,
  priceHistory = [],
  onToggle,
  onConfigure,
}) => {
  const getTrendColor = () => {
    if (trend === 'bullish') return 'text-green-400';
    if (trend === 'bearish') return 'text-red-400';
    return 'text-gray-400';
  };

  const getTrendIcon = () => {
    if (trend === 'bullish') return <TrendingUp className="w-5 h-5" />;
    if (trend === 'bearish') return <TrendingDown className="w-5 h-5" />;
    return <Activity className="w-5 h-5" />;
  };

  const getSignalColor = () => {
    if (signalStrength >= 5) return 'from-green-500/30 to-green-600/10 border-green-500/50';
    if (signalStrength <= -5) return 'from-red-500/30 to-red-600/10 border-red-500/50';
    return 'from-gray-700/30 to-gray-800/10 border-gray-600/50';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      className={`relative overflow-hidden rounded-xl border backdrop-blur-sm
        bg-gradient-to-br ${getSignalColor()}
        shadow-lg hover:shadow-2xl transition-all duration-300
        ${!enabled && 'opacity-60'}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-2xl font-bold text-white">{symbol}</h3>
            <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${getTrendColor()} bg-black/30`}>
              {getTrendIcon()}
              <span className="capitalize">{trend}</span>
            </div>
          </div>
          
          <button
            onClick={onToggle}
            className={`px-4 py-2 rounded-lg font-medium transition-all
              ${enabled 
                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' 
                : 'bg-gray-700/20 text-gray-400 hover:bg-gray-700/30'
              }`}
          >
            {enabled ? 'Active' : 'Paused'}
          </button>
        </div>
      </div>

      {/* Price & Chart */}
      <div className="p-4">
        {currentPrice && (
          <div className="flex items-baseline gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-gray-400" />
            <span className="text-3xl font-bold text-white">
              {currentPrice.toFixed(2)}
            </span>
          </div>
        )}

        {priceHistory.length > 0 && (
          <div className="h-20 mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceHistory}>
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke={trend === 'bullish' ? '#22c55e' : trend === 'bearish' ? '#ef4444' : '#6b7280'}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          {orbHigh !== undefined && orbLow !== undefined && (
            <div className="bg-black/20 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Target className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-gray-400">ORB Range</span>
              </div>
              <p className="text-sm font-semibold text-white">
                ${orbLow.toFixed(2)} - ${orbHigh.toFixed(2)}
              </p>
            </div>
          )}

          {atr !== undefined && (
            <div className="bg-black/20 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4 text-purple-400" />
                <span className="text-xs text-gray-400">ATR</span>
              </div>
              <p className="text-sm font-semibold text-white">${atr.toFixed(2)}</p>
            </div>
          )}

          <div className="bg-black/20 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-gray-400">Signal</span>
            </div>
            <p className={`text-sm font-semibold ${signalStrength >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {signalStrength.toFixed(1)}
            </p>
          </div>

          {volumeRatio !== undefined && (
            <div className="bg-black/20 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="text-xs text-gray-400">Volume</span>
              </div>
              <p className="text-sm font-semibold text-white">{volumeRatio.toFixed(2)}x</p>
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-gray-700/50 flex gap-2">
        <button
          onClick={onConfigure}
          className="flex-1 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg
            font-medium transition-all"
        >
          Configure
        </button>
      </div>

      {/* Glow effect */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      </div>
    </motion.div>
  );
};

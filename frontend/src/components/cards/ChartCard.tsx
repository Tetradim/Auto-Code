import React from 'react';
import { motion } from 'framer-motion';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface ChartCardProps {
  title: string;
  data: Array<{ timestamp: string; value: number; label?: string }>;
  type?: 'line' | 'area';
  color?: string;
  showTrend?: boolean;
  height?: number;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  data,
  type = 'line',
  color = '#3b82f6',
  showTrend = true,
  height = 200,
  className = '',
}) => {
  const latestValue = data[data.length - 1]?.value || 0;
  const previousValue = data[data.length - 2]?.value || 0;
  const trend = latestValue >= previousValue ? 'up' : 'down';
  const trendPercent = previousValue !== 0 
    ? (((latestValue - previousValue) / previousValue) * 100).toFixed(2)
    : '0.00';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`relative rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50
        backdrop-blur-sm shadow-xl hover:shadow-2xl transition-all duration-300 ${className}`}
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {showTrend && (
            <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium
              ${trend === 'up' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {trend === 'up' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              <span>{trendPercent}%</span>
            </div>
          )}
        </div>

        <div style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            {type === 'area' ? (
              <AreaChart data={data}>
                <defs>
                  <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#6b7280" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis 
                  stroke="#6b7280" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1f2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#9ca3af' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#gradient-${title})`}
                  animationDuration={1000}
                />
              </AreaChart>
            ) : (
              <LineChart data={data}>
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#6b7280" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis 
                  stroke="#6b7280" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1f2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#9ca3af' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke={color}
                  strokeWidth={2}
                  dot={false}
                  animationDuration={1000}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    </motion.div>
  );
};

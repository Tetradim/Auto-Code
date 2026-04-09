import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface ChartDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

interface ChartCardProps {
  title: string;
  data: ChartDataPoint[];
  type?: 'line' | 'area';
  color?: string;
  showTrend?: boolean;
  height?: number;
  className?: string;
}

function buildSvgPath(
  data: ChartDataPoint[],
  width: number,
  height: number,
  filled: boolean,
): string {
  if (data.length < 2) return '';
  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const padY = height * 0.08;
  const innerH = height - padY * 2;

  const pts = data.map((d, i) => ({
    x: (i / (data.length - 1)) * width,
    y: padY + innerH - ((d.value - min) / range) * innerH,
  }));

  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  if (filled) {
    return `${line} L${pts[pts.length - 1].x.toFixed(1)},${height} L0,${height} Z`;
  }
  return line;
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
  const latestValue = data[data.length - 1]?.value ?? 0;
  const previousValue = data[data.length - 2]?.value ?? 0;
  const trendUp = latestValue >= previousValue;
  const trendPercent =
    previousValue !== 0
      ? (((latestValue - previousValue) / Math.abs(previousValue)) * 100).toFixed(2)
      : '0.00';

  const svgW = 600;
  const svgH = height;
  const filled = type === 'area';
  const pathD = buildSvgPath(data, svgW, svgH, filled);

  // Build tick labels
  const tickCount = Math.min(data.length, 6);
  const tickIndexes = data.length <= tickCount
    ? data.map((_, i) => i)
    : Array.from({ length: tickCount }, (_, i) =>
        Math.round((i / (tickCount - 1)) * (data.length - 1)),
      );

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`relative rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50
        backdrop-blur-sm shadow-xl hover:shadow-2xl transition-all duration-300 ${className}`}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {showTrend && data.length >= 2 && (
            <div
              className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                trendUp ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}
            >
              {trendUp ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span>{trendPercent}%</span>
            </div>
          )}
        </div>

        {/* SVG Chart */}
        <div style={{ height }} className="w-full overflow-hidden">
          {data.length < 2 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500 text-sm">No data yet</p>
            </div>
          ) : (
            <svg
              viewBox={`0 0 ${svgW} ${svgH}`}
              preserveAspectRatio="none"
              className="w-full h-full"
            >
              <defs>
                <linearGradient id={`grad-${title}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity="0.35" />
                  <stop offset="95%" stopColor={color} stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* Grid lines */}
              {[0.25, 0.5, 0.75].map((frac) => (
                <line
                  key={frac}
                  x1="0"
                  y1={svgH * frac}
                  x2={svgW}
                  y2={svgH * frac}
                  stroke="#374151"
                  strokeWidth="1"
                  strokeDasharray="4,4"
                />
              ))}

              {/* Fill */}
              {filled && (
                <path
                  d={pathD}
                  fill={`url(#grad-${title})`}
                  stroke="none"
                />
              )}

              {/* Line */}
              <path
                d={pathD.split(' Z')[0]}
                fill="none"
                stroke={color}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* X-axis labels */}
              {tickIndexes.map((idx, i) => {
                const xPos = (idx / (data.length - 1)) * svgW;
                const anchor =
                  i === 0 ? 'start' : i === tickIndexes.length - 1 ? 'end' : 'middle';
                return (
                  <text
                    key={idx}
                    x={xPos}
                    y={svgH - 2}
                    fill="#6b7280"
                    fontSize="18"
                    textAnchor={anchor}
                  >
                    {data[idx].timestamp}
                  </text>
                );
              })}
            </svg>
          )}
        </div>
      </div>
    </motion.div>
  );
};

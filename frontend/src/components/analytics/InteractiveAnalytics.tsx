/**
 * Interactive Analytics Dashboard
 * Cross-chart interaction, drill-down, and real-time synchronization
 */
import React, { useState, useMemo, useCallback } from 'react';
import { 
  TrendingUp, 
  TrendingDown,
  Activity,
  Download,
  Settings,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
type ChartType = 'line' | 'area' | 'bar' | 'candlestick' | 'heatmap';
type Timeframe = '1H' | '1D' | '1W' | '1M';

interface AnalyticsConfig {
  chartType: ChartType;
  timeframe: Timeframe;
  showVolume: boolean;
  showMA: boolean;
  showBollinger: boolean;
  crosshair: boolean;
}

interface SelectionState {
  symbols: string[];
}

// Default config
const DEFAULT_CONFIG: AnalyticsConfig = {
  chartType: 'line',
  timeframe: '1D',
  showVolume: true,
  showMA: true,
  showBollinger: false,
  crosshair: true
};

// Context for cross-chart sync
interface ChartSyncContext {
  selections: Record<string, string[]>;
  hoveredSymbol: string | null;
  config: AnalyticsConfig;
  notifySelection: (chartId: string, symbols: string[]) => void;
  notifyHover: (symbol: string | null) => void;
}

export const ChartSyncContext = React.createContext<ChartSyncContext>({
  selections: {},
  hoveredSymbol: null,
  config: DEFAULT_CONFIG,
  notifySelection: () => {},
  notifyHover: () => {}
});

// Interactive chart with selection sync
interface InteractiveChartProps {
  id: string;
  symbol: string;
  data: any[];
  onSelect?: (symbols: string[]) => void;
  onDrillDown?: (data: any) => void;
}

export const InteractiveChart: React.FC<InteractiveChartProps> = ({
  id,
  onSelect
}) => {
  const ctx = React.useContext(ChartSyncContext);
  const [selection, setSelection] = useState<string[]>([]);
  
  const handleClick = useCallback((point: any) => {
    if (point.symbol) {
      const newSelection = selection.includes(point.symbol)
        ? selection.filter(s => s !== point.symbol)
        : [...selection, point.symbol];
      
      setSelection(newSelection);
      ctx.notifySelection(id, newSelection);
      onSelect?.(newSelection);
    }
  }, [selection, id, onSelect]);
  
  return (
    <div className="relative">
      <div className="chart-content" />
    </div>
  );
};

// Draggable chart card
interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  minimizable?: boolean;
  onRemove?: () => void;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  children,
  className,
  minimizable = true,
  onRemove
}) => {
  const [minimized, setMinimized] = useState(false);
  
  return (
    <div className={cn(
      "bg-gray-800 rounded-xl border border-gray-700 overflow-hidden",
      "transition-all duration-300",
      minimized && "h-12",
      className
    )}>
      <div className="flex items-center justify-between p-3 border-b border-gray-700 bg-gray-900/30">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <div className="flex items-center gap-1">
          {minimizable && (
            <button
              onClick={() => setMinimized(!minimized)}
              className="p-1.5 text-gray-400 hover:text-white"
            >
              {minimized ? <TrendingUp className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
            </button>
          )}
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1.5 text-gray-400 hover:text-red-400"
            >
              ×
            </button>
          )}
        </div>
      </div>
      {!minimized && (
        <div className="p-3">
          {children}
        </div>
      )}
    </div>
  );
};

// Settings toolbar
interface SettingsToolbarProps {
  onExport?: () => void;
  onRefresh?: () => void;
}

export const SettingsToolbar: React.FC<SettingsToolbarProps> = ({
  onExport,
  onRefresh
}) => {
  return (
    <div className="flex items-center gap-2 p-2 bg-gray-800 rounded-lg">
      <button onClick={onRefresh} className="p-2 text-gray-400 hover:text-white" title="Refresh">
        <RefreshCw className="w-4 h-4" />
      </button>
      <button onClick={onExport} className="p-2 text-gray-400 hover:text-white" title="Export">
        <Download className="w-4 h-4" />
      </button>
    </div>
  );
};

// Correlation heatmap
interface CorrelationHeatmapProps {
  data: [string, string, number][];
  onCellClick?: (x: string, y: string) => void;
}

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({
  data,
  onCellClick
}) => {
  const [hoveredCell, setHoveredCell] = useState<[string, string] | null>(null);
  
  const symbols = useMemo(() => {
    const set = new Set<string>();
    data.forEach(([x, y]) => { set.add(x); set.add(y); });
    return Array.from(set).sort();
  }, [data]);
  
  const getColor = (corr: number) => {
    if (corr > 0.7) return 'bg-emerald-600';
    if (corr > 0.4) return 'bg-emerald-800';
    if (corr > 0) return 'bg-emerald-900';
    if (corr > -0.4) return 'bg-red-900';
    if (corr > -0.7) return 'bg-red-800';
    return 'bg-red-600';
  };
  
  return (
    <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${symbols.length}, minmax(30px, 1fr))` }}>
      {symbols.map(y => (
        <React.Fragment key={y}>
          {symbols.map(x => {
            const cell = data.find(([sx, syr]) => sx === x && syr === y);
            const corr = cell?.[2] || 0;
            return (
              <div
                key={`${x}-${y}`}
                onClick={() => onCellClick?.(x, y)}
                onMouseEnter={() => setHoveredCell([x, y])}
                onMouseLeave={() => setHoveredCell(null)}
                className={cn(
                  "h-8 rounded cursor-pointer transition-colors flex items-center justify-center text-xs",
                  getColor(corr),
                  hoveredCell?.[0] === x && hoveredCell?.[1] === y && "ring-2 ring-white"
                )}
              >
                {corr.toFixed(2)}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
};

// P&L attribution
interface AttributionChartProps {
  data: { symbol: string; pnl: number }[];
}

export const AttributionChart: React.FC<AttributionChartProps> = ({ data }) => {
  const sorted = useMemo(() => 
    [...data].sort((a, b) => b.pnl - a.pnl)
  , [data]);
  
  const maxPnl = Math.max(...sorted.map(s => Math.abs(s.pnl)), 1);
  
  return (
    <div className="space-y-2">
      {sorted.map(item => (
        <div key={item.symbol} className="flex items-center gap-3">
          <div className="w-16 text-sm text-gray-400">{item.symbol}</div>
          <div className="flex-1 h-6 bg-gray-700 rounded overflow-hidden">
            <div
              className={cn(
                "h-full transition-all",
                item.pnl >= 0 ? "bg-emerald-500" : "bg-red-500"
              )}
              style={{ 
                width: `${(Math.abs(item.pnl) / maxPnl) * 100}%`,
                marginLeft: item.pnl < 0 ? 'auto' : 0
              }}
            />
          </div>
          <div className="w-16 text-sm text-right">
            <span className={item.pnl >= 0 ? "text-emerald-400" : "text-red-400"}>
              {item.pnl >= 0 ? '+' : ''}{item.pnl.toFixed(0)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};

// Analytics summary cards
interface AnalyticsSummaryProps {
  metrics: {
    totalValue: number;
    dayPnl: number;
    totalPnl: number;
    var95: number;
  };
}

export const AnalyticsSummary: React.FC<AnalyticsSummaryProps> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-xs text-gray-400 mb-1">Portfolio Value</div>
        <div className="text-xl font-bold text-white">
          ${metrics.totalValue.toLocaleString()}
        </div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-xs text-gray-400 mb-1">Day P&L</div>
        <div className={cn(
          "text-xl font-bold",
          metrics.dayPnl >= 0 ? "text-emerald-400" : "text-red-400"
        )}>
          {metrics.dayPnl >= 0 ? '+' : ''}{metrics.dayPnl.toFixed(0)}
        </div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-xs text-gray-400 mb-1">Total P&L</div>
        <div className={cn(
          "text-xl font-bold",
          metrics.totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
        )}>
          {metrics.totalPnl >= 0 ? '+' : ''}{metrics.totalPnl.toFixed(0)}
        </div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-xs text-gray-400 mb-1">VaR (95%)</div>
        <div className="text-xl font-bold text-amber-400">
          ${metrics.var95.toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default {
  InteractiveChart,
  ChartCard,
  SettingsToolbar,
  CorrelationHeatmap,
  AttributionChart,
  AnalyticsSummary
};
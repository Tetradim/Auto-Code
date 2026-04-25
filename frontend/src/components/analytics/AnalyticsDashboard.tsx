/**
 * Analytics Dashboard with Enhanced Customization
 * Multiple chart types, layouts, and real-time analytics
 */
import React, { useState, useMemo, useEffect } from 'react';
import { 
  LayoutDashboard,
  Settings,
  Download,
  RefreshCw,
  ChevronDown,
  Filter,
  Target,
  TrendingUp,
  Activity,
  BarChart3,
  PieChart,
  Grid3X3
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
type ChartType = 'line' | 'area' | 'bar' | 'candlestick' | 'heatmap' | 'radar';
type Layout = 'grid' | 'list' | 'heatmap' | 'radar';
type Theme = 'dark' | 'light' | 'matrix';

// Customization options
interface DashboardConfig {
  layout: Layout;
  chartType: ChartType;
  theme: Theme;
  timeframe: string;
  showVolume: boolean;
  showMA: boolean;
  showBollinger: boolean;
  showRSI: boolean;
  showMACD: boolean;
  autoRefresh: boolean;
  refreshInterval: number;
}

const DEFAULT_CONFIG: DashboardConfig = {
  layout: 'grid',
  chartType: 'line',
  theme: 'dark',
  timeframe: '1D',
  showVolume: true,
  showMA: true,
  showBollinger: false,
  showRSI: false,
  showMACD: false,
  autoRefresh: true,
  refreshInterval: 5000
};

// Demo data generators
function generateDemoData(symbols: string[], days: number = 30) {
  const data: Record<string, any[]> = {};
  
  symbols.forEach(sym => {
    let price = 100 + Math.random() * 100;
    const points = [];
    
    for (let i = 0; i < days; i++) {
      const change = (Math.random() - 0.5) * 5;
      price = Math.max(price + change, 10);
      points.push({
        date: new Date(Date.now() - (days - i) * 86400000).toISOString(),
        open: price - Math.random() * 2,
        high: price + Math.random() * 3,
        low: price - Math.random() * 3,
        close: price,
        volume: Math.floor(Math.random() * 10000000),
        delta: (Math.random() - 0.5) * 0.5,
        theta: -(Math.random() * 0.1),
        gamma: Math.random() * 0.02,
        vega: Math.random() * 0.2,
      });
    }
    data[sym] = points;
  });
  
  return data;
}

// Settings dropdown component
interface SettingsDropdownProps {
  config: DashboardConfig;
  onChange: (config: Partial<DashboardConfig>) => void;
}

const SettingsDropdown: React.FC<SettingsDropdownProps> = ({ config, onChange }) => {
  const [open, setOpen] = useState(false);
  
  const options = {
    layout: [
      { value: 'grid', label: 'Grid View' },
      { value: 'list', label: 'List View' },
      { value: 'heatmap', label: 'Heatmap' },
      { value: 'radar', label: 'Radar' },
    ],
    chartType: [
      { value: 'line', label: 'Line' },
      { value: 'area', label: 'Area' },
      { value: 'bar', label: 'Bar' },
      { value: 'candlestick', label: 'Candlestick' },
      { value: 'heatmap', label: 'Heatmap' },
    ],
    timeframe: [
      { value: '1H', label: '1 Hour' },
      { value: '1D', label: '1 Day' },
      { value: '1W', label: '1 Week' },
      { value: '1M', label: '1 Month' },
    ],
    theme: [
      { value: 'dark', label: 'Dark' },
      { value: 'light', label: 'Light' },
      { value: 'matrix', label: 'Matrix' },
    ],
  };
  
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg text-gray-300 hover:text-white"
      >
        <Settings className="w-4 h-4" />
        <span className="text-sm">Customize</span>
        <ChevronDown className={cn("w-4 h-4 transition-transform", open && "rotate-180")} />
      </button>
      
      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-gray-800 rounded-xl border border-gray-700 shadow-xl z-50 p-4 space-y-4">
          {/* Layout */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Dashboard Layout</label>
            <select
              value={config.layout}
              onChange={e => onChange({ layout: e.target.value as Layout })}
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
            >
              {options.layout.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          
          {/* Chart Type */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Chart Type</label>
            <select
              value={config.chartType}
              onChange={e => onChange({ chartType: e.target.value as ChartType })}
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
            >
              {options.chartType.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          
          {/* Timeframe */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Timeframe</label>
            <select
              value={config.timeframe}
              onChange={e => onChange({ timeframe: e.target.value })}
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
            >
              {options.timeframe.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          
          {/* Indicators */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Indicators</label>
            <div className="space-y-2">
              {[
                { key: 'showVolume', label: 'Volume' },
                { key: 'showMA', label: 'Moving Average' },
                { key: 'showBollinger', label: 'Bollinger Bands' },
                { key: 'showRSI', label: 'RSI' },
                { key: 'showMACD', label: 'MACD' },
              ].map(ind => (
                <label key={ind.key} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config[ind.key as keyof DashboardConfig] as boolean}
                    onChange={e => onChange({ [ind.key]: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-300">{ind.label}</span>
                </label>
              ))}
            </div>
          </div>
          
          {/* Auto Refresh */}
          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={config.autoRefresh}
                onChange={e => onChange({ autoRefresh: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm text-gray-300">Auto Refresh</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
};

// Preset selector
interface PresetSelectorProps {
  onSelect: (preset: string) => void;
}

const PresetSelector: React.FC<PresetSelectorProps> = ({ onSelect }) => {
  const [open, setOpen] = useState(false);
  
  const presets = [
    { id: 'default', name: 'Default', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'greeks', name: 'Greeks Focus', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'signals', name: 'Signals View', icon: <Activity className="w-4 h-4" /> },
    { id: 'heatmap', name: 'Correlation', icon: <Grid3X3 className="w-4 h-4" /> },
    { id: 'radar', name: 'Radar View', icon: <Target className="w-4 h-4" /> },
  ];
  
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg text-gray-300 hover:text-white"
      >
        <Filter className="w-4 h-4" />
        <span className="text-sm">Presets</span>
      </button>
      
      {open && (
        <div className="absolute left-0 top-full mt-2 w-48 bg-gray-800 rounded-xl border border-gray-700 shadow-xl z-50">
          {presets.map(preset => (
            <button
              key={preset.id}
              onClick={() => { onSelect(preset.id); setOpen(false); }}
              className="flex items-center gap-2 w-full px-4 py-2 text-gray-300 hover:bg-gray-700 first:rounded-t-xl last:rounded-b-xl"
            >
              {preset.icon}
              <span className="text-sm">{preset.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// Analytics toolbar
interface AnalyticsToolbarProps {
  config: DashboardConfig;
  onConfigChange: (config: Partial<DashboardConfig>) => void;
  onRefresh: () => void;
  onExport: () => void;
}

export const AnalyticsToolbar: React.FC<AnalyticsToolbarProps> = ({
  config,
  onConfigChange,
  onRefresh,
  onExport
}) => {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-800 rounded-xl border border-gray-700">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold text-white">Analytics</h2>
        <span className="text-sm text-gray-400">{config.timeframe}</span>
      </div>
      
      <div className="flex items-center gap-2">
        <PresetSelector onSelect={preset => {
          // Apply preset
          const presets: Record<string, DashboardConfig> = {
            default: { ...DEFAULT_CONFIG },
            greeks: { ...DEFAULT_CONFIG, chartType: 'radar', showMA: true },
            signals: { ...DEFAULT_CONFIG, chartType: 'bar', showVolume: true },
            heatmap: { ...DEFAULT_CONFIG, layout: 'heatmap', chartType: 'heatmap' },
            radar: { ...DEFAULT_CONFIG, layout: 'radar', chartType: 'radar' },
          };
          onConfigChange(presets[preset] || DEFAULT_CONFIG);
        }} />
        
        <button
          onClick={onRefresh}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
          title="Refresh"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
        
        <button
          onClick={onExport}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
          title="Export"
        >
          <Download className="w-5 h-5" />
        </button>
        
        <SettingsDropdown config={config} onChange={onConfigChange} />
      </div>
    </div>
  );
};

// Main analytics dashboard
export const AnalyticsDashboard: React.FC = () => {
  const [config, setConfig] = useState<DashboardConfig>(DEFAULT_CONFIG);
  const [demoData, setDemoData] = useState<Record<string, any[]>>({});
  
  useEffect(() => {
    setDemoData(generateDemoData(['NVDA', 'AAPL', 'SPY', 'TSLA', 'AMD'], 30));
  }, []);
  
  const handleConfigChange = (updates: Partial<DashboardConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  };
  
  const renderLayout = () => {
    switch (config.layout) {
      case 'heatmap':
        return (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(demoData).map(([sym, data]) => (
              <div key={sym} className="bg-gray-800 rounded-lg p-4">
                <div className="text-lg font-bold text-white">{sym}</div>
                <div className="text-2xl font-bold text-emerald-400">
                  ${data[data.length - 1]?.close.toFixed(2)}
                </div>
                <div className="text-sm text-gray-400">
                  {((data[data.length - 1]?.close - data[0]?.close) / data[0]?.close * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        );
      
      case 'list':
        return (
          <div className="space-y-2">
            {Object.entries(demoData).map(([sym, data]) => (
              <div key={sym} className="flex items-center justify-between bg-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-4">
                  <span className="text-lg font-bold text-white w-16">{sym}</span>
                  <span className="text-emerald-400">${data[data.length - 1]?.close.toFixed(2)}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-gray-400">
                    Vol: {(data[data.length - 1]?.volume / 1000000).toFixed(1)}M
                  </span>
                  <span className={data[data.length - 1]?.close >= data[0]?.close ? "text-emerald-400" : "text-red-400"}>
                    {((data[data.length - 1]?.close - data[0]?.close) / data[0]?.close * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        );
      
      case 'radar':
        return (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Radar Chart View</div>
          </div>
        );
      
      default: // grid
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(demoData).map(([sym, data]) => (
              <div key={sym} className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-lg font-bold text-white">{sym}</span>
                  <span className="text-emerald-400">${data[data.length - 1]?.close.toFixed(2)}</span>
                </div>
                <div className="h-24 bg-gray-900 rounded flex items-center justify-center text-gray-500">
                  Chart Area ({config.chartType})
                </div>
              </div>
            ))}
          </div>
        );
    }
  };
  
  return (
    <div className="space-y-4">
      <AnalyticsToolbar
        config={config}
        onConfigChange={handleConfigChange}
        onRefresh={() => setDemoData(generateDemoData(['NVDA', 'AAPL', 'SPY', 'TSLA', 'AMD'], 30))}
        onExport={() => console.log('Export:', demoData)}
      />
      
      {renderLayout()}
    </div>
  );
};

export default AnalyticsDashboard;
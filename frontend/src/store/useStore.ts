import { create } from 'zustand';
import { TickerData, MarketStatus, SystemStats, CorrelationCluster } from '@/types';

interface Breadth {
  bullish: number;
  bearish: number;
  neutral: number;
  bullish_pct: number;
  bearish_pct: number;
  total: number;
}

interface CorrelationState {
  latest: CorrelationCluster | null;
  breadth: Breadth;
  clusters: CorrelationCluster[];
}

interface EdgeStore {
  // Tickers
  tickers: TickerData[];
  setTickers: (tickers: TickerData[]) => void;
  addTicker: (ticker: TickerData) => void;
  removeTicker: (symbol: string) => void;
  updateTicker: (symbol: string, updates: Partial<TickerData>) => void;

  // Markets
  markets: Record<string, MarketStatus>;
  setMarkets: (markets: Record<string, MarketStatus>) => void;

  // System Stats
  stats: SystemStats | null;
  setStats: (stats: SystemStats) => void;

  // UI State
  loading: boolean;
  setLoading: (loading: boolean) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Connection
  connected: boolean;
  setConnected: (connected: boolean) => void;

  // Greek Analysis Toggles (optional analysis)
  greeksEnabled: {
    delta: boolean;    // Delta Direction & Probability
    theta: boolean;  // Theta Time Decay
    vega: boolean; // Vega Volatility Sensitivity
    gamma: boolean; // Gamma Delta Acceleration
    rho: boolean; // Interest rate sensitivity
    gex: boolean; // Gamma Exposure
    vex: boolean; // Vega Exposure
  };
  setGreeksEnabled: (enabled: Partial<EdgeStore['greeksEnabled']>) => void;

  // IV Percentile Tracking
  ivTrackingEnabled: boolean;
  setIVTracking: (enabled: boolean) => void;

  // Volatility Spike Protection
  spikeProtectionEnabled: boolean;
  setSpikeProtection: (enabled: boolean) => void;

  // Short Interest Analysis
  shortInterestEnabled: boolean;
  setShortInterestEnabled: (enabled: boolean) => void;
  shortInterestData: Record<string, unknown>;
  setShortInterestData: (data: Record<string, unknown>) => void;

  // Chart Type Selection (Area, Bar, Line, Candlestick)
  defaultChartType: 'area' | 'bar' | 'line' | 'candlestick' | 'heatmap';
  setDefaultChartType: (type: EdgeStore['defaultChartType']) => void;

  // Dashboard Layout (Grid, List, Heatmap)
  dashboardLayout: 'grid' | 'list' | 'heatmap';
  setDashboardLayout: (layout: EdgeStore['dashboardLayout']) => void;

  // Analytics Cross-Chart Sync
  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;

  // Analytics Preset
  analyticsPreset: 'default' | 'greeks' | 'signals' | 'heatmap' | 'radar';
  setAnalyticsPreset: (preset: EdgeStore['analyticsPreset']) => void;

  // Interactive Chart Settings
  chartCrosshair: boolean;
  setChartCrosshair: (enabled: boolean) => void;
  chartTooltips: boolean;
  setChartTooltips: (enabled: boolean) => void;

  // Auto-Refresh Settings
  autoRefresh: boolean;
  setAutoRefresh: (enabled: boolean) => void;
  refreshInterval: number;
  setRefreshInterval: (interval: number) => void;

  // Correlation alerts (legacy — kept for DecisionFeed backward compat)
  correlationAlerts: CorrelationCluster[];
  setCorrelationAlerts: (alerts: CorrelationCluster[]) => void;
  addCorrelationAlert: (alert: CorrelationCluster) => void;

  // Full correlation state (new)
  correlation: CorrelationState;
  setCorrelation: (state: CorrelationState) => void;
}

export const useStore = create<EdgeStore>((set) => ({
  // Tickers
  tickers: [],
  setTickers: (tickers) => set({ tickers }),
  addTicker: (ticker) =>
    set((state) => ({ tickers: [...state.tickers, ticker] })),
  removeTicker: (symbol) =>
    set((state) => ({ tickers: state.tickers.filter((t) => t.symbol !== symbol) })),
  updateTicker: (symbol, updates) =>
    set((state) => ({
      tickers: state.tickers.map((t) =>
        t.symbol === symbol ? { ...t, ...updates } : t,
      ),
    })),

  // Markets
  markets: {},
  setMarkets: (markets) => set({ markets }),

  // System Stats
  stats: null,
  setStats: (stats) => set({ stats }),

  // UI State
  loading: false,
  setLoading: (loading) => set({ loading }),
  activeTab: 'overview',
  setActiveTab: (activeTab) => set({ activeTab }),

  // Connection
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Greek Analysis Toggles (optional analysis - can exclude unused Greeks for performance)
  greeksEnabled: {
    delta: false,
    theta: false,
    vega: false,
    gamma: false,
    rho: false,    // Interest rate sensitivity
    gex: false,
    vex: false,
  },
  setGreeksEnabled: (enabled) =>
    set((state) => ({
      greeksEnabled: { ...state.greeksEnabled, ...enabled },
    })),

  // IV Percentile Tracking
  ivTrackingEnabled: false,
  setIVTracking: (enabled: boolean) => set({ ivTrackingEnabled: enabled }),

  // Volatility Spike Protection
  spikeProtectionEnabled: true,
  setSpikeProtection: (enabled: boolean) => set({ spikeProtectionEnabled: enabled }),

  // Short Interest Analysis
  shortInterestEnabled: false,
  setShortInterestEnabled: (enabled: boolean) => set({ shortInterestEnabled: enabled }),
  shortInterestData: {},
  setShortInterestData: (data: Record<string, unknown>) => set({ shortInterestData: data }),

  // Chart Type Selection (Area, Bar, Line, Candlestick)
  defaultChartType: 'line' as 'area' | 'bar' | 'line' | 'candlestick' | 'heatmap',
  setDefaultChartType: (type: 'area' | 'bar' | 'line' | 'candlestick' | 'heatmap') => 
    set({ defaultChartType: type }),

  // Dashboard Layout (Grid, List, Heatmap)
  dashboardLayout: 'grid' as 'grid' | 'list' | 'heatmap',
  setDashboardLayout: (layout: 'grid' | 'list' | 'heatmap') => 
    set({ dashboardLayout: layout }),

  // Analytics Cross-Chart Sync
  selectedSymbol: null as string | null,
  setSelectedSymbol: (symbol: string | null) => set({ selectedSymbol: symbol }),
  
  // Analytics Preset
  analyticsPreset: 'default' as 'default' | 'greeks' | 'signals' | 'heatmap' | 'radar',
  setAnalyticsPreset: (preset: 'default' | 'greeks' | 'signals' | 'heatmap' | 'radar') => 
    set({ analyticsPreset: preset }),

  // Interactive Chart Settings
  chartCrosshair: true,
  setChartCrosshair: (enabled: boolean) => set({ chartCrosshair: enabled }),
  chartTooltips: true,
  setChartTooltips: (enabled: boolean) => set({ chartTooltips: enabled }),
  
  // Auto-Refresh Settings
  autoRefresh: true,
  setAutoRefresh: (enabled: boolean) => set({ autoRefresh: enabled }),
  refreshInterval: 5000,
  setRefreshInterval: (interval: number) => set({ refreshInterval: interval }),

  // Correlation alerts (legacy)
  correlationAlerts: [],
  setCorrelationAlerts: (correlationAlerts) => set({ correlationAlerts }),
  addCorrelationAlert: (alert) =>
    set((state) => ({
      correlationAlerts: [alert, ...state.correlationAlerts].slice(0, 20),
    })),

  // Full correlation state
  correlation: {
    latest: null,
    breadth: { bullish: 0, bearish: 0, neutral: 0, bullish_pct: 0, bearish_pct: 0, total: 1 },
    clusters: [],
  },
  setCorrelation: (correlation) => set({ correlation }),
}));

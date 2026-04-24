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

  // Mock mode toggle
  mockMode: boolean;
  setMockMode: (enabled: boolean) => void;

  // Greek Analysis Toggles (optional analysis)
  greeksEnabled: {
    delta: boolean;    // Delta Direction & Probability
    theta: boolean;  // Theta Time Decay
    vega: boolean; // Vega Volatility Sensitivity
    gamma: boolean; // Gamma Delta Acceleration
    gex: boolean; // Gamma Exposure
    vex: boolean; // Vega Exposure
  };
  setGreeksEnabled: (enabled: Partial<EdgeStore['greeksEnabled']>) => void;

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

  // Mock mode
  mockMode: false,
  setMockMode: (mockMode) => set({ mockMode }),

  // Greek Analysis Toggles (optional analysis)
  greeksEnabled: {
    delta: false,
    theta: false,
    vega: false,
    gamma: false,
    gex: false,
    vex: false,
  },
  setGreeksEnabled: (enabled) =>
    set((state) => ({
      greeksEnabled: { ...state.greeksEnabled, ...enabled },
    })),

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

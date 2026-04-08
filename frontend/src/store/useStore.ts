import { create } from 'zustand';
import { TickerData, MarketStatus, SystemStats } from '@/types';

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
}

export const useStore = create<EdgeStore>((set) => ({
  // Tickers
  tickers: [],
  setTickers: (tickers) => set({ tickers }),
  addTicker: (ticker) => set((state) => ({ 
    tickers: [...state.tickers, ticker] 
  })),
  removeTicker: (symbol) => set((state) => ({ 
    tickers: state.tickers.filter(t => t.symbol !== symbol) 
  })),
  updateTicker: (symbol, updates) => set((state) => ({
    tickers: state.tickers.map(t => 
      t.symbol === symbol ? { ...t, ...updates } : t
    )
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
}));

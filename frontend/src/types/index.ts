// API Types
export interface TickerData {
  symbol: string;
  enabled: boolean;
  current_price?: number;
  orb_levels?: {
    '5m'?: OrbLevel;
    '15m'?: OrbLevel;
    '30m'?: OrbLevel;
  };
  signal_strength?: number;
  trend?: string;
  atr?: number;
  volume_ratio?: number;
  last_decision?: string;
  confidence?: number;
  last_updated?: string;
}

export interface OrbLevel {
  high: number;
  low: number;
  locked: boolean;
  range_width: number;
  is_valid: boolean;
}

export interface MarketStatus {
  open: boolean;
  lunch_break: boolean;
  minutes_to_close: number;
}

export interface SystemStats {
  active_tickers: string[];
  running: boolean;
  paused: boolean;
  orb_levels_count: number;
  pulse_circuit_state: string;
  pulse_failures: number;
}

export interface MetricCard {
  title: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
  icon?: string;
}

export interface ChartDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

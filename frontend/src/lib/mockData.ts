/**
 * Mock data service for Sentinel Edge.
 * Used when mockMode is enabled so the dashboard always looks live,
 * even when yfinance is rate-limited or markets are closed.
 */

import type { TickerData } from '../types';

export const MOCK_BASE_PRICES: Record<string, number> = {
  SPY: 592.45,
  QQQ: 512.8,
  NVDA: 142.35,
  AAPL: 237.85,
  TSLA: 312.1,
  MSFT: 415.2,
  AMZN: 198.7,
  META: 578.3,
};

let _mockPrices: Record<string, number> = { ...MOCK_BASE_PRICES };

/** Generate a price that drifts slightly from the previous value */
export function generateMockPrice(symbol: string, volatility = 0.008): number {
  const base = _mockPrices[symbol] || MOCK_BASE_PRICES[symbol] || 100;
  const change = (Math.random() - 0.5) * volatility * base;
  const next = parseFloat((base + change).toFixed(2));
  _mockPrices[symbol] = next;
  return next;
}

/** Build a full TickerData object with simulated values */
export function generateMockTicker(symbol: string): TickerData {
  const price = generateMockPrice(symbol);
  const orbSpread = price * (0.005 + Math.random() * 0.01);
  const orbHigh = parseFloat((price + orbSpread).toFixed(2));
  const orbLow = parseFloat((price - orbSpread).toFixed(2));
  const rawSignal = parseFloat(((Math.random() - 0.4) * 12).toFixed(1));
  const signal = Math.max(-10, Math.min(10, rawSignal));
  const trend = signal >= 2 ? 'bullish' : signal <= -2 ? 'bearish' : 'neutral';

  return {
    symbol,
    enabled: true,
    current_price: price,
    orb_levels: {
      '5m': {
        high: parseFloat((orbHigh * 0.998).toFixed(2)),
        low: parseFloat((orbLow * 1.002).toFixed(2)),
        locked: true,
        range_width: parseFloat((orbSpread * 0.8).toFixed(2)),
        is_valid: true,
      },
      '15m': {
        high: orbHigh,
        low: orbLow,
        locked: true,
        range_width: parseFloat((orbSpread * 2).toFixed(2)),
        is_valid: true,
      },
      '30m': {
        high: parseFloat((orbHigh * 1.002).toFixed(2)),
        low: parseFloat((orbLow * 0.998).toFixed(2)),
        locked: Math.random() > 0.4,
        range_width: parseFloat((orbSpread * 2.5).toFixed(2)),
        is_valid: true,
      },
    },
    signal_strength: signal,
    trend,
    atr: parseFloat((price * 0.012 + Math.random() * price * 0.006).toFixed(2)),
    volume_ratio: parseFloat((0.6 + Math.random() * 2.4).toFixed(2)),
  };
}

/** Generate enriched mock data for all default symbols */
export const DEFAULT_MOCK_SYMBOLS = ['SPY', 'QQQ', 'NVDA', 'AAPL'];

export function generateMockTickerList(symbols: string[] = DEFAULT_MOCK_SYMBOLS): TickerData[] {
  return symbols.map(generateMockTicker);
}

// ── Mock decisions ────────────────────────────────────────────────────

import type { DecisionEntry } from '../types';

const MOCK_DECISION_OPTIONS = [
  'buy', 'stop_buying', 'enable_trailing_stop', 'tighten_trailing_stop', 'emergency_exit',
];

export function generateMockDecision(symbol: string): DecisionEntry {
  const dec = MOCK_DECISION_OPTIONS[Math.floor(Math.random() * MOCK_DECISION_OPTIONS.length)];
  const rawSignal = parseFloat(((Math.random() - 0.4) * 14).toFixed(1));
  const signal = Math.max(-10, Math.min(10, rawSignal));
  return {
    symbol,
    decision: dec,
    signal_strength: signal,
    trend: signal >= 2 ? 'bullish' : signal <= -2 ? 'bearish' : 'neutral',
    confidence: parseFloat(Math.min(Math.abs(signal) / 10, 1).toFixed(2)),
    price: _mockPrices[symbol] || MOCK_BASE_PRICES[symbol] || 100,
    timestamp: new Date().toISOString(),
  };
}

export function generateMockDecisions(
  symbols: string[] = DEFAULT_MOCK_SYMBOLS,
  chancePct = 0.4,
): DecisionEntry[] {
  return symbols
    .filter(() => Math.random() < chancePct)
    .map(generateMockDecision);
}

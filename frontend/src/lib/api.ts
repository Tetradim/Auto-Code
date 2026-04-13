const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

async function fetchJSON<T = any>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

class ApiClient {
  async getHealth() {
    return fetchJSON('/api/health');
  }

  async getStats() {
    return fetchJSON('/api/stats');
  }

  async getTickers() {
    return fetchJSON('/api/tickers');
  }

  async addTicker(symbol: string) {
    return fetchJSON(`/api/tickers/${symbol}`, { method: 'POST' });
  }

  async removeTicker(symbol: string) {
    return fetchJSON(`/api/tickers/${symbol}`, { method: 'DELETE' });
  }

  async updateTickerConfig(symbol: string, config: any) {
    return fetchJSON(`/api/tickers/${symbol}/config`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getTickerConfig(symbol: string) {
    return fetchJSON(`/api/tickers/${symbol}/config`);
  }

  async updatePriceProviders(symbol: string, providers: string[]) {
    return fetchJSON(`/api/tickers/${symbol}/price-providers`, {
      method: 'PUT',
      body: JSON.stringify({ symbol, price_providers: providers }),
    });
  }

  async getOrbLevels(symbol: string) {
    return fetchJSON(`/api/orb/${symbol}`);
  }

  async getMarkets() {
    return fetchJSON('/api/markets');
  }

  async runBacktest(symbol: string, startDate: string, endDate: string, initialCapital?: number) {
    return fetchJSON('/api/backtest', {
      method: 'POST',
      body: JSON.stringify({
        symbol,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital || 10000,
      }),
    });
  }

  async optimizeStrategy(symbol: string, startDate: string, endDate: string, paramGrid: any, initialCapital?: number) {
    return fetchJSON('/api/backtest/optimize', {
      method: 'POST',
      body: JSON.stringify({
        symbol,
        start_date: startDate,
        end_date: endDate,
        param_grid: paramGrid,
        initial_capital: initialCapital || 10000,
      }),
    });
  }

  async getDryRunStatus() {
    return fetchJSON('/api/dry-run/status');
  }

  async pauseScheduler() {
    return fetchJSON('/api/control/pause', { method: 'POST' });
  }

  async resumeScheduler() {
    return fetchJSON('/api/control/resume', { method: 'POST' });
  }

  async toggleKillSwitch(state: boolean) {
    return fetchJSON(`/api/emergency/kill-switch?state=${state}`, { method: 'POST' });
  }

  async getKillSwitchStatus() {
    return fetchJSON('/api/emergency/kill-switch');
  }

  async getCorrelation() {
    return fetchJSON('/api/correlation');
  }

  async getDecisions() {
    return fetchJSON('/api/decisions');
  }
}

export const api = new ApiClient();
export default api;

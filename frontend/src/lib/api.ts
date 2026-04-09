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

  async getOrbLevels(symbol: string) {
    return fetchJSON(`/api/orb/${symbol}`);
  }

  async getMarkets() {
    return fetchJSON('/api/markets');
  }

  async pauseScheduler() {
    return fetchJSON('/api/control/pause', { method: 'POST' });
  }

  async resumeScheduler() {
    return fetchJSON('/api/control/resume', { method: 'POST' });
  }
}

export const api = new ApiClient();
export default api;

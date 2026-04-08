import axios, { AxiosInstance } from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BACKEND_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Health & Status
  async getHealth() {
    const { data } = await this.client.get('/api/health');
    return data;
  }

  async getStats() {
    const { data } = await this.client.get('/api/stats');
    return data;
  }

  // Tickers
  async getTickers() {
    const { data } = await this.client.get('/api/tickers');
    return data;
  }

  async addTicker(symbol: string) {
    const { data } = await this.client.post(`/api/tickers/${symbol}`);
    return data;
  }

  async removeTicker(symbol: string) {
    const { data } = await this.client.delete(`/api/tickers/${symbol}`);
    return data;
  }

  // Ticker Configuration
  async updateTickerConfig(symbol: string, config: any) {
    const { data } = await this.client.put(`/api/tickers/${symbol}/config`, config);
    return data;
  }

  async getTickerConfig(symbol: string) {
    const { data } = await this.client.get(`/api/tickers/${symbol}/config`);
    return data;
  }

  // ORB Data
  async getOrbLevels(symbol: string) {
    const { data } = await this.client.get(`/api/orb/${symbol}`);
    return data;
  }

  // Markets
  async getMarkets() {
    const { data } = await this.client.get('/api/markets');
    return data;
  }

  // Control
  async pauseScheduler() {
    const { data } = await this.client.post('/api/control/pause');
    return data;
  }

  async resumeScheduler() {
    const { data } = await this.client.post('/api/control/resume');
    return data;
  }

  // Metrics (raw Prometheus format)
  async getMetrics() {
    const { data } = await this.client.get('/metrics');
    return data;
  }
}

export const api = new ApiClient();
export default api;

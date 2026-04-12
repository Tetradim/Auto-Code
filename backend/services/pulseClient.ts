export class PulseClient {
  constructor(private pulseUrl: string, private pulseApiKey?: string) {}

  private getHeaders(extra: Record<string, string> = {}) {
    return {
      ...(this.pulseApiKey ? { 'X-API-KEY': this.pulseApiKey } : {}),
      ...extra,
    }
  }

  async fetchTickers() {
    const response = await fetch(`${this.pulseUrl}/api/tickers`, {
      headers: this.getHeaders(),
    })

    if (!response.ok) {
      throw new Error('Failed to fetch tickers from Pulse')
    }

    return await response.json()
  }

  async updateTicker(symbol: string, payload: Record<string, unknown>) {
    const response = await fetch(`${this.pulseUrl}/api/tickers/${symbol}`, {
      method: 'PUT',
      headers: this.getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`Failed to update ticker ${symbol} in Pulse`)
    }

    return await response.json().catch(() => null)
  }
}

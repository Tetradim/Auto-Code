import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PulseClient } from '../pulseClient'

describe('PulseClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches tickers with API key headers', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch' as any).mockResolvedValue({
      ok: true,
      json: async () => [{ symbol: 'SPY', enabled: true }],
    } as any)

    const client = new PulseClient('https://pulse.example.com', 'secret')
    const result = await client.fetchTickers()

    expect(result).toHaveLength(1)
    expect(fetchMock).toHaveBeenCalledWith(
      'https://pulse.example.com/api/tickers',
      expect.objectContaining({ headers: expect.objectContaining({ 'X-API-KEY': 'secret' }) })
    )
  })

  it('throws on non-OK emergency-stop response', async () => {
    vi.spyOn(globalThis, 'fetch' as any).mockResolvedValue({ ok: false } as any)
    const client = new PulseClient('https://pulse.example.com', 'secret')

    await expect(client.emergencyStop({ reason: 'test' })).rejects.toThrow('Failed to trigger Pulse emergency stop')
  })
})

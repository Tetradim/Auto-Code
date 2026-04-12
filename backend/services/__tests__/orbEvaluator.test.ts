import { describe, it, expect, vi } from 'vitest'
import { evaluateTickers } from '../orbEvaluator'

describe('evaluateTickers', () => {
  it('evaluates enabled tickers and triggers breakout side effects', async () => {
    const pulseClient = {
      fetchTickers: vi.fn().mockResolvedValue([
        { symbol: 'SPY', enabled: true },
        { symbol: 'QQQ', enabled: false },
      ]),
      updateTicker: vi.fn().mockResolvedValue({ success: true }),
    }

    const logService = {
      logEvaluation: vi.fn().mockResolvedValue(undefined),
      logBreakout: vi.fn().mockResolvedValue(undefined),
    }

    const blink = {
      db: {
        table: vi.fn().mockReturnValue({
          get: vi.fn().mockResolvedValue({ date: new Date().toISOString().split('T')[0], high: 440 }),
        }),
        breakouts: {
          create: vi.fn().mockResolvedValue(undefined),
        },
      },
    }

    const result = await evaluateTickers({
      blink: blink as any,
      pulseClient: pulseClient as any,
      logService: logService as any,
      autoControl: true,
      userId: 'user-1',
    })

    expect(result.evaluated).toBe(1)
    expect(logService.logEvaluation).toHaveBeenCalledWith('SPY')
    expect(pulseClient.updateTicker).toHaveBeenCalled()
    expect(blink.db.breakouts.create).toHaveBeenCalled()
    expect(logService.logBreakout).toHaveBeenCalledWith('SPY')
  })
})

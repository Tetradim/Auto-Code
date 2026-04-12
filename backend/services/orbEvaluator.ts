import type { BlinkClient, ActiveTicker } from './types'
import { PulseClient } from './pulseClient'
import { LogService } from './logService'

export interface EvaluateOptions {
  blink: BlinkClient
  pulseClient: PulseClient
  logService: LogService
  autoControl: boolean
  userId: string
}

export async function evaluateTickers({
  blink,
  pulseClient,
  logService,
  autoControl,
  userId,
}: EvaluateOptions) {
  const tickers = await pulseClient.fetchTickers()
  const activeTickers: ActiveTicker[] = tickers.filter((t: ActiveTicker) => t.enabled)
  const today = new Date().toISOString().split('T')[0]

  for (const ticker of activeTickers) {
    const symbol = ticker.symbol

    await logService.logEvaluation(symbol)

    const range = await blink.db.table('orb_ranges').get(`${symbol}_15`)

    if (range && range.date === today) {
      const currentPrice = 445.5 // Placeholder; replace with real market feed

      if (currentPrice > range.high && autoControl) {
        await pulseClient.updateTicker(symbol, {
          trailing_enabled: true,
          trailing_percent: 1.5,
          stop_offset: 5.0,
        })

        await blink.db.breakouts.create({
          id: `${symbol}_${Date.now()}`,
          symbol,
          direction: 'UP',
          timeframe: 15,
          price: currentPrice,
          userId,
          date: today,
        })

        await logService.logBreakout(symbol)
      }
    }
  }

  return { evaluated: activeTickers.length }
}

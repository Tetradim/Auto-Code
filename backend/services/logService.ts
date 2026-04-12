import type { BlinkClient } from './types'

export class LogService {
  constructor(private blink: BlinkClient, private userId: string) {}

  async logEvaluation(symbol: string) {
    await this.blink.db.bot_logs.create({
      message: `Evaluating ${symbol} for O.R.B. breakout`,
      level: 'INFO',
      userId: this.userId,
    })
  }

  async logBreakout(symbol: string) {
    await this.blink.db.bot_logs.create({
      message: `SENTINEL EDGE: Breakout UP detected for ${symbol}. Trailing stop enabled.`,
      level: 'WARNING',
      userId: this.userId,
    })
  }

  async logPulseTrade(symbol: string, side: string, price: number, pnl: number) {
    await this.blink.db.bot_logs.create({
      message: `PULSE TRADE: ${side} ${symbol} at ${price} (P&L: ${pnl})`,
      level: 'INFO',
      userId: this.userId,
    })
  }
}

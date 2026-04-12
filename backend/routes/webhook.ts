import type { Hono } from 'hono'
import { LogService } from '../services/logService'

interface WebhookRouteDeps {
  blink: any
}

const DEFAULT_USER_ID = 'kbOom2czwsedIWHkc0KlF2UDGBK2'

export function registerWebhookRoute(app: Hono, { blink }: WebhookRouteDeps) {
  app.post('/pulse/webhook', async (c) => {
    const body = await c.req.json()
    const { symbol, side, price, pnl } = body

    const logService = new LogService(blink, DEFAULT_USER_ID)
    await logService.logPulseTrade(symbol, side, price, pnl)

    return c.json({ success: true })
  })
}

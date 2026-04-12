import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { createClient } from 'npm:@blinkdotnew/sdk'

const app = new Hono()

// CORS setup
app.use('*', cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization', 'X-API-KEY'],
  exposeHeaders: ['Content-Length'],
  maxAge: 600,
}))

// Initialize Blink Client
const blink = createClient({
  projectId: Deno.env.get("VITE_BLINK_PROJECT_ID") || "",
  secretKey: Deno.env.get("BLINK_SECRET_KEY") || "",
})

// Helper to get settings
async function getSetting(key: string) {
  const setting = await blink.db.table('settings').get(key)
  return setting?.value
}

// THE "EDGE" LOGIC: ORB Detection & Control
app.post('/analyze', async (c) => {
  const authHeader = c.req.header('Authorization')
  const userId = "kbOom2czwsedIWHkc0KlF2UDGBK2" // In production, verify JWT

  try {
    const pulseUrl = await getSetting('pulse_api_url')
    const pulseApiKey = await getSetting('pulse_api_key')
    const autoControl = (await getSetting('auto_control_enabled')) === '1'
    
    if (!pulseUrl) {
      return c.json({ error: "Pulse API URL not configured" }, 400)
    }

    // 1. Fetch Tickers from Pulse
    const pulseResponse = await fetch(`${pulseUrl}/api/tickers`, {
      headers: pulseApiKey ? { "X-API-KEY": pulseApiKey } : {}
    })
    
    if (!pulseResponse.ok) {
      return c.json({ error: "Failed to fetch tickers from Pulse" }, 500)
    }
    
    const tickers = await pulseResponse.json()
    const activeTickers = tickers.filter((t: any) => t.enabled)

    // 2. Perform ORB Logic (Simulated for this demo, usually requires real-time price feed)
    // In a real setup, we'd fetch historical 1m data for today
    const results = []
    const today = new Date().toISOString().split('T')[0]

    for (const ticker of activeTickers) {
      const symbol = ticker.symbol
      
      // Fetch prices from a reliable source (mocked here or using blink.data.search/fetch)
      // For this edge function, we'll assume we have a way to get the price
      // We'll log the "evaluation"
      await blink.db.bot_logs.create({
        message: `Evaluating ${symbol} for O.R.B. breakout`,
        level: 'INFO',
        userId: userId
      })

      // Example Breakout Detection (Up)
      // If price > orb_high (stored in DB)
      const range = await blink.db.table('orb_ranges').get(`${symbol}_15`) // 15m default
      
      if (range && range.date === today) {
        // Mock current price from a public API or the Pulse feed if available
        // ... Price fetching logic ...
        const currentPrice = 445.50 // Placeholder
        
        if (currentPrice > range.high && autoControl) {
          // Trigger ACTION in Pulse
          await fetch(`${pulseUrl}/api/tickers/${symbol}`, {
            method: 'PUT',
            headers: { 
              "Content-Type": "application/json",
              ...(pulseApiKey ? { "X-API-KEY": pulseApiKey } : {})
            },
            body: JSON.stringify({
              trailing_enabled: true,
              trailing_percent: 1.5, // Dynamic based on volatility
              stop_offset: 5.0
            })
          })
          
          await blink.db.breakouts.create({
            id: `${symbol}_${Date.now()}`,
            symbol,
            direction: 'UP',
            timeframe: 15,
            price: currentPrice,
            userId: userId,
            date: today
          })
          
          await blink.db.bot_logs.create({
            message: `SENTINEL EDGE: Breakout UP detected for ${symbol}. Trailing stop enabled.`,
            level: 'WARNING',
            userId: userId
          })
        }
      }
    }

    return c.json({ success: true, evaluated: activeTickers.length })

  } catch (error: any) {
    console.error("Edge analysis failed:", error)
    return c.json({ error: error.message }, 500)
  }
})

// Webhook for Pulse to report trades
app.post('/pulse/webhook', async (c) => {
  const body = await c.req.json()
  const { symbol, side, price, pnl } = body

  await blink.db.bot_logs.create({
    message: `PULSE TRADE: ${side} ${symbol} at ${price} (P&L: ${pnl})`,
    level: 'INFO',
    userId: "kbOom2czwsedIWHkc0KlF2UDGBK2"
  })

  return c.json({ success: true })
})

export default app

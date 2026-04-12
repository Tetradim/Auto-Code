import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { createClient } from 'npm:@blinkdotnew/sdk'
import { registerAnalyzeRoute } from './routes/analyze'
import { registerWebhookRoute } from './routes/webhook'
import { registerEmergencyStopRoute } from './routes/emergencyStop'

const app = new Hono()

app.use(
  '*',
  cors({
    origin: '*',
    allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowHeaders: ['Content-Type', 'Authorization', 'X-API-KEY'],
    exposeHeaders: ['Content-Length'],
    maxAge: 600,
  })
)

const blink = createClient({
  projectId: Deno.env.get('VITE_BLINK_PROJECT_ID') || '',
  secretKey: Deno.env.get('BLINK_SECRET_KEY') || '',
})

async function getSetting(key: string) {
  const setting = await blink.db.table('settings').get(key)
  return setting?.value
}

registerAnalyzeRoute(app, { blink, getSetting })
registerWebhookRoute(app, { blink })
registerEmergencyStopRoute(app, { blink, getSetting })

export default app

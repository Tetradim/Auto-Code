import type { Hono } from 'hono'
import { PulseClient } from '../services/pulseClient'
import { LogService } from '../services/logService'

interface EmergencyRouteDeps {
  blink: any
  getSetting: (key: string) => Promise<string | undefined>
}

const DEFAULT_USER_ID = 'kbOom2czwsedIWHkc0KlF2UDGBK2'

export function registerEmergencyStopRoute(app: Hono, { blink, getSetting }: EmergencyRouteDeps) {
  app.post('/pulse/emergency-stop', async (c) => {
    try {
      const requestSecret = c.req.header('X-EDGE-SECRET')
      const expectedSecret = await getSetting('edge_control_secret')

      if (!expectedSecret || requestSecret !== expectedSecret) {
        return c.json({ error: 'Unauthorized emergency stop request' }, 401)
      }

      const pulseUrl = await getSetting('pulse_api_url')
      const pulseApiKey = await getSetting('pulse_api_key')

      if (!pulseUrl) {
        return c.json({ error: 'Pulse API URL not configured' }, 400)
      }

      const body = await c.req.json().catch(() => ({}))
      const requestedBy = body?.requestedBy || DEFAULT_USER_ID
      const reason = body?.reason || 'Manual emergency stop'

      const pulseClient = new PulseClient(pulseUrl, pulseApiKey)
      const logService = new LogService(blink, requestedBy)

      await pulseClient.emergencyStop({ reason, requestedBy })
      await blink.db.table('settings').upsert({ key: 'pulse_engine_status', value: 'stopped' })
      await logService.logPulseTrade('ALL', 'EMERGENCY_STOP', 0, 0)

      return c.json({ success: true, message: 'Emergency stop acknowledged by backend and forwarded to Pulse' })
    } catch (error: any) {
      console.error('Emergency stop failed:', error)
      return c.json({ error: error.message }, 500)
    }
  })
}

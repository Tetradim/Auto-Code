import type { Hono } from 'hono'
import { PulseClient } from '../services/pulseClient'
import { LogService } from '../services/logService'
import { evaluateTickers } from '../services/orbEvaluator'

interface AnalyzeRouteDeps {
  blink: any
  getSetting: (key: string) => Promise<string | undefined>
}

const DEFAULT_USER_ID = 'kbOom2czwsedIWHkc0KlF2UDGBK2'

export function registerAnalyzeRoute(app: Hono, { blink, getSetting }: AnalyzeRouteDeps) {
  app.post('/analyze', async (c) => {
    try {
      const pulseUrl = await getSetting('pulse_api_url')
      const pulseApiKey = await getSetting('pulse_api_key')
      const autoControl = (await getSetting('auto_control_enabled')) === '1'

      if (!pulseUrl) {
        return c.json({ error: 'Pulse API URL not configured' }, 400)
      }

      const pulseClient = new PulseClient(pulseUrl, pulseApiKey)
      const logService = new LogService(blink, DEFAULT_USER_ID)

      const { evaluated } = await evaluateTickers({
        blink,
        pulseClient,
        logService,
        autoControl,
        userId: DEFAULT_USER_ID,
      })

      return c.json({ success: true, evaluated })
    } catch (error: any) {
      console.error('Edge analysis failed:', error)
      return c.json({ error: error.message }, 500)
    }
  })
}

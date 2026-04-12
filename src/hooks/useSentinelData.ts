import { useQuery } from '@tanstack/react-query'
import { blink } from '../lib/blink'

export function useORBRanges() {
  return useQuery({
    queryKey: ['orb_ranges'],
    queryFn: async () => {
      return await blink.db.orb_ranges.list({
        orderBy: { createdAt: 'desc' }
      })
    }
  })
}

export function useBreakouts() {
  return useQuery({
    queryKey: ['breakouts'],
    queryFn: async () => {
      return await blink.db.breakouts.list({
        orderBy: { createdAt: 'desc' },
        limit: 200
      })
    }
  })
}

export function useBreakoutSeries() {
  return useQuery({
    queryKey: ['breakout_series'],
    queryFn: async () => {
      const rows = await blink.db.breakouts.list({
        orderBy: { createdAt: 'asc' },
        limit: 200
      })

      return rows.map((row: any) => ({
        time: new Date(row.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        price: Number(row.price)
      }))
    }
  })
}

export function useBotLogs() {
  return useQuery({
    queryKey: ['bot_logs'],
    queryFn: async () => {
      return await blink.db.bot_logs.list({
        orderBy: { createdAt: 'desc' },
        limit: 100
      })
    }
  })
}

export function usePulseStatus() {
  return useQuery({
    queryKey: ['pulse_status'],
    queryFn: async () => {
      const status = await blink.db.table('settings').get('pulse_engine_status')
      return status?.value || 'stopped'
    }
  })
}

export async function triggerEmergencyStop(userId: string) {
  const pulseUrl = await blink.db.table('settings').get('pulse_api_url')
  const pulseApiKey = await blink.db.table('settings').get('pulse_api_key')
  const edgeSecret = await blink.db.table('settings').get('edge_control_secret')

  if (!pulseUrl?.value) {
    throw new Error('Pulse API URL not configured')
  }

  const edgeApiBase = import.meta.env.VITE_EDGE_API_URL || ''
  const response = await fetch(`${edgeApiBase}/pulse/emergency-stop`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(edgeSecret?.value ? { 'X-EDGE-SECRET': edgeSecret.value } : {}),
      ...(pulseApiKey?.value ? { 'X-API-KEY': pulseApiKey.value } : {})
    },
    body: JSON.stringify({
      requestedBy: userId,
      reason: 'Manual emergency stop from dashboard',
      pulseUrl: pulseUrl.value
    })
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload?.error || 'Failed to execute emergency stop')
  }

  return payload
}

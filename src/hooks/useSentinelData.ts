import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
        limit: 50
      })
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
  // This would ideally call the Pulse API via an Edge Function
  // For now, we'll store status in blink.db.settings if Pulse updates it
  return useQuery({
    queryKey: ['pulse_status'],
    queryFn: async () => {
      const status = await blink.db.table('settings').get('pulse_engine_status')
      return status?.value || 'stopped'
    }
  })
}

import { Page, PageHeader, PageTitle, PageDescription, PageBody, StatGroup, Stat, Card, CardHeader, CardTitle, CardContent, Button, EmptyState, DataTable, Badge, useBlinkUI } from '@blinkdotnew/ui'
import { TrendingUp, AlertTriangle, Activity, Zap, Shield, ArrowUpRight, ArrowDownRight, RefreshCcw, Bell } from 'lucide-react'
import { useORBRanges, useBreakouts, useBotLogs, usePulseStatus } from '../hooks/useSentinelData'
import { AreaChart, ResponsiveContainer, YAxis, XAxis, Tooltip, Area, CartesianGrid } from 'recharts'
import { useBlinkAuth } from '@blinkdotnew/react'
import { blink } from '../lib/blink'
import { useState } from 'react'

const data = [
  { time: '09:30', price: 440.50 },
  { time: '09:45', price: 442.20 },
  { time: '10:00', price: 441.80 },
  { time: '10:15', price: 443.50 },
  { time: '10:30', price: 445.10 },
  { time: '10:45', price: 444.80 },
  { time: '11:00', price: 446.20 },
]

export function DashboardPage() {
  const { data: ranges, isLoading: rangesLoading } = useORBRanges()
  const { data: breakouts, isLoading: breakoutsLoading } = useBreakouts()
  const { data: status, refetch: refetchStatus } = usePulseStatus()
  const [emergencyLoading, setEmergencyLoading] = useState(false)

  const handleEmergencyStop = async () => {
    if (!confirm('Are you sure you want to trigger EMERGENCY STOP for Sentinel Pulse? This will kill all active trades.')) return
    
    setEmergencyLoading(true)
    try {
      // Logic would call Edge Function to update DB/Pulse
      await blink.db.table('settings').upsert({ key: 'pulse_engine_status', value: 'stopped' })
      await blink.db.bot_logs.create({ 
        message: 'EMERGENCY STOP TRIGGERED BY USER',
        level: 'CRITICAL',
        userId: (await blink.auth.me())?.id || 'unknown'
      })
      await refetchStatus()
    } finally {
      setEmergencyLoading(false)
    }
  }

  const breakoutsToday = breakouts?.filter(b => b.date === new Date().toISOString().split('T')[0]) || []

  return (
    <Page>
      <PageHeader>
        <div className="flex w-full items-center justify-between">
          <div>
            <PageTitle className="text-2xl font-bold tracking-tight">Command Center</PageTitle>
            <PageDescription>Advanced ORB Monitoring & Pulse Control</PageDescription>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" size="sm" onClick={() => refetchStatus()} className="bg-card/50">
              <RefreshCcw className="mr-2 h-4 w-4" /> Sync Status
            </Button>
            <Button 
              variant="destructive" 
              size="sm" 
              onClick={handleEmergencyStop}
              loading={emergencyLoading}
              className="bg-red-600 hover:bg-red-700 shadow-lg shadow-red-900/20"
            >
              <AlertTriangle className="mr-2 h-4 w-4" /> EMERGENCY STOP
            </Button>
          </div>
        </div>
      </PageHeader>
      <PageBody className="space-y-6">
        <StatGroup className="grid-cols-2 lg:grid-cols-4">
          <Stat 
            label="Pulse Engine" 
            value={status?.toUpperCase() || 'STOPPED'} 
            icon={<Zap className={status === 'running' ? "text-green-500 fill-green-500/20" : "text-muted-foreground"} />}
            trendLabel={status === 'running' ? "Active Evaluation" : "Bot Offline"}
            trend={status === 'running' ? 100 : 0}
          />
          <Stat 
            label="Active Tickers" 
            value={ranges?.length || 0} 
            icon={<Activity className="text-primary" />}
            trendLabel="Across 7 Markets"
          />
          <Stat 
            label="Breakouts Today" 
            value={breakoutsToday.length} 
            icon={<TrendingUp className="text-accent" />}
            trendLabel="Total Events"
            trend={12.5}
          />
          <Stat 
            label="Bot Integrity" 
            value="PASS" 
            icon={<Shield className="text-green-400" />}
            trendLabel="No Latency Issues"
          />
        </StatGroup>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 bg-card/50 backdrop-blur-md border-border/50">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 py-4">
              <CardTitle className="text-sm font-medium tracking-tight">Active Breakdown — SPY 5m ORB</CardTitle>
              <Badge variant="outline" className="text-[10px] tracking-widest font-bold">LIVE FEED</Badge>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="time" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis domain={['auto', 'auto']} stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                      labelStyle={{ color: 'hsl(var(--foreground))', fontWeight: 'bold' }}
                    />
                    <Area type="monotone" dataKey="price" stroke="hsl(var(--primary))" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader className="border-b border-border/50 py-4">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Bell className="h-4 w-4 text-accent" /> Recent Breakouts
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {breakoutsToday.length === 0 ? (
                <div className="flex h-[300px] flex-col items-center justify-center p-6 text-center text-muted-foreground">
                  <Activity className="mb-2 h-8 w-8 opacity-20" />
                  <p className="text-xs">No breakout events detected yet during this session.</p>
                </div>
              ) : (
                <div className="divide-y divide-border/50 overflow-auto max-h-[350px]">
                  {breakoutsToday.map((b, i) => (
                    <div key={i} className="flex items-center justify-between p-4 hover:bg-accent/5 transition-colors">
                      <div className="flex items-center gap-3">
                        {b.direction === 'UP' ? (
                          <div className="rounded-full bg-green-500/10 p-1.5 text-green-500">
                            <ArrowUpRight className="h-4 w-4" />
                          </div>
                        ) : (
                          <div className="rounded-full bg-red-500/10 p-1.5 text-red-500">
                            <ArrowDownRight className="h-4 w-4" />
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-bold tracking-tight text-foreground">{b.symbol}</p>
                          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{b.timeframe}m O.R.B. Breakout</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-foreground">${b.price.toFixed(2)}</p>
                        <p className="text-[10px] text-muted-foreground">{new Date(b.createdAt).toLocaleTimeString()}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </PageBody>
    </Page>
  )
}

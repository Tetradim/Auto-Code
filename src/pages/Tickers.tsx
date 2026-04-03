import { Page, PageHeader, PageTitle, PageDescription, PageBody, DataTable, Badge, Card, CardHeader, CardTitle, CardContent, Button, EmptyState } from '@blinkdotnew/ui'
import { BarChart3, TrendingUp, TrendingDown, Clock, Activity, Search, RefreshCw } from 'lucide-react'
import { useORBRanges } from '../hooks/useSentinelData'
import { ColumnDef } from '@tanstack/react-table'

type ORBRange = {
  id: string
  symbol: string
  timeframe: number
  high: number
  low: number
  avgVol: number
  date: string
  createdAt: string
}

const columns: ColumnDef<ORBRange>[] = [
  {
    accessorKey: 'symbol',
    header: 'Ticker Symbol',
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="rounded-md bg-primary/10 p-1.5 text-primary">
          <Activity className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-foreground">{row.original.symbol}</p>
          <Badge variant="outline" className="text-[10px] tracking-widest font-bold">{row.original.timeframe}m O.R.B.</Badge>
        </div>
      </div>
    )
  },
  {
    accessorKey: 'high',
    header: 'ORB High',
    cell: ({ row }) => (
      <div className="flex items-center gap-2 text-green-500 font-mono text-sm">
        <TrendingUp className="h-3 w-3" />
        {row.original.high.toFixed(2)}
      </div>
    )
  },
  {
    accessorKey: 'low',
    header: 'ORB Low',
    cell: ({ row }) => (
      <div className="flex items-center gap-2 text-red-500 font-mono text-sm">
        <TrendingDown className="h-3 w-3" />
        {row.original.low.toFixed(2)}
      </div>
    )
  },
  {
    accessorKey: 'range',
    header: 'Range Spread',
    cell: ({ row }) => {
      const spread = row.original.high - row.original.low
      const pct = (spread / row.original.low) * 100
      return (
        <div className="text-sm text-muted-foreground font-mono">
          {spread.toFixed(2)} ({pct.toFixed(2)}%)
        </div>
      )
    }
  },
  {
    accessorKey: 'avgVol',
    header: 'ORB Volume',
    cell: ({ row }) => (
      <div className="text-sm text-muted-foreground font-mono">
        {(row.original.avgVol / 1000).toFixed(1)}k
      </div>
    )
  },
  {
    accessorKey: 'createdAt',
    header: 'Established At',
    cell: ({ row }) => (
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground uppercase tracking-widest">
        <Clock className="h-3 w-3" />
        {new Date(row.original.createdAt).toLocaleTimeString()}
      </div>
    )
  }
]

export function TickersPage() {
  const { data: ranges, isLoading, refetch } = useORBRanges()

  return (
    <Page>
      <PageHeader>
        <div className="flex w-full items-center justify-between">
          <div>
            <PageTitle className="text-2xl font-bold tracking-tight">Ticker Monitoring</PageTitle>
            <PageDescription>Real-time O.R.B. levels and volatility analysis.</PageDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="bg-card/50">
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh Data
          </Button>
        </div>
      </PageHeader>
      <PageBody>
        {!ranges || ranges.length === 0 ? (
          <Card className="flex h-[400px] flex-col items-center justify-center border-border/50 bg-card/50 p-12 text-center backdrop-blur-sm">
            <EmptyState 
              icon={<Search className="h-12 w-12 text-muted-foreground opacity-20" />}
              title="No active ranges detected"
              description="The market might be closed or the bot is still gathering initial session data. Check back during market hours (9:30 AM - 4:00 PM ET)."
            />
          </Card>
        ) : (
          <div className="space-y-6">
            <Card className="border-border/50 bg-card/50 backdrop-blur-md">
              <DataTable 
                columns={columns} 
                data={ranges} 
                searchable 
                searchColumn="symbol" 
                loading={isLoading}
              />
            </Card>
          </div>
        )}
      </PageBody>
    </Page>
  )
}

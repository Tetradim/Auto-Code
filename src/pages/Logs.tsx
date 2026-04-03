import { Page, PageHeader, PageTitle, PageDescription, PageBody, DataTable, Card, Badge, EmptyState } from '@blinkdotnew/ui'
import { Activity, Bell, Shield, AlertTriangle, Clock, History } from 'lucide-react'
import { useBotLogs } from '../hooks/useSentinelData'
import { ColumnDef } from '@tanstack/react-table'

type BotLog = {
  id: string
  message: string
  level: string
  userId: string
  createdAt: string
}

const columns: ColumnDef<BotLog>[] = [
  {
    accessorKey: 'level',
    header: 'Level',
    cell: ({ row }) => (
      <Badge 
        variant={row.original.level === 'CRITICAL' ? 'destructive' : 'secondary'} 
        className="text-[10px] font-bold uppercase tracking-widest"
      >
        {row.original.level}
      </Badge>
    )
  },
  {
    accessorKey: 'message',
    header: 'Event Message',
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="text-sm font-medium text-foreground">{row.original.message}</span>
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{row.original.userId}</span>
      </div>
    )
  },
  {
    accessorKey: 'createdAt',
    header: 'Timestamp',
    cell: ({ row }) => (
      <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
        <Clock className="h-3 w-3" />
        {new Date(row.original.createdAt).toLocaleString()}
      </div>
    )
  }
]

export function LogsPage() {
  const { data: logs, isLoading } = useBotLogs()

  return (
    <Page>
      <PageHeader>
        <PageTitle className="text-2xl font-bold tracking-tight">Audit Trail</PageTitle>
        <PageDescription>Detailed bot event history and user actions.</PageDescription>
      </PageHeader>
      <PageBody>
        {!logs || logs.length === 0 ? (
          <Card className="flex h-[400px] flex-col items-center justify-center border-border/50 bg-card/50 p-12 text-center backdrop-blur-sm">
            <EmptyState 
              icon={<History className="h-12 w-12 text-muted-foreground opacity-20" />}
              title="No events logged"
              description="System audit trail is currently empty. All bot actions will be recorded here in real-time."
            />
          </Card>
        ) : (
          <Card className="border-border/50 bg-card/50 backdrop-blur-md overflow-hidden">
            <DataTable 
              columns={columns} 
              data={logs} 
              loading={isLoading}
            />
          </Card>
        )}
      </PageBody>
    </Page>
  )
}

import { Page, PageHeader, PageTitle, PageDescription, PageBody, Card, CardHeader, CardTitle, CardContent, Button, Input, Field, FieldLabel, FieldDescription, Switch, toast, Banner } from '@blinkdotnew/ui'
import { Shield, Zap, Globe, Link as LinkIcon, Save, RefreshCw, AlertTriangle, Key } from 'lucide-react'
import { useEffect, useState } from 'react'
import { blink } from '../lib/blink'
import { usePulseStatus } from '../hooks/useSentinelData'

export function SettingsPage() {
  const [pulseUrl, setPulseUrl] = useState('')
  const [pulseApiKey, setPulseApiKey] = useState('')
  const [orbMinutes, setOrbMinutes] = useState(15)
  const [autoControl, setAutoControl] = useState(true)
  const [saving, setSaving] = useState(false)
  const { refetch: refetchStatus } = usePulseStatus()

  useEffect(() => {
    async function loadSettings() {
      const url = await blink.db.table('settings').get('pulse_api_url')
      const key = await blink.db.table('settings').get('pulse_api_key')
      const orb = await blink.db.table('settings').get('orb_minutes')
      const auto = await blink.db.table('settings').get('auto_control_enabled')
      
      if (url) setPulseUrl(url.value)
      if (key) setPulseApiKey(key.value)
      if (orb) setOrbMinutes(Number(orb.value))
      if (auto) setAutoControl(auto.value === '1')
    }
    loadSettings()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await blink.db.table('settings').upsertMany([
        { key: 'pulse_api_url', value: pulseUrl },
        { key: 'pulse_api_key', value: pulseApiKey },
        { key: 'orb_minutes', value: String(orbMinutes) },
        { key: 'auto_control_enabled', value: autoControl ? '1' : '0' }
      ])
      toast.success('Configuration saved successfully')
      await refetchStatus()
    } catch (error) {
      toast.error('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Page>
      <PageHeader>
        <PageTitle className="text-2xl font-bold tracking-tight">Configuration</PageTitle>
        <PageDescription>Bridge Sentinel Edge to your Pulse Engine.</PageDescription>
      </PageHeader>
      <PageBody className="max-w-4xl space-y-6">
        <Banner 
          variant="warning" 
          title="Remote Connectivity Required"
          description="Ensure your Sentinel Pulse instance is reachable from the Blink network. Use a public URL or a tunnel (like Cloudflare Tunnel) if running locally."
          className="bg-accent/10 border-accent/20 text-accent-foreground"
          icon={<Globe className="h-5 w-5" />}
        />

        <Card className="border-border/50 bg-card/50 backdrop-blur-md">
          <CardHeader className="border-b border-border/50 py-4">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <LinkIcon className="h-4 w-4 text-primary" /> Integration Bridge
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Field>
                <FieldLabel>Sentinel Pulse API URL</FieldLabel>
                <Input 
                  value={pulseUrl} 
                  onChange={(e) => setPulseUrl(e.target.value)} 
                  placeholder="https://pulse.yourdomain.com"
                  className="bg-background/50"
                />
                <FieldDescription>The base URL of your Sentinel Pulse backend (FastAPI).</FieldDescription>
              </Field>
              <Field>
                <FieldLabel>Pulse API Secret</FieldLabel>
                <div className="relative">
                  <Input 
                    type="password"
                    value={pulseApiKey} 
                    onChange={(e) => setPulseApiKey(e.target.value)} 
                    placeholder="blnk_pk_..."
                    className="bg-background/50 pr-10"
                  />
                  <Key className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground opacity-20" />
                </div>
                <FieldDescription>If your Pulse instance requires authentication.</FieldDescription>
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur-md">
          <CardHeader className="border-b border-border/50 py-4">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Zap className="h-4 w-4 text-accent" /> Edge Ruleset
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="grid gap-6 md:grid-cols-2">
              <Field>
                <FieldLabel>Primary O.R.B. Timeframe</FieldLabel>
                <Input 
                  type="number"
                  value={orbMinutes} 
                  onChange={(e) => setOrbMinutes(Number(e.target.value))} 
                  placeholder="15"
                  className="bg-background/50"
                />
                <FieldDescription>Standard breakout window duration in minutes.</FieldDescription>
              </Field>
              <div className="flex items-center justify-between rounded-lg border border-border/50 bg-background/30 p-4">
                <div className="space-y-0.5">
                  <FieldLabel className="text-sm font-bold">Autonomous Control</FieldLabel>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Enable AI Actions</p>
                </div>
                <Switch 
                  checked={autoControl} 
                  onCheckedChange={setAutoControl}
                  className="data-[state=checked]:bg-primary"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3 pt-4">
          <Button variant="outline" className="bg-card/50" disabled={saving}>
            <RefreshCw className="mr-2 h-4 w-4" /> Reset Changes
          </Button>
          <Button 
            onClick={handleSave} 
            loading={saving}
            className="bg-primary text-primary-foreground shadow-lg shadow-primary/20 px-8"
          >
            <Save className="mr-2 h-4 w-4" /> Update Strategy
          </Button>
        </div>
      </PageBody>
    </Page>
  )
}

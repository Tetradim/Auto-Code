import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  Radio,
  Shield,
  WifiOff,
  XCircle,
} from 'lucide-react';
import { MetricCard } from '../cards/MetricCard';
import { api } from '@/lib/api';

interface ProviderStatus {
  healthy: boolean;
  last_success: string | null;
  error_count: number;
}

interface ProviderInfo {
  key: string;
  label: string;
  configured: boolean;
  requires_key: boolean;
  intraday?: boolean;
  eod?: boolean;
}

interface HealthState {
  connected: boolean;
  loading: boolean;
  error: string | null;
  health: any | null;
  stats: any | null;
  pulse: any | null;
  killSwitch: any | null;
  providers: Record<string, ProviderStatus>;
  providerMeta: ProviderInfo[];
  fallbackOrder: string[];
  decisionsCount: number;
  refreshedAt: string | null;
}

const emptyState: HealthState = {
  connected: false,
  loading: true,
  error: null,
  health: null,
  stats: null,
  pulse: null,
  killSwitch: null,
  providers: {},
  providerMeta: [],
  fallbackOrder: [],
  decisionsCount: 0,
  refreshedAt: null,
};

const formatAge = (iso: string | null) => {
  if (!iso) return 'never';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'unknown';
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m ago`;
};

const statusBadge = (ok: boolean, text: string) => (
  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
    ok ? 'bg-emerald-500/10 text-emerald-300' : 'bg-red-500/10 text-red-300'
  }`}>
    {ok ? <CheckCircle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
    {text}
  </span>
);

export const AdvisorHealth: React.FC = () => {
  const [state, setState] = useState<HealthState>(emptyState);

  const load = async () => {
    try {
      const [health, stats, pulse, killSwitch, providerHealth, providerCatalog, decisions] = await Promise.allSettled([
        api.getHealth(),
        api.getStats(),
        api.getPulseStatus(),
        api.getKillSwitchStatus(),
        api.getProviderHealth(),
        api.getMarketDataProviders(),
        api.getDecisions(),
      ]);

      const next: HealthState = {
        connected: health.status === 'fulfilled',
        loading: false,
        error: null,
        health: health.status === 'fulfilled' ? health.value : null,
        stats: stats.status === 'fulfilled' ? stats.value : null,
        pulse: pulse.status === 'fulfilled' ? pulse.value : null,
        killSwitch: killSwitch.status === 'fulfilled' ? killSwitch.value : null,
        providers: providerHealth.status === 'fulfilled' ? providerHealth.value.providers || {} : {},
        providerMeta: providerCatalog.status === 'fulfilled' ? providerCatalog.value.providers || [] : [],
        fallbackOrder: providerCatalog.status === 'fulfilled' ? providerCatalog.value.fallback_order || [] : [],
        decisionsCount: decisions.status === 'fulfilled' ? decisions.value.count ?? decisions.value.decisions?.length ?? 0 : 0,
        refreshedAt: new Date().toLocaleTimeString(),
      };
      setState(next);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        connected: false,
        error: err instanceof Error ? err.message : 'Unable to load advisor health',
      }));
    }
  };

  useEffect(() => {
    load();
    const id = window.setInterval(load, 10000);
    return () => window.clearInterval(id);
  }, []);

  const activeProviders = useMemo(
    () => state.fallbackOrder.map((key) => state.providerMeta.find((provider) => provider.key === key)?.label || key),
    [state.fallbackOrder, state.providerMeta],
  );

  const providerRows = useMemo(() => {
    const labels = new Map(state.providerMeta.map((provider) => [provider.key, provider]));
    const orderedKeys = Array.from(new Set([...state.fallbackOrder, ...Object.keys(state.providers)]));
    return orderedKeys.map((key) => ({ key, meta: labels.get(key), status: state.providers[key] }));
  }, [state.fallbackOrder, state.providerMeta, state.providers]);

  const pulseConnected = Boolean(state.pulse?.available || state.health?.pulse_available);
  const paused = Boolean(state.health?.paused || state.stats?.paused);
  const running = Boolean(state.health?.running || state.stats?.running);
  const killSwitchActive = Boolean(state.killSwitch?.kill_switch_active);
  const retryQueueSize = state.stats?.retry_queue?.size ?? state.stats?.retry_queue?.pending ?? 0;

  return (
    <div className="space-y-6" data-testid="advisor-health">
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white">Advisor Operations Health</h2>
            <p className="mt-1 text-sm text-gray-400">
              Read-only operational status for Sentinel Edge. Edge generates recommendations; Pulse remains the execution boundary.
            </p>
          </div>
          <div className="text-xs text-gray-500">
            {state.refreshedAt ? `Refreshed ${state.refreshedAt}` : 'Loading…'}
          </div>
        </div>
        {state.error && <p className="mt-3 text-sm text-red-300">{state.error}</p>}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Edge Service"
          value={state.connected ? (running ? 'Running' : 'Stopped') : 'Offline'}
          subtitle={paused ? 'Scheduler paused' : 'Scheduler active'}
          icon={state.connected ? Activity : WifiOff}
          color={state.connected && running ? 'green' : 'red'}
        />
        <MetricCard
          title="Pulse Link"
          value={pulseConnected ? 'Connected' : 'Standalone'}
          subtitle={`Circuit: ${state.pulse?.circuit_state || state.stats?.pulse_circuit_state || 'unknown'}`}
          icon={pulseConnected ? Radio : WifiOff}
          color={pulseConnected ? 'green' : 'yellow'}
        />
        <MetricCard
          title="Kill Switch"
          value={killSwitchActive ? 'Active' : 'Clear'}
          subtitle="Read-only indicator"
          icon={Shield}
          color={killSwitchActive ? 'red' : 'green'}
        />
        <MetricCard
          title="Recommendations"
          value={state.decisionsCount}
          subtitle="Recent advisor decisions"
          icon={CheckCircle}
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50 p-6 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
                <Database className="h-5 w-5 text-emerald-400" />
                Market Data Providers
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Active intraday order: {activeProviders.length > 0 ? activeProviders.join(' → ') : 'none'}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {providerRows.length === 0 && (
              <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-4 text-sm text-gray-500">
                Provider health is not available yet.
              </div>
            )}
            {providerRows.map(({ key, meta, status }) => {
              const active = state.fallbackOrder.includes(key);
              const healthy = status?.healthy ?? false;
              return (
                <div key={key} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-800 bg-gray-900/60 p-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-white">{meta?.label || key}</span>
                      {active && <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-xs text-blue-300">active</span>}
                      {meta?.eod && !meta?.intraday && <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">EOD only</span>}
                      {meta?.requires_key && !meta?.configured && <span className="rounded-full bg-gray-500/10 px-2 py-0.5 text-xs text-gray-400">env key missing</span>}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <span>last success: {formatAge(status?.last_success || null)}</span>
                      <span>errors: {status?.error_count ?? 0}</span>
                    </div>
                  </div>
                  {status ? statusBadge(healthy, healthy ? 'healthy' : 'degraded') : statusBadge(false, 'unseen')}
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50 p-6">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
            <Clock className="h-5 w-5 text-purple-400" />
            Runtime Details
          </h3>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-3 border-b border-gray-800 pb-3">
              <dt className="text-gray-500">Scheduler</dt>
              <dd className="font-medium text-white">{paused ? 'Paused' : running ? 'Active' : 'Stopped'}</dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-gray-800 pb-3">
              <dt className="text-gray-500">Position mode</dt>
              <dd className="font-medium text-white">{state.health?.position_tracking_mode || state.stats?.position_tracking_mode || 'unknown'}</dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-gray-800 pb-3">
              <dt className="text-gray-500">Pulse failures</dt>
              <dd className="font-medium text-white">{state.pulse?.failure_count ?? state.stats?.pulse_failures ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-gray-800 pb-3">
              <dt className="text-gray-500">Retry queue</dt>
              <dd className="font-medium text-white">{retryQueueSize}</dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-gray-800 pb-3">
              <dt className="text-gray-500">ORB levels</dt>
              <dd className="font-medium text-white">{state.stats?.orb_levels_count ?? 0}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-gray-500">Active tickers</dt>
              <dd className="font-medium text-white">{state.health?.active_tickers ?? state.stats?.active_tickers?.length ?? 0}</dd>
            </div>
          </dl>

          {(paused || killSwitchActive || !pulseConnected) && (
            <div className="mt-5 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
              <div className="mb-1 flex items-center gap-2 font-medium">
                <AlertTriangle className="h-4 w-4" />
                Attention
              </div>
              <p className="text-amber-200/80">
                {killSwitchActive
                  ? 'Kill switch is active. Edge should remain advisory-only until cleared by an operator.'
                  : paused
                    ? 'Scheduler is paused. Recommendations may be stale.'
                    : 'Pulse is not connected. Edge is operating standalone and will not hand off actions.'}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

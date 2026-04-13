import { useCallback, useEffect, useMemo, useState } from "react";


import IncidentWindow from "./IncidentWindow";
import RefreshControls from "./RefreshControls";
import ServiceRow from "./ServiceRow";
import type { Signal, RefreshSource, IncidentWindowRect, HealthSummary, VisibleRefreshState } from "./types";


const SERVICES = ["Gateway API", "Auth Service", "Worker Cluster", "Redis Cache", "Webhook Relay"];

const PRESET_INTERVALS = [5, 15, 30, 60];
const MIN_REFRESH_SECONDS = 3;
const MAX_REFRESH_SECONDS = 300;
const MIN_DASHBOARD_SCALE = 85;
const MAX_DASHBOARD_SCALE = 120;
const MIN_TICKER_ROW_SIZE = 40;
const MAX_TICKER_ROW_SIZE = 84;

const DASHBOARD_SCALE_KEY = "sentinel.dashboardScale";
const TICKER_ROW_SIZE_KEY = "sentinel.tickerRowSize";
const AUTO_REFRESH_KEY = "sentinel.autoRefreshEnabled";
const REFRESH_SECONDS_KEY = "sentinel.refreshEverySeconds";
const INCIDENT_WINDOW_RECT_KEY = "sentinel.incidentWindowRect";

const MIN_INCIDENT_WINDOW_WIDTH = 420;
const MIN_INCIDENT_WINDOW_HEIGHT = 280;


function readStoredNumber(key: string, fallback: number): number {
  if (typeof window === "undefined") return fallback;
  const rawValue = window.localStorage.getItem(key);
  if (!rawValue) return fallback;
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) return fallback;
  return parsed;
}


function readStoredBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const rawValue = window.localStorage.getItem(key);
  if (rawValue === null) return fallback;
  return rawValue === "true";
}


function clampValue(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}


function getDefaultIncidentRect(): IncidentWindowRect {
  if (typeof window === "undefined") {
    return { x: 96, y: 80, width: 760, height: 500 };
  }
  const width = Math.min(860, Math.max(MIN_INCIDENT_WINDOW_WIDTH, window.innerWidth * 0.72));
  const height = Math.min(560, Math.max(MIN_INCIDENT_WINDOW_HEIGHT, window.innerHeight * 0.68));
  const x = Math.max(12, (window.innerWidth - width) / 2);
  const y = Math.max(12, (window.innerHeight - height) / 2);
  return { x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) };
}


function clampIncidentRect(rect: IncidentWindowRect): IncidentWindowRect {
  if (typeof window === "undefined") return rect;
  const maxWidth = Math.max(MIN_INCIDENT_WINDOW_WIDTH, window.innerWidth - 24);
  const maxHeight = Math.max(MIN_INCIDENT_WINDOW_HEIGHT, window.innerHeight - 24);
  const width = clampValue(rect.width, MIN_INCIDENT_WINDOW_WIDTH, maxWidth);
  const height = clampValue(rect.height, MIN_INCIDENT_WINDOW_HEIGHT, maxHeight);
  const x = clampValue(rect.x, 12, Math.max(12, window.innerWidth - width - 12));
  const y = clampValue(rect.y, 12, Math.max(12, window.innerHeight - height - 12));
  return { x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) };
}


function readStoredIncidentRect(): IncidentWindowRect {
  const fallback = getDefaultIncidentRect();
  if (typeof window === "undefined") return fallback;
  const rawValue = window.localStorage.getItem(INCIDENT_WINDOW_RECT_KEY);
  if (!rawValue) return fallback;
  try {
    const parsed = JSON.parse(rawValue) as Partial<IncidentWindowRect>;
    if (
      typeof parsed.x !== "number" ||
      typeof parsed.y !== "number" ||
      typeof parsed.width !== "number" ||
      typeof parsed.height !== "number"
    ) {
      return fallback;
    }
    return clampIncidentRect({ x: parsed.x, y: parsed.y, width: parsed.width, height: parsed.height });
  } catch {
    return fallback;
  }
}


function createSignals(): Signal[] {
  return SERVICES.map((service) => {
    const roll = Math.random();
    const status: Signal["status"] = roll > 0.85 ? "critical" : roll > 0.65 ? "warning" : "healthy";
    return {
      id: service,
      service,
      status,
      latencyMs: Math.round(40 + Math.random() * 200),
      eventsPerMinute: Math.round(200 + Math.random() * 1800),
    };
  });
}


export default function HealthDashboard() {
  const [signals, setSignals] = useState<Signal[]>(() => createSignals());
  const [isAutoRefreshEnabled, setIsAutoRefreshEnabled] = useState(() => readStoredBoolean(AUTO_REFRESH_KEY, true));
  const [refreshEverySeconds, setRefreshEverySeconds] = useState(() =>
    clampValue(readStoredNumber(REFRESH_SECONDS_KEY, 15), MIN_REFRESH_SECONDS, MAX_REFRESH_SECONDS),
  );
  const [customSecondsInput, setCustomSecondsInput] = useState("15");
  const [secondsInputError, setSecondsInputError] = useState<string | null>(null);
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(refreshEverySeconds);
  const [lastRefreshAt, setLastRefreshAt] = useState(() => new Date());
  const [lastRefreshSource, setLastRefreshSource] = useState<RefreshSource>("initial");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [changedRows, setChangedRows] = useState<Set<string>>(new Set());
  const [clockNow, setClockNow] = useState(() => Date.now());
  const [dashboardScale, setDashboardScale] = useState(() =>
    clampValue(readStoredNumber(DASHBOARD_SCALE_KEY, 100), MIN_DASHBOARD_SCALE, MAX_DASHBOARD_SCALE),
  );
  const [tickerRowSize, setTickerRowSize] = useState(() =>
    clampValue(readStoredNumber(TICKER_ROW_SIZE_KEY, 56), MIN_TICKER_ROW_SIZE, MAX_TICKER_ROW_SIZE),
  );
  const [isIncidentModalOpen, setIsIncidentModalOpen] = useState(false);
  const [incidentWindowRect, setIncidentWindowRect] = useState<IncidentWindowRect>(() => readStoredIncidentRect());
  const [statusChangedAt, setStatusChangedAt] = useState<Record<string, number>>(() => {
    const now = Date.now();
    return Object.fromEntries(SERVICES.map((service) => [service, now]));
  });

  const refreshNow = useCallback((source: RefreshSource = "manual") => {
    setIsRefreshing(true);
    const incomingSignals = createSignals();
    setSignals((previousSignals) => {
      const changedServices = incomingSignals
        .filter((signal) => {
          const previousSignal = previousSignals.find((item) => item.service === signal.service);
          if (!previousSignal) return true;
          return (
            previousSignal.status !== signal.status ||
            previousSignal.latencyMs !== signal.latencyMs ||
            previousSignal.eventsPerMinute !== signal.eventsPerMinute
          );
        })
        .map((signal) => signal.service);
      setChangedRows(new Set(changedServices));
      setStatusChangedAt((previousMap) => {
        const updatedMap = { ...previousMap };
        incomingSignals.forEach((signal) => {
          const previousSignal = previousSignals.find((item) => item.service === signal.service);
          if (!previousSignal || previousSignal.status !== signal.status) {
            updatedMap[signal.id] = Date.now();
          }
        });
        return updatedMap;
      });
      return incomingSignals;
    });
    setLastRefreshSource(source);
    setLastRefreshAt(new Date());
    setSecondsUntilRefresh(refreshEverySeconds);
    window.setTimeout(() => setIsRefreshing(false), 450);
    window.setTimeout(() => setChangedRows(new Set()), 1300);
  }, [refreshEverySeconds]);

  useEffect(() => {
    const interval = window.setInterval(() => setClockNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => { window.localStorage.setItem(AUTO_REFRESH_KEY, String(isAutoRefreshEnabled)); }, [isAutoRefreshEnabled]);
  useEffect(() => { window.localStorage.setItem(REFRESH_SECONDS_KEY, String(refreshEverySeconds)); }, [refreshEverySeconds]);
  useEffect(() => { window.localStorage.setItem(DASHBOARD_SCALE_KEY, String(dashboardScale)); }, [dashboardScale]);
  useEffect(() => { window.localStorage.setItem(TICKER_ROW_SIZE_KEY, String(tickerRowSize)); }, [tickerRowSize]);
  useEffect(() => { window.localStorage.setItem(INCIDENT_WINDOW_RECT_KEY, JSON.stringify(incidentWindowRect)); }, [incidentWindowRect]);

  useEffect(() => {
    if (!isIncidentModalOpen) return;
    setIncidentWindowRect((prev) => clampIncidentRect(prev));
    const onEscape = (e: KeyboardEvent) => { if (e.key === "Escape") setIsIncidentModalOpen(false); };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [isIncidentModalOpen]);

  useEffect(() => {
    const onResize = () => setIncidentWindowRect((prev) => clampIncidentRect(prev));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    setSecondsUntilRefresh(refreshEverySeconds);
    setCustomSecondsInput(String(refreshEverySeconds));
  }, [refreshEverySeconds]);

  useEffect(() => {
    if (!isAutoRefreshEnabled) return;
    const timer = window.setInterval(() => {
      setSecondsUntilRefresh((prev) => {
        if (prev <= 1) { refreshNow("auto"); return refreshEverySeconds; }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isAutoRefreshEnabled, refreshEverySeconds, refreshNow]);

  const healthSummary: HealthSummary = useMemo(() => ({
    healthyCount: signals.filter((s) => s.status === "healthy").length,
    warningCount: signals.filter((s) => s.status === "warning").length,
    criticalCount: signals.filter((s) => s.status === "critical").length,
  }), [signals]);

  const troubledSignals = useMemo(() => signals.filter((s) => s.status !== "healthy"), [signals]);
  const downSignals = useMemo(() => signals.filter((s) => s.status === "critical"), [signals]);

  const visibleRefreshState: VisibleRefreshState = useMemo(() => {
    if (secondsInputError) {
      return { label: "Timer input invalid", message: `Enter a value between ${MIN_REFRESH_SECONDS}s and ${MAX_REFRESH_SECONDS}s.`, tone: "border-rose-500/60 bg-rose-500/10 text-rose-200" };
    }
    if (!isAutoRefreshEnabled) {
      return { label: "Auto-refresh paused", message: "Only manual refresh is active.", tone: "border-amber-400/50 bg-amber-400/10 text-amber-100" };
    }
    return { label: "Auto-refresh active", message: `Next sync in ${secondsUntilRefresh}s at ${refreshEverySeconds}s cadence.`, tone: "border-emerald-400/50 bg-emerald-400/10 text-emerald-100" };
  }, [isAutoRefreshEnabled, refreshEverySeconds, secondsInputError, secondsUntilRefresh]);

  const applyCustomSeconds = useCallback(() => {
    const parsed = Number(customSecondsInput);
    if (Number.isNaN(parsed) || !Number.isFinite(parsed)) {
      setSecondsInputError(`Use a whole number from ${MIN_REFRESH_SECONDS} to ${MAX_REFRESH_SECONDS}.`);
      return;
    }
    if (parsed < MIN_REFRESH_SECONDS || parsed > MAX_REFRESH_SECONDS) {
      setSecondsInputError(`Seconds must be between ${MIN_REFRESH_SECONDS} and ${MAX_REFRESH_SECONDS}.`);
      return;
    }
    setSecondsInputError(null);
    setRefreshEverySeconds(Math.round(parsed));
  }, [customSecondsInput]);

  const formatSince = useCallback((serviceId: string) => {
    const changedAt = statusChangedAt[serviceId] ?? clockNow;
    const totalSeconds = Math.max(0, Math.floor((clockNow - changedAt) / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const hours = Math.floor(minutes / 60);
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  }, [clockNow, statusChangedAt]);

  const dashboardWidth = `${Math.round((dashboardScale / 100) * 72)}rem`;

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex w-full flex-col gap-8 px-4 py-6 sm:px-6 lg:px-10 lg:py-12" style={{ maxWidth: dashboardWidth }}>
        <header className="space-y-5">
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Sentinel Edge</p>
          <div className="space-y-3">
            <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl">Live edge health with configurable auto-refresh</h1>
            <p className="max-w-2xl text-slate-300">Turn auto-refresh on or off, choose a seconds interval, and watch service health update in real time.</p>
          </div>
        </header>

        <section className="sticky top-0 z-20 -mx-4 border-y border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6 lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1 text-xs text-slate-300">
              <p className="font-semibold text-slate-100">
                {isAutoRefreshEnabled ? `Active · ${secondsUntilRefresh}s` : "Paused · Manual mode"}
              </p>
              <p>H {healthSummary.healthyCount} | W {healthSummary.warningCount} | C {healthSummary.criticalCount}</p>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => refreshNow("manual")} className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-100">Refresh</button>
              <button type="button" onClick={() => setIsIncidentModalOpen(true)} className="rounded-md bg-rose-500 px-3 py-1.5 text-xs font-medium text-slate-950">Incidents {troubledSignals.length}</button>
            </div>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            <div className="mb-1 flex items-center justify-between text-sm text-slate-300">
              <span className="inline-flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                Auto-refresh {isAutoRefreshEnabled ? "active" : "paused"}
              </span>
              <span>{isAutoRefreshEnabled ? `${secondsUntilRefresh}s to next update` : "Manual refresh mode"}</span>
            </div>
            <div className={`h-1.5 overflow-hidden rounded-full ${isAutoRefreshEnabled ? "bg-slate-800" : "bg-amber-950/60"}`}>
              <div
                className={`h-full rounded-full transition-[width,background-color,opacity] duration-1000 ease-linear ${
                  isAutoRefreshEnabled ? "bg-cyan-400 opacity-100" : "bg-amber-400 opacity-60"
                }`}
                style={{ width: isAutoRefreshEnabled ? `${(secondsUntilRefresh / refreshEverySeconds) * 100}%` : "0%" }}
              />
            </div>

            <div className="mt-6 space-y-3">
              <div className="grid grid-cols-[1.15fr_0.65fr_0.75fr_0.7fr] border-b border-slate-800 pb-2 text-xs uppercase tracking-wide text-slate-400">
                <span>Service</span>
                <span>Latency</span>
                <span>Status</span>
                <span>Since change</span>
              </div>
              {signals.map((signal) => (
                <ServiceRow
                  key={signal.id}
                  signal={signal}
                  isChanged={changedRows.has(signal.service)}
                  rowSize={tickerRowSize}
                  formatSince={formatSince}
                />
              ))}
            </div>
          </div>

          <RefreshControls
            isAutoRefreshEnabled={isAutoRefreshEnabled}
            setIsAutoRefreshEnabled={setIsAutoRefreshEnabled}
            refreshEverySeconds={refreshEverySeconds}
            setRefreshEverySeconds={setRefreshEverySeconds}
            secondsUntilRefresh={secondsUntilRefresh}
            customSecondsInput={customSecondsInput}
            setCustomSecondsInput={setCustomSecondsInput}
            secondsInputError={secondsInputError}
            applyCustomSeconds={applyCustomSeconds}
            isRefreshing={isRefreshing}
            refreshNow={refreshNow}
            dashboardScale={dashboardScale}
            setDashboardScale={setDashboardScale}
            tickerRowSize={tickerRowSize}
            setTickerRowSize={setTickerRowSize}
            healthSummary={healthSummary}
            visibleRefreshState={visibleRefreshState}
            lastRefreshAt={lastRefreshAt}
            lastRefreshSource={lastRefreshSource}
            troubledSignalsCount={troubledSignals.length}
            openIncidentWindow={() => setIsIncidentModalOpen(true)}
          />
        </section>
      </div>

      <IncidentWindow
        isOpen={isIncidentModalOpen}
        onClose={() => setIsIncidentModalOpen(false)}
        incidentWindowRect={incidentWindowRect}
        setIncidentWindowRect={setIncidentWindowRect}
        downSignals={downSignals}
        troubledSignals={troubledSignals}
      />
    </main>
  );
}
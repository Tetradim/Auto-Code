import { useMemo } from "react";


interface RefreshControlsProps {
  isAutoRefreshEnabled: boolean;
  setIsAutoRefreshEnabled: (enabled: boolean) => void;
  refreshEverySeconds: number;
  setRefreshEverySeconds: (seconds: number) => void;
  secondsUntilRefresh: number;
  customSecondsInput: string;
  setCustomSecondsInput: (value: string) => void;
  secondsInputError: string | null;
  applyCustomSeconds: () => void;
  isRefreshing: boolean;
  refreshNow: (source: "manual" | "auto") => void;
  dashboardScale: number;
  setDashboardScale: (scale: number) => void;
  tickerRowSize: number;
  setTickerRowSize: (size: number) => void;
  healthSummary: { healthyCount: number; warningCount: number; criticalCount: number };
  visibleRefreshState: { label: string; message: string; tone: string };
  lastRefreshAt: Date;
  lastRefreshSource: "initial" | "manual" | "auto";
  troubledSignalsCount: number;
  openIncidentWindow: () => void;
}


const PRESET_INTERVALS = [5, 15, 30, 60];
const MIN_REFRESH_SECONDS = 3;
const MAX_REFRESH_SECONDS = 300;
const MIN_DASHBOARD_SCALE = 85;
const MAX_DASHBOARD_SCALE = 120;
const MIN_TICKER_ROW_SIZE = 40;
const MAX_TICKER_ROW_SIZE = 84;


function getRefreshSourceLabel(source: "initial" | "manual" | "auto"): string {
  if (source === "manual") return "Manual";
  if (source === "auto") return "Auto timer";
  return "Initial load";
}


export default function RefreshControls({
  isAutoRefreshEnabled,
  setIsAutoRefreshEnabled,
  refreshEverySeconds,
  setRefreshEverySeconds,
  secondsUntilRefresh,
  customSecondsInput,
  setCustomSecondsInput,
  secondsInputError,
  applyCustomSeconds,
  isRefreshing,
  refreshNow,
  dashboardScale,
  setDashboardScale,
  tickerRowSize,
  setTickerRowSize,
  healthSummary,
  visibleRefreshState,
  lastRefreshAt,
  lastRefreshSource,
  troubledSignalsCount,
  openIncidentWindow,
}: RefreshControlsProps) {
  return (
    <aside className="space-y-7 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto">
      <div className="space-y-3">
        <h2 className="font-semibold">Refresh controls</h2>
        <div className={`rounded-xl border px-3 py-2 text-sm ${visibleRefreshState.tone}`}>
          <p className="font-semibold">{visibleRefreshState.label}</p>
          <p className="text-xs opacity-90">{visibleRefreshState.message}</p>
        </div>
        <label className="flex items-center justify-between gap-3 text-sm">
          <span className="text-slate-300">Enable auto-refresh</span>
          <button
            type="button"
            onClick={() => setIsAutoRefreshEnabled((current) => !current)}
            className={`relative inline-flex h-7 w-12 items-center rounded-full transition ${
              isAutoRefreshEnabled ? "bg-cyan-500" : "bg-slate-700"
            }`}
            aria-pressed={isAutoRefreshEnabled}
          >
            <span
              className={`h-5 w-5 rounded-full bg-white transition-transform ${
                isAutoRefreshEnabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </label>

        <label className="space-y-2 text-sm">
          <span className="block text-slate-300">Refresh cadence</span>
          <div className="flex flex-wrap gap-2">
            {PRESET_INTERVALS.map((seconds) => {
              const isActive = refreshEverySeconds === seconds;
              return (
                <button
                  key={seconds}
                  type="button"
                  onClick={() => {
                    setCustomSecondsInput(String(seconds));
                    setRefreshEverySeconds(seconds);
                  }}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    isActive
                      ? "bg-cyan-500 text-slate-950"
                      : "bg-slate-800 text-slate-200 hover:bg-slate-700"
                  }`}
                >
                  {seconds}s
                </button>
              );
            })}
          </div>
          <input
            type="number"
            min={MIN_REFRESH_SECONDS}
            max={MAX_REFRESH_SECONDS}
            value={customSecondsInput}
            onChange={(event) => setCustomSecondsInput(event.target.value)}
            onBlur={applyCustomSeconds}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                applyCustomSeconds();
              }
            }}
            className={`w-full rounded-md border bg-slate-950 px-3 py-2 text-slate-100 outline-none transition ${
              secondsInputError ? "border-rose-500 focus:border-rose-400" : "border-slate-700 focus:border-cyan-400"
            }`}
          />
          <p className={`text-xs ${secondsInputError ? "text-rose-300" : "text-slate-400"}`}>
            {secondsInputError ?? `Enter ${MIN_REFRESH_SECONDS}-${MAX_REFRESH_SECONDS} seconds for custom cadence.`}
          </p>
        </label>

        <button
          type="button"
          onClick={() => refreshNow("manual")}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
        >
          <svg
            className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <path d="M21 3v6h-6" />
          </svg>
          Refresh now
        </button>

        <button
          type="button"
          onClick={openIncidentWindow}
          className="inline-flex w-full items-center justify-between rounded-md border border-rose-400/50 bg-rose-500/10 px-4 py-2 text-sm font-medium text-rose-100"
        >
          Incident window
          <span>{troubledSignalsCount} open</span>
        </button>

        <div className="space-y-3 border-t border-slate-800 pt-5">
          <h3 className="text-sm font-medium text-slate-100">Window sizing</h3>
          <label className="space-y-1 text-xs text-slate-300">
            <span className="block">Dashboard width {dashboardScale}%</span>
            <input
              type="range"
              min={MIN_DASHBOARD_SCALE}
              max={MAX_DASHBOARD_SCALE}
              value={dashboardScale}
              onChange={(event) => setDashboardScale(Number(event.target.value))}
              className="w-full accent-cyan-400"
            />
          </label>
          <label className="space-y-1 text-xs text-slate-300">
            <span className="block">Ticker card size {tickerRowSize}px</span>
            <input
              type="range"
              min={MIN_TICKER_ROW_SIZE}
              max={MAX_TICKER_ROW_SIZE}
              value={tickerRowSize}
              onChange={(event) => setTickerRowSize(Number(event.target.value))}
              className="w-full accent-cyan-400"
            />
          </label>
        </div>
      </div>

      <div className="space-y-2 border-t border-slate-800 pt-5 text-sm">
        <h3 className="font-medium text-slate-100">Snapshot</h3>
        <p className="inline-flex items-center gap-2 text-slate-300">
          <span className="text-emerald-300">✓</span> Healthy: {healthSummary.healthyCount}
        </p>
        <p className="inline-flex items-center gap-2 text-slate-300">
          <span className="text-amber-300">!</span> Warnings: {healthSummary.warningCount}
        </p>
        <p className="inline-flex items-center gap-2 text-slate-300">
          <span className="text-rose-300">x</span> Critical: {healthSummary.criticalCount}
        </p>
        <p className="text-slate-300">Refresh source: {getRefreshSourceLabel(lastRefreshSource)}</p>
        <p className="pt-1 text-xs text-slate-400">Last refresh: {lastRefreshAt.toLocaleTimeString()}</p>
      </div>
    </aside>
  );
}
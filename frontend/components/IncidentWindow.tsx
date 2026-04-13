import type { PointerEvent as ReactPointerEvent } from "react";
import { useCallback } from "react";


type Signal = {
  id: string;
  service: string;
  status: "healthy" | "warning" | "critical";
  latencyMs: number;
  eventsPerMinute: number;
};


type IncidentWindowRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};


type StatusMeta = {
  label: string;
  tone: string;
  icon: string;
};


const statusMeta: Record<Signal["status"], StatusMeta> = {
  healthy: {
    label: "Healthy",
    tone: "text-emerald-300",
    icon: "M20 6 9 17l-5-5",
  },
  warning: {
    label: "Warning",
    tone: "text-amber-300",
    icon: "M12 9v4m0 4h.01M10.29 3.86l-8.18 14a2 2 0 0 0 1.72 3h16.34a2 2 0 0 0 1.72-3l-8.18-14a2 2 0 0 0-3.44 0Z",
  },
  critical: {
    label: "Critical",
    tone: "text-rose-300",
    icon: "m18 6-12 12M6 6l12 12",
  },
};


const MIN_INCIDENT_WINDOW_WIDTH = 420;
const MIN_INCIDENT_WINDOW_HEIGHT = 280;


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
  const clampValue = (val: number, min: number, max: number) => Math.min(max, Math.max(min, val));

  const width = clampValue(rect.width, MIN_INCIDENT_WINDOW_WIDTH, maxWidth);
  const height = clampValue(rect.height, MIN_INCIDENT_WINDOW_HEIGHT, maxHeight);
  const x = clampValue(rect.x, 12, Math.max(12, window.innerWidth - width - 12));
  const y = clampValue(rect.y, 12, Math.max(12, window.innerHeight - height - 12));

  return {
    x: Math.round(x),
    y: Math.round(y),
    width: Math.round(width),
    height: Math.round(height),
  };
}


type WindowInteraction = {
  mode: "drag" | "resize";
  startX: number;
  startY: number;
  startRect: IncidentWindowRect;
} | null;


interface IncidentWindowProps {
  isOpen: boolean;
  onClose: () => void;
  incidentWindowRect: IncidentWindowRect;
  setIncidentWindowRect: (rect: IncidentWindowRect) => void;
  downSignals: Signal[];
  troubledSignals: Signal[];
}


export default function IncidentWindow({
  isOpen,
  onClose,
  incidentWindowRect,
  setIncidentWindowRect,
  downSignals,
  troubledSignals,
}: IncidentWindowProps) {
  const startWindowInteraction = useCallback(
    (mode: "drag" | "resize", event: ReactPointerEvent<HTMLElement>) => {
      if (event.button !== 0) return;
      event.preventDefault();

      const interaction: WindowInteraction = {
        mode,
        startX: event.clientX,
        startY: event.clientY,
        startRect: incidentWindowRect,
      };

      const onPointerMove = (event: PointerEvent) => {
        const deltaX = event.clientX - interaction.startX;
        const deltaY = event.clientY - interaction.startY;

        if (interaction.mode === "drag") {
          setIncidentWindowRect(
            clampIncidentRect({
              ...interaction.startRect,
              x: interaction.startRect.x + deltaX,
              y: interaction.startRect.y + deltaY,
            }),
          );
          return;
        }

        setIncidentWindowRect(
          clampIncidentRect({
            ...interaction.startRect,
            width: interaction.startRect.width + deltaX,
            height: interaction.startRect.height + deltaY,
          }),
        );
      };

      const onPointerUp = () => {
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    },
    [incidentWindowRect, setIncidentWindowRect],
  );

  const resetIncidentWindow = useCallback(() => {
    setIncidentWindowRect(getDefaultIncidentRect());
  }, [setIncidentWindowRect]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-40">
      <button
        type="button"
        onClick={onClose}
        className="absolute inset-0 bg-slate-950/80"
        aria-label="Close incident window"
      />

      <div
        className="absolute flex flex-col overflow-hidden border border-slate-700 bg-slate-900 shadow-2xl"
        style={{
          left: incidentWindowRect.x,
          top: incidentWindowRect.y,
          width: incidentWindowRect.width,
          height: incidentWindowRect.height,
        }}
      >
        <div
          onPointerDown={(event) => startWindowInteraction("drag", event)}
          className="flex cursor-move items-center justify-between gap-4 border-b border-slate-700 bg-slate-800/90 px-4 py-2 select-none"
        >
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-100">Incident window</h2>
              <p className="text-xs text-slate-300">Downed APIs and all trouble signals.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onPointerDown={(event) => event.stopPropagation()}
              onClick={resetIncidentWindow}
              className="rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-200"
            >
              Reset size
            </button>
            <button
              type="button"
              onPointerDown={(event) => event.stopPropagation()}
              onClick={onClose}
              className="rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-100"
            >
              Close
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 text-sm">
          <div className="space-y-5">
            <section className="space-y-2">
              <h3 className="font-medium text-rose-200">Downed APIs ({downSignals.length})</h3>
              {downSignals.length === 0 ? (
                <p className="text-slate-400">No downed APIs right now.</p>
              ) : (
                downSignals.map((signal) => (
                  <div key={`down-${signal.id}`} className="flex items-center justify-between border-b border-slate-800 py-2">
                    <span className="text-slate-200">{signal.service}</span>
                    <span className="text-rose-300">{signal.latencyMs} ms</span>
                  </div>
                ))
              )}
            </section>

            <section className="space-y-2">
              <h3 className="font-medium text-amber-100">All troubles ({troubledSignals.length})</h3>
              {troubledSignals.length === 0 ? (
                <p className="text-slate-400">All services are healthy.</p>
              ) : (
                troubledSignals.map((signal) => (
                  <div key={`trouble-${signal.id}`} className="flex items-center justify-between border-b border-slate-800 py-2">
                    <span className="text-slate-200">{signal.service}</span>
                    <span className={statusMeta[signal.status].tone}>{statusMeta[signal.status].label}</span>
                  </div>
                ))
              )}
            </section>
          </div>
        </div>

        <button
          type="button"
          onPointerDown={(event) => startWindowInteraction("resize", event)}
          className="absolute right-0 bottom-0 h-6 w-6 cursor-se-resize bg-slate-700/60"
          aria-label="Resize incident window"
        >
          <svg viewBox="0 0 24 24" className="h-full w-full p-1 text-slate-200" fill="none" stroke="currentColor" strokeWidth={1.8}>
            <path d="M8 16h8M12 12h4M16 8h0" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
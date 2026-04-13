import type { Signal, StatusMeta } from "./types";


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


interface ServiceRowProps {
  signal: Signal;
  isChanged: boolean;
  rowSize: number;
  formatSince: (serviceId: string) => string;
}


export default function ServiceRow({ signal, isChanged, rowSize, formatSince }: ServiceRowProps) {
  return (
    <div
      className={`grid grid-cols-[1.15fr_0.65fr_0.75fr_0.7fr] items-center border-b text-sm transition-colors duration-700 hover:border-slate-600 ${
        isChanged ? "border-cyan-500/60 bg-cyan-500/10" : "border-slate-800"
      }`}
      style={{ minHeight: `${rowSize}px` }}
    >
      <span className="font-medium text-slate-100">{signal.service}</span>
      <span className="text-slate-300">{signal.latencyMs} ms</span>
      <span className={`inline-flex items-center gap-2 font-medium ${statusMeta[signal.status].tone}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4" aria-hidden>
          <path d={statusMeta[signal.status].icon} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {statusMeta[signal.status].label}
      </span>
      <span className="text-slate-300">{formatSince(signal.id)}</span>
    </div>
  );
}
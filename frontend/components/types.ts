export type Signal = {
  id: string;
  service: string;
  status: "healthy" | "warning" | "critical";
  latencyMs: number;
  eventsPerMinute: number;
};


export type RefreshSource = "initial" | "manual" | "auto";


export type StatusMeta = {
  label: string;
  tone: string;
  icon: string;
};


export type IncidentWindowRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};


export type WindowInteraction = {
  mode: "drag" | "resize";
  startX: number;
  startY: number;
  startRect: IncidentWindowRect;
} | null;


export type HealthSummary = {
  healthyCount: number;
  warningCount: number;
  criticalCount: number;
};


export type VisibleRefreshState = {
  label: string;
  message: string;
  tone: string;
};
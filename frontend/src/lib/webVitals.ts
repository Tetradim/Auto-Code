export type WebVitalRating = 'good' | 'needs-improvement' | 'poor' | 'pending';

export interface WebVitalMetric {
  name: 'INP' | 'LCP' | 'CLS' | 'TTFB' | 'FCP';
  value: number | null;
  unit: 'ms' | 'score';
  rating: WebVitalRating;
  source: string;
}

export interface SlowInteraction {
  target: string;
  type: string;
  duration: number;
  startTime: number;
}

export interface LongTaskEntry {
  duration: number;
  startTime: number;
}

export interface WebVitalsSnapshot {
  route: string;
  collectedAt: string;
  metrics: WebVitalMetric[];
  slowInteractions: SlowInteraction[];
  longTasks: LongTaskEntry[];
  navigation: {
    domContentLoadedMs: number | null;
    loadCompleteMs: number | null;
    transferSize: number | null;
  };
}

type Listener = (snapshot: WebVitalsSnapshot) => void;

interface LayoutShiftEntry extends PerformanceEntry {
  value: number;
  hadRecentInput: boolean;
}

interface LargestContentfulPaintEntry extends PerformanceEntry {
  renderTime: number;
  loadTime: number;
}

interface EventTimingEntry extends PerformanceEntry {
  duration: number;
  interactionId?: number;
  target?: EventTarget | null;
}

const emptySnapshot = (): WebVitalsSnapshot => ({
  route: window.location.pathname || '/',
  collectedAt: new Date().toISOString(),
  metrics: [
    metric('INP', null, 'ms', 'pending', 'Event Timing API'),
    metric('LCP', null, 'ms', 'pending', 'Largest Contentful Paint API'),
    metric('CLS', null, 'score', 'pending', 'Layout Instability API'),
    metric('TTFB', null, 'ms', 'pending', 'Navigation Timing API'),
    metric('FCP', null, 'ms', 'pending', 'Paint Timing API'),
  ],
  slowInteractions: [],
  longTasks: [],
  navigation: {
    domContentLoadedMs: null,
    loadCompleteMs: null,
    transferSize: null,
  },
});

let snapshot = emptySnapshot();
const listeners = new Set<Listener>();
let started = false;

export function startWebVitalsCollection() {
  if (started || typeof window === 'undefined') return;
  started = true;

  collectNavigationTiming();
  observePaintTiming();
  observeLargestContentfulPaint();
  observeCumulativeLayoutShift();
  observeInteractions();
  observeLongTasks();

  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') publish();
  });
}

export function subscribeToWebVitals(listener: Listener) {
  listeners.add(listener);
  listener(snapshot);
  return () => {
    listeners.delete(listener);
  };
}

export function getWebVitalsSnapshot() {
  return snapshot;
}

export function toPrometheusText(data: WebVitalsSnapshot = snapshot) {
  const lines = [
    '# HELP sentinel_edge_frontend_web_vital Browser Web Vital metric collected in the Edge UI.',
    '# TYPE sentinel_edge_frontend_web_vital gauge',
    ...data.metrics
      .filter((item) => item.value !== null)
      .map((item) => `sentinel_edge_frontend_web_vital{route="${escapeLabel(data.route)}",metric="${item.name.toLowerCase()}",rating="${item.rating}"} ${item.value}`),
    '# HELP sentinel_edge_frontend_long_task_duration_ms Long task duration observed in the Edge UI.',
    '# TYPE sentinel_edge_frontend_long_task_duration_ms gauge',
    ...data.longTasks.map((item, index) => `sentinel_edge_frontend_long_task_duration_ms{route="${escapeLabel(data.route)}",rank="${index + 1}"} ${item.duration}`),
    '# HELP sentinel_edge_frontend_slow_interaction_duration_ms Slow interaction duration observed in the Edge UI.',
    '# TYPE sentinel_edge_frontend_slow_interaction_duration_ms gauge',
    ...data.slowInteractions.map(
      (item, index) =>
        `sentinel_edge_frontend_slow_interaction_duration_ms{route="${escapeLabel(data.route)}",type="${escapeLabel(item.type)}",rank="${index + 1}"} ${item.duration}`,
    ),
  ];

  return `${lines.join('\n')}\n`;
}

function metric(
  name: WebVitalMetric['name'],
  value: number | null,
  unit: WebVitalMetric['unit'],
  rating: WebVitalRating,
  source: string,
): WebVitalMetric {
  return { name, value, unit, rating, source };
}

function setMetric(name: WebVitalMetric['name'], value: number | null, unit: WebVitalMetric['unit'], source: string) {
  snapshot = {
    ...snapshot,
    route: window.location.pathname || '/',
    collectedAt: new Date().toISOString(),
    metrics: snapshot.metrics.map((item) =>
      item.name === name ? metric(name, value, unit, rateMetric(name, value), source) : item,
    ),
  };
  publish();
}

function collectNavigationTiming() {
  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
  if (!nav) return;

  const ttfb = Math.max(0, nav.responseStart - nav.requestStart);
  snapshot = {
    ...snapshot,
    collectedAt: new Date().toISOString(),
    navigation: {
      domContentLoadedMs: Math.max(0, nav.domContentLoadedEventEnd - nav.startTime),
      loadCompleteMs: Math.max(0, nav.loadEventEnd - nav.startTime),
      transferSize: nav.transferSize || null,
    },
  };
  setMetric('TTFB', round(ttfb), 'ms', 'Navigation Timing API');
}

function observePaintTiming() {
  for (const entry of performance.getEntriesByType('paint')) {
    if (entry.name === 'first-contentful-paint') {
      setMetric('FCP', round(entry.startTime), 'ms', 'Paint Timing API');
    }
  }

  makeObserver('paint', (entries) => {
    for (const entry of entries.getEntries()) {
      if (entry.name === 'first-contentful-paint') {
        setMetric('FCP', round(entry.startTime), 'ms', 'Paint Timing API');
      }
    }
  });
}

function observeLargestContentfulPaint() {
  makeObserver('largest-contentful-paint', (entries) => {
    const observed = entries.getEntries();
    const last = observed[observed.length - 1] as LargestContentfulPaintEntry | undefined;
    if (!last) return;
    setMetric('LCP', round(last.renderTime || last.loadTime || last.startTime), 'ms', 'Largest Contentful Paint API');
  });
}

function observeCumulativeLayoutShift() {
  let cls = 0;
  makeObserver('layout-shift', (entries) => {
    for (const entry of entries.getEntries() as LayoutShiftEntry[]) {
      if (!entry.hadRecentInput) cls += entry.value;
    }
    setMetric('CLS', round(cls, 3), 'score', 'Layout Instability API');
  });
}

function observeInteractions() {
  const interactions = new Map<number, EventTimingEntry>();
  makeObserver('event', (entries) => {
    for (const entry of entries.getEntries() as EventTimingEntry[]) {
      const duration = Math.max(0, entry.duration || 0);
      const interactionId = entry.interactionId || Math.floor(entry.startTime);
      const previous = interactions.get(interactionId);
      if (!previous || duration > previous.duration) interactions.set(interactionId, entry);
    }

    const slowest = [...interactions.values()].sort((a, b) => b.duration - a.duration).slice(0, 10);
    const inp = slowest[0]?.duration ?? null;

    snapshot = {
      ...snapshot,
      route: window.location.pathname || '/',
      collectedAt: new Date().toISOString(),
      slowInteractions: slowest.map((entry) => ({
        target: describeTarget(entry.target),
        type: entry.name || 'interaction',
        duration: round(entry.duration),
        startTime: round(entry.startTime),
      })),
    };
    setMetric('INP', inp === null ? null : round(inp), 'ms', 'Event Timing API');
  });
}

function observeLongTasks() {
  makeObserver('longtask', (entries) => {
    snapshot = {
      ...snapshot,
      collectedAt: new Date().toISOString(),
      longTasks: [
        ...entries.getEntries().map((entry) => ({
          duration: round(entry.duration),
          startTime: round(entry.startTime),
        })),
        ...snapshot.longTasks,
      ].slice(0, 12),
    };
    publish();
  });
}

function makeObserver(type: string, callback: PerformanceObserverCallback) {
  if (!('PerformanceObserver' in window)) return;
  try {
    const observer = new PerformanceObserver(callback);
    observer.observe({ type, buffered: true });
  } catch {
    // Some browser engines do not support every observed entry type.
  }
}

function rateMetric(name: WebVitalMetric['name'], value: number | null): WebVitalRating {
  if (value === null) return 'pending';
  if (name === 'CLS') {
    if (value <= 0.1) return 'good';
    if (value <= 0.25) return 'needs-improvement';
    return 'poor';
  }
  if (name === 'LCP') {
    if (value <= 2500) return 'good';
    if (value <= 4000) return 'needs-improvement';
    return 'poor';
  }
  if (name === 'INP') {
    if (value <= 200) return 'good';
    if (value <= 500) return 'needs-improvement';
    return 'poor';
  }
  if (name === 'TTFB') {
    if (value <= 800) return 'good';
    if (value <= 1800) return 'needs-improvement';
    return 'poor';
  }
  if (value <= 1800) return 'good';
  if (value <= 3000) return 'needs-improvement';
  return 'poor';
}

function publish() {
  for (const listener of listeners) listener(snapshot);
}

function describeTarget(target?: EventTarget | null) {
  if (!(target instanceof Element)) return 'unknown';
  const tag = target.tagName.toLowerCase();
  const testId = safeTargetToken(target.getAttribute('data-testid'));
  if (testId) return `${tag}[data-testid="${testId}"]`;
  if (target.id) return `${tag}#id`;
  const role = safeTargetToken(target.getAttribute('role'));
  if (role) return `${tag}[role="${role}"]`;
  return tag;
}

function safeTargetToken(value: string | null) {
  const token = value?.trim().replace(/[^A-Za-z0-9_-]+/g, '-').slice(0, 48);
  return token || null;
}

function round(value: number, places = 1) {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

function escapeLabel(value: string) {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

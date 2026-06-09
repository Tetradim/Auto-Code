import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle,
  Gauge,
  Lock,
  Pause,
  Play,
  RefreshCw,
  Save,
  Shield,
  SlidersHorizontal,
  Target,
  Zap,
} from 'lucide-react';
import { AdvisorHealth } from '../dashboards/AdvisorHealth';
import { ExperienceDashboard } from '../dashboards/ExperienceDashboard';
import { MarketCoverage } from '../dashboards/MarketCoverage';
import { PnLTracking } from '../dashboards/PnLTracking';
import { PortfolioAnalytics } from '../dashboards/PortfolioAnalytics';
import { ProtectionDashboard as OperationsProtectionDashboard } from '../dashboards/ProtectionDashboard';
import { SettingsDashboard } from '../dashboards/SettingsDashboard';
import { TradingOverview } from '../dashboards/TradingOverview';
import { TutorialsDashboard, type TutorialModuleView } from '../tutorials';
import { api } from '@/lib/api';
import './AssetCommandConsole.css';

type Mode = 'monitor' | 'command' | 'protect' | 'operations' | 'settings';
type OperationsView = 'overview' | 'advisor' | 'experience' | 'protection' | 'pnl' | 'markets' | 'portfolio' | 'settings' | 'tutorials';
type Tone = 'green' | 'cyan' | 'gold' | 'red';

interface Watcher {
  plugin: string;
  status: string;
  trigger: string;
  source: string;
}

interface Metric {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: Tone;
}

interface Ticker {
  symbol: string;
  change: string;
  status: string;
  signal: string;
  price: number;
  watchers: Watcher[];
  metrics: Metric[];
}

interface EventLine {
  id: string;
  symbol: string;
  title: string;
  detail: string;
  time: string;
}

const money = (value: number) => `$${value.toFixed(2)}`;

const metricMap = (symbol: string, price: number, ids: string[]): Metric[] => {
  const base: Record<string, Metric> = {
    hist: { id: 'hist', label: 'MACD', value: 'Hist', detail: '+0.18', tone: 'gold' },
    vscore: { id: 'vscore', label: 'Vol', value: 'V-score', detail: symbol === 'SPY' ? '71' : '64', tone: 'cyan' },
    emaTop: { id: 'emaTop', label: 'EMA', value: 'EMA top', detail: money(price + 0.7), tone: 'green' },
    emaBottom: { id: 'emaBottom', label: 'EMA', value: 'EMA bottom', detail: money(price - 4.9), tone: 'red' },
    smaTop: { id: 'smaTop', label: 'SMA', value: 'SMA top', detail: money(price + 1.4), tone: 'green' },
    smaBottom: { id: 'smaBottom', label: 'SMA', value: 'SMA bottom', detail: money(price - 6.2), tone: 'red' },
    invalid: { id: 'invalid', label: 'ATR', value: 'Invalid', detail: money(price - 4.2), tone: 'red' },
    momentum: { id: 'momentum', label: 'RSI', value: 'Momentum', detail: symbol === 'NVDA' ? '44' : '62', tone: 'green' },
    liquidity: { id: 'liquidity', label: 'Flow', value: 'Liquidity', detail: '$1.42M', tone: 'cyan' },
    spread: { id: 'spread', label: 'Book', value: 'Spread', detail: '0.04%', tone: 'cyan' },
    drawdown: { id: 'drawdown', label: 'Risk', value: 'Drawdown', detail: '-0.84%', tone: 'red' },
    heat: { id: 'heat', label: 'Risk', value: 'Heat', detail: '46', tone: 'red' },
    atr: { id: 'atr', label: 'ATR', value: 'Vol shelf', detail: '0.72R', tone: 'gold' },
    flow: { id: 'flow', label: 'Flow', value: 'Sweep', detail: '+14', tone: 'cyan' },
    gap: { id: 'gap', label: 'Gap', value: 'Distance', detail: '0.7%', tone: 'gold' },
    volume: { id: 'volume', label: 'Vol', value: 'Rel vol', detail: '1.8x', tone: 'cyan' },
  };
  return ids.map((id) => base[id] || base.momentum);
};

const createTicker = (
  symbol: string,
  change: string,
  status: string,
  watchers: Watcher[],
  price: number,
  metrics: string[],
  signal: string,
): Ticker => ({
  symbol,
  change,
  status,
  watchers,
  price,
  signal,
  metrics: metricMap(symbol, price, metrics),
});

const tickers: Ticker[] = [
  createTicker('MSFT', '+0.42%', 'Pulse idle', [], 414.2, ['smaTop', 'smaBottom', 'liquidity', 'spread', 'drawdown'], 'Bull 58'),
  createTicker('QQQ', '-0.18%', 'Flow watch', [{ plugin: 'FLOW', status: 'watching', trigger: 'sweep', source: 'Sentinel Pulse' }], 472.8, ['flow', 'spread', 'liquidity', 'momentum', 'drawdown'], 'Flat 49'),
  createTicker('AAPL', '+3.52%', 'EMA scan', [{ plugin: 'EMA', status: 'scanning', trigger: 'cross', source: 'Sentinel Pulse' }], 183.42, ['emaTop', 'emaBottom', 'smaTop', 'smaBottom', 'momentum'], 'Bull 71'),
  createTicker('SPY', '+0.50%', 'MACD-V', [{ plugin: 'MACD-V', status: 'armed', trigger: 'compression', source: 'Sentinel Pulse' }], 632.4, ['hist', 'vscore', 'emaTop', 'invalid', 'momentum'], 'Bull 71'),
  createTicker('NVDA', '-1.88%', 'Risk cut', [{ plugin: 'RISK', status: 'armed', trigger: 'heat', source: 'Sentinel Pulse' }], 141.18, ['heat', 'invalid', 'atr', 'drawdown', 'spread'], 'Bear 42'),
  createTicker('TSLA', '+1.12%', 'Pulse idle', [], 219.64, ['momentum', 'smaTop', 'emaTop', 'liquidity', 'spread'], 'Bull 63'),
  createTicker('META', '-0.07%', 'Gap watch', [{ plugin: 'GAP', status: 'watching', trigger: 'open-gap', source: 'Sentinel Pulse' }], 503.72, ['gap', 'flow', 'volume', 'invalid', 'momentum'], 'Flat 52'),
];

const initialEvents: EventLine[] = [
  { id: 'e1', symbol: 'SPY', title: 'MACD-V watcher armed', detail: 'Histogram compression detected', time: '--:--:--' },
  { id: 'e2', symbol: 'AAPL', title: 'EMA scan updated', detail: 'Trend shelf strengthened', time: '--:--:--' },
  { id: 'e3', symbol: 'NVDA', title: 'Risk cut queued', detail: 'Heat corridor narrowed', time: '--:--:--' },
];

const allMetricOptions = Array.from(
  new Map(tickers.flatMap((ticker) => ticker.metrics.map((metric) => [metric.id, { id: metric.id, label: metric.value }]))).values(),
);

const serviceRows = [
  ['Market data feed', 'online', '22ms', '1.8k msg/min'],
  ['Sentinel Pulse bridge', 'online', '18ms', '5 watchers'],
  ['Prediction core', 'online', '31ms', '42 forecasts/min'],
  ['Plugin bus', 'degraded', '44ms', '1 retry/min'],
  ['Event router', 'online', '12ms', '92 events/min'],
];

const protectionRows = [
  { symbol: 'SPY', guard: 'MACD-V / trailing', exposure: '32%', stop: '$628.20', invalid: '$626.80', heat: '38', action: 'tighten into strength', tone: 'green' as Tone },
  { symbol: 'AAPL', guard: 'EMA / protected', exposure: '18%', stop: '$180.10', invalid: '$178.80', heat: '31', action: 'hold corridor', tone: 'green' as Tone },
  { symbol: 'QQQ', guard: 'FLOW / hedged', exposure: '28%', stop: '$468.40', invalid: '$465.90', heat: '44', action: 'watch sweep fade', tone: 'gold' as Tone },
  { symbol: 'NVDA', guard: 'RISK / redline', exposure: '21%', stop: '$137.90', invalid: '$135.80', heat: '69', action: 'reduce if 135.80 breaks', tone: 'red' as Tone },
];

const nowTime = () => new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

const operationsViews: { id: OperationsView; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Trading Overview', icon: Activity },
  { id: 'advisor', label: 'Advisor Health', icon: Gauge },
  { id: 'experience', label: 'Experience', icon: Zap },
  { id: 'protection', label: 'Protection Ops', icon: Shield },
  { id: 'pnl', label: 'P&L Tracking', icon: Target },
  { id: 'markets', label: 'Market Coverage', icon: SlidersHorizontal },
  { id: 'portfolio', label: 'Portfolio', icon: Bell },
  { id: 'settings', label: 'System Settings', icon: Save },
  { id: 'tutorials', label: 'Tutorials', icon: CheckCircle },
];

const modes: Mode[] = ['monitor', 'command', 'protect', 'operations', 'settings'];

const modeLabel = (mode: Mode) => (mode === 'protect' ? 'Protect' : mode === 'operations' ? 'Ops' : mode);

const parseHashState = (): { mode: Mode; operationsView: OperationsView } => {
  if (typeof window === 'undefined') return { mode: 'command', operationsView: 'overview' };
  const raw = window.location.hash.replace('#', '');
  const [modePart, viewPart] = raw.split(':');
  const mode = modes.includes(modePart as Mode) ? (modePart as Mode) : 'command';
  const operationsView = operationsViews.some((item) => item.id === viewPart) ? (viewPart as OperationsView) : 'overview';
  return { mode, operationsView };
};

const writeHashState = (mode: Mode, operationsView = 'overview') => {
  if (typeof window === 'undefined') return;
  const hash = mode === 'operations' ? `#operations:${operationsView}` : `#${mode}`;
  if (window.location.hash !== hash) window.history.replaceState(null, '', hash);
};

export default function AssetCommandConsole() {
  const initialHashState = parseHashState();
  const [mode, setModeState] = useState<Mode>(initialHashState.mode);
  const [operationsView, setOperationsViewState] = useState<OperationsView>(initialHashState.operationsView);
  const [selectedSymbol, setSelectedSymbol] = useState('SPY');
  const [horizon, setHorizon] = useState('30m');
  const [menuOpen, setMenuOpen] = useState(false);
  const [customHorizon, setCustomHorizon] = useState('90m');
  const [visibleReels, setVisibleReels] = useState(5);
  const [selectedMetrics, setSelectedMetrics] = useState(['hist', 'vscore', 'emaTop', 'invalid', 'momentum']);
  const [events, setEvents] = useState<EventLine[]>(() => initialEvents.map((event) => ({ ...event, time: nowTime() })));
  const [clock, setClock] = useState('--:--');
  const [feedPaused, setFeedPaused] = useState(false);
  const [protectionMode, setProtectionMode] = useState('armed');
  const [showPulseStartup, setShowPulseStartup] = useState(true);
  const [runtime, setRuntime] = useState({
    connected: false,
    loading: true,
    pulseAvailable: false,
    killSwitchActive: false,
    schedulerPaused: false,
  });
  const wheelDelta = useRef(0);
  const wheelLocked = useRef(false);

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      const next = parseHashState();
      setModeState(next.mode);
      setOperationsViewState(next.operationsView);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadRuntime = async () => {
      try {
        const [health, pulse, kill] = await Promise.allSettled([
          api.getHealth(),
          api.getPulseStatus(),
          api.getKillSwitchStatus(),
        ]);
        if (cancelled) return;
        const healthValue = health.status === 'fulfilled' ? health.value : null;
        const pulseValue = pulse.status === 'fulfilled' ? pulse.value : null;
        const killValue = kill.status === 'fulfilled' ? kill.value : null;
        setRuntime({
          connected: health.status === 'fulfilled',
          loading: false,
          pulseAvailable: Boolean(pulseValue?.available || healthValue?.pulse_available),
          killSwitchActive: Boolean(killValue?.kill_switch_active),
          schedulerPaused: Boolean(healthValue?.paused),
        });
      } catch {
        if (!cancelled) {
          setRuntime((current) => ({ ...current, connected: false, loading: false, pulseAvailable: false }));
        }
      }
    };
    loadRuntime();
    const id = window.setInterval(loadRuntime, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const selected = tickers.find((ticker) => ticker.symbol === selectedSymbol) || tickers[0];
  const selectedIndex = tickers.findIndex((ticker) => ticker.symbol === selected.symbol);
  const watcher = selected.watchers[0];
  const reels = selected.metrics.filter((metric) => selectedMetrics.includes(metric.id)).slice(0, visibleReels);

  const intelligence = useMemo(() => {
    const pluginBoost = selected.watchers.length ? 18 : 4;
    return {
      move: selected.watchers.some((item) => item.plugin === 'MACD-V') ? '+0.8%' : '+0.4%',
      price: money(selected.price),
      delta: selected.watchers.length ? '+4 pts' : '+1 pt',
      state: selected.watchers.length ? 'strengthening' : 'monitoring',
      pressure: selected.watchers.length ? `${selected.watchers[0].plugin} pressure rising` : 'baseline pressure stable',
      contributors: [
        { label: 'Trend', value: '+22', tone: 'green' as Tone },
        { label: 'Volume', value: '+14', tone: 'cyan' as Tone },
        { label: 'Risk', value: '-6', tone: 'red' as Tone },
        { label: 'Plugin', value: `+${pluginBoost}`, tone: 'gold' as Tone },
      ],
    };
  }, [selected]);

  const addEvent = (symbol: string, title: string, detail: string) => {
    setEvents((current) => [{ id: `${Date.now()}`, symbol, title, detail, time: nowTime() }, ...current].slice(0, 12));
  };

  const selectSymbol = (symbol: string) => {
    const ticker = tickers.find((item) => item.symbol === symbol);
    if (!ticker) return;
    setSelectedSymbol(symbol);
    setSelectedMetrics(ticker.metrics.slice(0, visibleReels).map((metric) => metric.id));
    addEvent(symbol, 'Ticker selected', `${symbol} command state loaded`);
  };

  const movePicker = (direction: number) => {
    const nextIndex = (selectedIndex + direction + tickers.length) % tickers.length;
    selectSymbol(tickers[nextIndex].symbol);
  };

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (wheelLocked.current) return;
    wheelDelta.current += event.deltaY;
    if (Math.abs(wheelDelta.current) < 95) return;
    const direction = wheelDelta.current > 0 ? 1 : -1;
    wheelDelta.current = 0;
    wheelLocked.current = true;
    movePicker(direction);
    window.setTimeout(() => {
      wheelLocked.current = false;
    }, 240);
  };

  const setPrediction = (next: string) => {
    setHorizon(next);
    setMenuOpen(false);
    addEvent(selected.symbol, 'Prediction horizon changed', `Forecast window set to ${next}`);
  };

  const runCommand = (action: string) => {
    const labels: Record<string, string> = {
      arm: 'Arm Trigger',
      backtest: 'Backtest Window',
      alert: 'Convert to Alert',
      mute: 'Mute Watch',
    };
    addEvent(selected.symbol, labels[action] || action, `${selected.status} command acknowledged`);
  };

  const runMonitorAction = (action: string) => {
    if (action === 'toggle-feed') setFeedPaused((value) => !value);
    if (action === 'ack') addEvent('EDGE', 'Monitor alerts acknowledged', '3 alerts cleared');
    if (action === 'diagnostics') addEvent('EDGE', 'Diagnostics completed', 'Plugin bus, Pulse bridge, and prediction core checked');
    if (action === 'refresh') addEvent('EDGE', 'Monitor refreshed', 'Health probes and watcher telemetry updated');
  };

  const runProtectionAction = (action: string) => {
    const labels: Record<string, [string, string]> = {
      refresh: ['Protection refreshed', 'Stops, heat, hedge ratio, and invalidation bands updated'],
      tighten: ['Stops tightened', 'Stops trailed toward current price across protected positions'],
      hedge: ['Hedge staged', 'Coverage raised toward the target corridor'],
      reduce: ['Exposure reduced', 'Highest heat symbol reduced and redline corridor recalculated'],
      clear: ['Protection alerts acknowledged', 'Protection queue cleared'],
    };
    if (action === 'tighten') setProtectionMode('tightened');
    if (action === 'hedge') setProtectionMode('hedged');
    if (action === 'reduce') setProtectionMode('de-risked');
    const [title, detail] = labels[action] || labels.refresh;
    addEvent('PROTECT', title, detail);
  };

  const toggleMetric = (id: string) => {
    setSelectedMetrics((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const pickerItems = Array.from({ length: 7 }, (_, offset) => tickers[(selectedIndex + offset - 3 + tickers.length) % tickers.length]);

  const setMode = (nextMode: Mode) => {
    setModeState(nextMode);
    writeHashState(nextMode, operationsView);
  };

  const handleModeKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, currentMode: Mode) => {
    const currentIndex = modes.indexOf(currentMode);
    const nextMode =
      event.key === 'ArrowRight' ? modes[(currentIndex + 1) % modes.length] :
      event.key === 'ArrowLeft' ? modes[(currentIndex - 1 + modes.length) % modes.length] :
      event.key === 'Home' ? modes[0] :
      event.key === 'End' ? modes[modes.length - 1] :
      null;
    if (!nextMode) return;
    event.preventDefault();
    setMode(nextMode);
    window.requestAnimationFrame(() => document.getElementById(`edge-mode-tab-${nextMode}`)?.focus());
  };

  const setOperationsView = (nextView: OperationsView) => {
    setOperationsViewState(nextView);
    writeHashState('operations', nextView);
  };

  const toggleScheduler = async () => {
    if (runtime.loading || !runtime.connected) return;
    try {
      if (runtime.schedulerPaused) {
        await api.resumeScheduler();
      } else {
        await api.pauseScheduler();
      }
      setRuntime((current) => ({ ...current, schedulerPaused: !current.schedulerPaused }));
      addEvent('EDGE', runtime.schedulerPaused ? 'Scheduler resumed' : 'Scheduler paused', 'Runtime control updated from Asset Command');
    } catch {
      addEvent('EDGE', 'Scheduler control failed', 'Backend control endpoint unavailable');
    }
  };

  return (
    <main className="edge-console" aria-label="Sentinel Edge asset command console">
      <div className="edge-frame" aria-hidden="true" />
      {showPulseStartup && (
        <PulseStartupPanel
          runtime={runtime}
          onConnect={() => setShowPulseStartup(false)}
          onStandalone={() => setShowPulseStartup(false)}
        />
      )}
      <nav className="edge-top-nav">
        <div className="edge-brand">
          <div className="edge-brand-mark" aria-hidden="true" />
          <div>
            Sentinel Edge
            <small>Asset command console</small>
          </div>
        </div>
        <div className="edge-mode-switch" role="tablist" aria-label="Modes">
          {modes.map((item) => (
            <button
              key={item}
              id={`edge-mode-tab-${item}`}
              type="button"
              role="tab"
              aria-selected={mode === item}
              aria-controls={`edge-mode-panel-${item}`}
              className={mode === item ? 'active' : ''}
              onClick={() => setMode(item)}
              onKeyDown={(event) => handleModeKeyDown(event, item)}
            >
              {modeLabel(item)}
            </button>
          ))}
        </div>
        <div className="edge-clock">
          <RuntimeBadges runtime={runtime} onToggleScheduler={toggleScheduler} />
          <div>
            <span>Current time</span>
            <strong>{clock}</strong>
            <span>local / live</span>
          </div>
          <div className="edge-radar" aria-hidden="true" />
        </div>
      </nav>

      <section className="edge-status-strip" aria-label="Portfolio status">
        <div className="edge-primary-metric">Total PBL: <strong>+$12,500.75</strong></div>
        <StatusMetric label="Selected asset" value={selected.symbol} tone="cyan" />
        <StatusMetric label="Prediction horizon" value={horizon} />
        <StatusMetric label="Signal exposure" value="64.8%" tone="gold" />
        <StatusMetric label="Risk corridor" value="2.18R" tone="red" />
      </section>

      <section className="edge-command-grid">
        <aside className="edge-glass edge-events" aria-label="Activity log">
          <PanelTitle eyebrow="Event log" title="Activity" chip={`${events.length} live`} />
          <div className="edge-event-list">
            {events.map((event, index) => (
              <div key={event.id} className={`edge-event ${index === 0 ? 'active' : ''}`}>
                <div><strong>{event.title}</strong>{event.detail}</div>
                <div><span className="edge-gold">{event.symbol}</span><br /><span>{event.time}</span></div>
              </div>
            ))}
          </div>
        </aside>

        <section
          id={`edge-mode-panel-${mode}`}
          className="edge-glass edge-center"
          role="tabpanel"
          aria-label="Asset command center"
        >
          <header className="edge-command-header">
            <div>
              <span>Asset command</span>
              <h1>{selected.symbol}</h1>
            </div>
            <div className="edge-chip">{watcher ? `${watcher.plugin} watcher active` : 'No active watcher'}</div>
          </header>

          {mode === 'command' && (
            <>
              <section className="edge-console-grid">
                <SignalIntelligence intelligence={intelligence} />
                <section className="edge-signal-stack" aria-label="Signal and plugin">
                  <div className="edge-signal-box">
                    <div className="edge-label">Signal</div>
                    <strong>{selected.signal}</strong>
                    <svg viewBox="0 0 120 18" aria-label="Signal confidence history">
                      <path d="M2 15 L14 12 L26 13 L38 9 L50 10 L62 7 L74 8 L86 5 L98 6 L118 3" />
                      <path className="fill" d="M2 15 L14 12 L26 13 L38 9 L50 10 L62 7 L74 8 L86 5 L98 6 L118 3 L118 18 L2 18 Z" />
                    </svg>
                    <span>core alignment</span>
                  </div>
                  <div className={`edge-plugin-box ${watcher ? '' : 'idle'}`}>
                    <div className="edge-label">Plugin watcher</div>
                    <strong>{watcher ? watcher.plugin : 'None'}</strong>
                    <span>{watcher ? `${watcher.source} / ${watcher.status}` : 'Sentinel Pulse / idle'}</span>
                  </div>
                </section>
                <section className="edge-hex-wrap" aria-label="Edge core"><div className="edge-target-core" /></section>
                <section className="edge-prediction" aria-label="Prediction horizon">
                  <button type="button" className="edge-predict-button" aria-expanded={menuOpen} onClick={() => setMenuOpen((value) => !value)}>
                    <span>Predict</span><strong>{horizon}</strong><b>v</b>
                  </button>
                  {menuOpen && (
                    <div className="edge-predict-menu">
                      {['30m', '3h', 'today'].map((item) => <button key={item} type="button" onClick={() => setPrediction(item)}>{item}</button>)}
                      <label>Custom<input value={customHorizon} maxLength={16} onChange={(event) => setCustomHorizon(event.target.value)} /></label>
                      <button type="button" onClick={() => setPrediction(customHorizon || '30m')}>Apply</button>
                    </div>
                  )}
                  <div className="edge-horizon-hint">3h / today / custom</div>
                </section>
              </section>
              <MetricReels reels={reels} source={watcher ? `${watcher.plugin} source` : 'market source'} availableCount={selected.metrics.length} />
            </>
          )}

          {mode === 'monitor' && (
            <MonitorPanel feedPaused={feedPaused} tickers={tickers} onAction={runMonitorAction} onSelect={selectSymbol} />
          )}

          {mode === 'protect' && (
            <ProtectionPanel mode={protectionMode} onAction={runProtectionAction} onSelect={selectSymbol} selectedSymbol={selected.symbol} />
          )}

          {mode === 'operations' && (
            <OperationsPanel activeView={operationsView} setActiveView={setOperationsView} />
          )}

          {mode === 'settings' && (
            <SettingsPanel
              visibleReels={visibleReels}
              setVisibleReels={setVisibleReels}
              selectedMetrics={selectedMetrics}
              toggleMetric={toggleMetric}
              onSave={() => addEvent(selected.symbol, 'Metric reel settings updated', `${visibleReels} reels visible`)}
            />
          )}
        </section>

        <aside className="edge-right-stack">
          <section className="edge-glass edge-picker-panel" aria-label="Kinetic watchlist">
            <PanelTitle eyebrow="Kinetic watchlist" title="Picker" chip="wheel scroll" />
            <div className="edge-ticker-picker" tabIndex={0} onWheel={handleWheel}>
              {pickerItems.map((ticker, index) => {
                const active = ticker.symbol === selected.symbol;
                return (
                  <button
                    type="button"
                    key={`${ticker.symbol}-${index}`}
                    className={`edge-picker-item ${active ? 'active' : ''}`}
                    style={{ opacity: active ? 1 : Math.max(0.16, 0.75 - Math.abs(index - 3) * 0.18) }}
                    onClick={() => selectSymbol(ticker.symbol)}
                  >
                    <b>{ticker.symbol}</b>
                    {ticker.watchers[0] ? <em>{ticker.watchers[0].plugin}</em> : <span>{ticker.status}</span>}
                    <span>{ticker.change}</span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="edge-glass edge-command-panel" aria-label="Plugin commands">
            <PanelTitle eyebrow={watcher ? `${watcher.plugin} command panel` : 'Command panel'} title={selected.symbol} />
            <div className="edge-command-buttons">
              <button type="button" onClick={() => runCommand('arm')}>Arm Trigger</button>
              <button type="button" onClick={() => runCommand('backtest')}>Backtest</button>
              <button type="button" onClick={() => runCommand('alert')}>Convert Alert</button>
              <button type="button" onClick={() => runCommand('mute')}>Mute Watch</button>
            </div>
            <div className="edge-plugin-watch">
              <div>Status <strong>{watcher ? watcher.status : 'idle'}</strong></div>
              <div>Trigger <strong>{watcher ? watcher.trigger : 'none'}</strong></div>
              <div>Source <strong>{watcher ? watcher.source : 'Sentinel Pulse'}</strong></div>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}

function PulseStartupPanel({
  runtime,
  onConnect,
  onStandalone,
}: {
  runtime: { connected: boolean; loading: boolean; pulseAvailable: boolean };
  onConnect: () => void;
  onStandalone: () => void;
}) {
  return (
    <section className="edge-pulse-startup edge-glass" aria-label="Sentinel Pulse startup choice">
      <div>
        <span>Sentinel Pulse</span>
        <strong>{runtime.pulseAvailable ? 'Execution bridge detected' : runtime.loading ? 'Checking execution bridge' : 'Execution bridge unavailable'}</strong>
        <p>{runtime.pulseAvailable ? 'Connect Edge to Pulse for order execution and live position updates.' : 'Run Edge standalone while Pulse is unavailable; decisions stay visible without order handoff.'}</p>
      </div>
      <div className="edge-pulse-actions">
        <button type="button" onClick={onConnect}>
          {runtime.pulseAvailable ? 'Connect to Pulse' : 'Try Connecting'}
        </button>
        <button type="button" onClick={onStandalone}>Standalone Mode</button>
      </div>
    </section>
  );
}

function RuntimeBadges({ runtime, onToggleScheduler }: { runtime: { connected: boolean; loading: boolean; pulseAvailable: boolean; killSwitchActive: boolean; schedulerPaused: boolean }; onToggleScheduler: () => void }) {
  return (
    <div className="edge-runtime-badges" aria-label="Runtime status">
      <button
        type="button"
        className={`edge-runtime-pill ${runtime.schedulerPaused ? 'warn' : 'ok'}`}
        disabled={runtime.loading || !runtime.connected}
        aria-disabled={runtime.loading || !runtime.connected}
        onClick={onToggleScheduler}
      >
        {runtime.schedulerPaused ? <Play size={14} /> : <Pause size={14} />}
        {runtime.schedulerPaused ? 'Resume' : 'Pause'}
      </button>
      <span className={`edge-runtime-pill ${runtime.killSwitchActive ? 'danger' : 'muted'}`}>
        <AlertTriangle size={14} />
        {runtime.killSwitchActive ? 'Kill Active' : 'Kill Clear'}
      </span>
      <span className={`edge-runtime-pill ${runtime.pulseAvailable ? 'ok' : 'warn'}`}>
        <Shield size={14} />
        {runtime.pulseAvailable ? 'Pulse' : 'No Pulse'}
      </span>
      <span className={`edge-runtime-pill ${runtime.connected ? 'ok' : 'danger'}`}>
        {runtime.connected ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
        {runtime.loading ? 'Connecting' : runtime.connected ? 'Connected' : 'Disconnected'}
      </span>
    </div>
  );
}

function StatusMetric({ label, value, tone }: { label: string; value: string; tone?: Tone }) {
  return <div className="edge-status-metric"><span>{label}</span><strong className={tone ? `edge-${tone}` : ''}>{value}</strong></div>;
}

function PanelTitle({ eyebrow, title, chip }: { eyebrow: string; title: string; chip?: string }) {
  return (
    <div className="edge-panel-title">
      <div><span>{eyebrow}</span><h2>{title}</h2></div>
      {chip && <div className="edge-chip">{chip}</div>}
    </div>
  );
}

function SignalIntelligence({ intelligence }: { intelligence: ReturnType<typeof AssetCommandConsole> extends never ? never : any }) {
  return (
    <section className="edge-intel-card" aria-label="Signal intelligence">
      <div className="edge-label">Signal intelligence</div>
      <div className="edge-intel-grid">
        <div><span>Move</span><strong>{intelligence.move}</strong></div>
        <div><span>Price</span><strong>{intelligence.price}</strong></div>
        <div><span>Delta</span><strong>{intelligence.delta}</strong></div>
        <div><span>State</span><strong>{intelligence.state}</strong></div>
      </div>
      <div className="edge-intel-note">last 12 candles / {intelligence.pressure}</div>
      <div className="edge-contributors">
        {intelligence.contributors.map((item: { label: string; value: string; tone: Tone }) => (
          <span key={item.label} className={`edge-contributor edge-tone-${item.tone}`}>{item.label} {item.value}</span>
        ))}
      </div>
    </section>
  );
}

function MetricReels({ reels, source, availableCount }: { reels: Metric[]; source: string; availableCount: number }) {
  return (
    <section className="edge-reels-panel" aria-label="Metric reels">
      <div className="edge-reel-header">
        <span>Slot metric reels</span>
        <div><span>{source}</span><span>{reels.length} of {availableCount} visible</span></div>
      </div>
      <div className="edge-reels" tabIndex={0} aria-label="Scrollable metric reel slots">
        {reels.map((metric) => (
          <div key={metric.id} className="edge-reel">
            <div>
              <span>{metric.label}</span>
              <strong className={`edge-tone-${metric.tone}`}>{metric.value}<br />{metric.detail}</strong>
              <span>{metric.id}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MonitorPanel({ feedPaused, tickers, onAction, onSelect }: { feedPaused: boolean; tickers: Ticker[]; onAction: (action: string) => void; onSelect: (symbol: string) => void }) {
  return (
    <section className="edge-tab-panel">
      <div className="edge-tab-head">
        <div><span>Monitor</span><h2>Edge observability</h2></div>
        <div className="edge-tab-actions">
          <button type="button" onClick={() => onAction('refresh')}><RefreshCw size={14} />Refresh</button>
          <button type="button" onClick={() => onAction('diagnostics')}><Gauge size={14} />Diagnostics</button>
          <button type="button" onClick={() => onAction('ack')}><CheckCircle size={14} />Ack alerts</button>
          <button type="button" onClick={() => onAction('toggle-feed')}>{feedPaused ? <Play size={14} /> : <Pause size={14} />}{feedPaused ? 'Resume feed' : 'Pause feed'}</button>
        </div>
      </div>
      <div className="edge-card-grid">
        <HealthCard label="Sentinel Pulse" value={feedPaused ? 'Paused' : 'Synced'} detail="7 tickers / 5 watchers" tone={feedPaused ? 'gold' : 'green'} />
        <HealthCard label="Prediction Engine" value="18ms" detail="p95 inference latency" tone="cyan" />
        <HealthCard label="Plugin Bus" value="5 active" detail="MACD-V, EMA, FLOW, RISK, GAP" tone="gold" />
        <HealthCard label="Alert Queue" value="3 open" detail="1 high priority" tone="red" />
      </div>
      <div className="edge-section-grid">
        <section className="edge-tab-section wide"><SectionHead label="Services" value="ops telemetry" />{serviceRows.map((row) => <ServiceRow key={row[0]} row={row} />)}</section>
        <section className="edge-tab-section"><SectionHead label="Watcher coverage" value="Sentinel Pulse" /><div className="edge-watcher-map">{tickers.map((ticker) => <button type="button" key={ticker.symbol} onClick={() => onSelect(ticker.symbol)}><strong>{ticker.symbol}</strong><em>{ticker.watchers[0] ? `${ticker.watchers[0].plugin} / ${ticker.watchers[0].status}` : 'Pulse idle'}</em></button>)}</div></section>
      </div>
    </section>
  );
}

function ProtectionPanel({ mode, onAction, onSelect, selectedSymbol }: { mode: string; onAction: (action: string) => void; onSelect: (symbol: string) => void; selectedSymbol: string }) {
  return (
    <section className="edge-tab-panel edge-protect-panel">
      <div className="edge-tab-head">
        <div><span>Protect</span><h2>Risk shield</h2></div>
        <div className="edge-tab-actions">
          <button type="button" onClick={() => onAction('refresh')}><RefreshCw size={14} />Refresh</button>
          <button type="button" onClick={() => onAction('tighten')}><Lock size={14} />Tighten stops</button>
          <button type="button" onClick={() => onAction('hedge')}><Shield size={14} />Stage hedge</button>
          <button type="button" onClick={() => onAction('reduce')}><AlertTriangle size={14} />Reduce exposure</button>
        </div>
      </div>
      <div className="edge-protect-overview">
        <div><span>Protection mode</span><strong>{mode}</strong></div>
        <div><span>Last update</span><strong>{nowTime()}</strong></div>
      </div>
      <div className="edge-card-grid">
        <HealthCard label="Portfolio heat" value="46/100" detail="inside protection band" tone="gold" />
        <HealthCard label="Stop discipline" value="100%" detail="4 stops / 4 positions protected" tone="green" />
        <HealthCard label="Hedge coverage" value="34%" detail="coverage below target" tone="cyan" />
        <HealthCard label="Breach risk" value="1 active" detail="SPY invalidates at $626.80" tone="red" />
      </div>
      <section className="edge-tab-section">
        <SectionHead label="Position risk" value="stops / invalidation / exposure" />
        <div className="edge-risk-table">
          {protectionRows.map((row) => (
            <button type="button" key={row.symbol} className={`edge-risk-row edge-tone-${row.tone} ${selectedSymbol === row.symbol ? 'active' : ''}`} onClick={() => onSelect(row.symbol)}>
              <div><strong>{row.symbol}</strong><span>{row.guard}</span></div>
              <div><span>Exposure</span><b>{row.exposure}</b></div>
              <div><span>Stop</span><b>{row.stop}</b></div>
              <div><span>Invalid</span><b>{row.invalid}</b></div>
              <div><span>Heat</span><b>{row.heat}</b></div>
              <em>{row.action}</em>
            </button>
          ))}
        </div>
      </section>
    </section>
  );
}

function OperationsPanel({ activeView, setActiveView }: { activeView: OperationsView; setActiveView: (view: OperationsView) => void }) {
  const handleOperationsKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, currentView: OperationsView) => {
    const viewIds = operationsViews.map((item) => item.id);
    const currentIndex = viewIds.indexOf(currentView);
    const nextView =
      event.key === 'ArrowDown' || event.key === 'ArrowRight' ? viewIds[(currentIndex + 1) % viewIds.length] :
      event.key === 'ArrowUp' || event.key === 'ArrowLeft' ? viewIds[(currentIndex - 1 + viewIds.length) % viewIds.length] :
      event.key === 'Home' ? viewIds[0] :
      event.key === 'End' ? viewIds[viewIds.length - 1] :
      null;
    if (!nextView) return;
    event.preventDefault();
    setActiveView(nextView);
    window.requestAnimationFrame(() => document.getElementById(`edge-ops-tab-${nextView}`)?.focus());
  };

  return (
    <section className="edge-tab-panel edge-ops-panel" aria-label="Operations deck">
      <div className="edge-tab-head">
        <div>
          <span>Operations</span>
          <h2>Legacy feature deck</h2>
        </div>
        <div className="edge-chip">all old UI modules</div>
      </div>
      <div className="edge-ops-layout">
        <nav className="edge-ops-nav" role="tablist" aria-label="Operations modules">
          {operationsViews.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`edge-ops-tab-${id}`}
              type="button"
              role="tab"
              aria-selected={activeView === id}
              aria-controls={`edge-ops-panel-${id}`}
              className={activeView === id ? 'active' : ''}
              onClick={() => setActiveView(id)}
              onKeyDown={(event) => handleOperationsKeyDown(event, id)}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
        </nav>
        <div
          id={`edge-ops-panel-${activeView}`}
          className="edge-ops-content"
          role="tabpanel"
          aria-labelledby={`edge-ops-tab-${activeView}`}
        >
          {activeView === 'overview' && <TradingOverview />}
          {activeView === 'advisor' && <AdvisorHealth />}
          {activeView === 'experience' && <ExperienceDashboard />}
          {activeView === 'protection' && <OperationsProtectionDashboard />}
          {activeView === 'pnl' && <PnLTracking />}
          {activeView === 'markets' && <MarketCoverage />}
          {activeView === 'portfolio' && <PortfolioAnalytics />}
          {activeView === 'settings' && <SettingsDashboard />}
          {activeView === 'tutorials' && <TutorialsDashboard onOpenModule={(view: TutorialModuleView) => setActiveView(view)} />}
        </div>
      </div>
    </section>
  );
}

function SettingsPanel({ visibleReels, setVisibleReels, selectedMetrics, toggleMetric, onSave }: { visibleReels: number; setVisibleReels: (value: number) => void; selectedMetrics: string[]; toggleMetric: (id: string) => void; onSave: () => void }) {
  return (
    <section className="edge-tab-panel edge-settings-panel">
      <div className="edge-tab-head"><div><span>Settings</span><h2>Metric reels</h2></div></div>
      <div className="edge-settings-grid">
        <label>Visible reels<input type="number" min={1} max={8} value={visibleReels} onChange={(event) => setVisibleReels(Math.max(1, Math.min(8, Number(event.target.value))))} /></label>
        <div className="edge-metric-options">{allMetricOptions.map((metric) => <label key={metric.id}><input type="checkbox" checked={selectedMetrics.includes(metric.id)} onChange={() => toggleMetric(metric.id)} />{metric.label}</label>)}</div>
        <button type="button" onClick={onSave}><Save size={14} />Apply settings</button>
      </div>
    </section>
  );
}

function HealthCard({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: Tone }) {
  return <article className={`edge-health-card edge-tone-${tone}`}><span>{label}</span><strong>{value}</strong><p>{detail}</p></article>;
}

function SectionHead({ label, value }: { label: string; value: string }) {
  return <div className="edge-section-head"><span>{label}</span><strong>{value}</strong></div>;
}

function ServiceRow({ row }: { row: string[] }) {
  return <div className="edge-service-row"><div><strong>{row[0]}</strong><span>{row[3]}</span></div><b>{row[1]}</b><em>{row[2]}</em></div>;
}

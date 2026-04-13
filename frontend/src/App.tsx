import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, Shield, Globe, CheckCircle, XCircle, Pause, Play, FlaskConical, BookOpen, AlertTriangle, Gauge } from 'lucide-react';
import { TradingOverview } from './components/dashboards/TradingOverview';
import { BrokerHealth } from './components/dashboards/BrokerHealth';
import { PnLTracking } from './components/dashboards/PnLTracking';
import { MarketCoverage } from './components/dashboards/MarketCoverage';
import { TutorialsDashboard } from './components/tutorials';
import { HealthDashboard } from './components';
import { useStore } from './store/useStore';
import { api } from './lib/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const TABS = [
  { id: 'overview', label: 'Trading Overview', icon: Activity },
  { id: 'health', label: 'Service Health', icon: Gauge },
  { id: 'broker', label: 'Broker Health', icon: Shield },
  { id: 'pnl', label: 'P&L Tracking', icon: TrendingUp },
  { id: 'markets', label: 'Market Coverage', icon: Globe },
  { id: 'tutorials', label: 'Tutorials', icon: BookOpen },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function App() {
  const { connected, setConnected, mockMode, setMockMode } = useStore();
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [schedulerPaused, setSchedulerPaused] = useState(false);
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkBackend();
    const interval = setInterval(checkBackend, 15000);
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      const health = await fetch(`${BACKEND_URL}/api/health`).then((r) => r.json());
      setConnected(true);
      setSchedulerPaused(health.paused ?? false);
      
      // Also check kill switch status
      try {
        const killStatus = await fetch(`${BACKEND_URL}/api/emergency/kill-switch`).then((r) => r.json());
        setKillSwitchActive(killStatus.kill_switch_active ?? false);
      } catch { /* kill switch endpoint may not exist */ }
      
      setLoading(false);
    } catch {
      setConnected(false);
      setLoading(false);
    }
  };

  const toggleScheduler = async () => {
    try {
      if (schedulerPaused) {
        await api.resumeScheduler();
        setSchedulerPaused(false);
      } else {
        await api.pauseScheduler();
        setSchedulerPaused(true);
      }
    } catch (err) {
      console.error('Failed to toggle scheduler:', err);
    }
  };

  const toggleKillSwitch = async () => {
    try {
      const newState = !killSwitchActive;
      await api.toggleKillSwitch(newState);
      setKillSwitchActive(newState);
    } catch (err) {
      console.error('Failed to toggle kill switch:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Top bar ── */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-emerald-500 rounded-lg flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Activity className="w-5 h-5 text-black" />
            </div>
            <div>
              <span className="text-lg font-bold text-white tracking-tight">Sentinel Edge</span>
              <span className="ml-2 text-xs text-gray-500 hidden sm:inline">Trading Analyst Sidecar</span>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            {/* Mock mode toggle */}
            <button
              data-testid="mock-mode-toggle"
              onClick={() => setMockMode(!mockMode)}
              title="Toggle mock/simulated data for testing"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                mockMode
                  ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                  : 'bg-gray-700/40 text-gray-500 hover:bg-gray-700/60 hover:text-gray-300'
              }`}
            >
              <FlaskConical className="w-4 h-4" />
              <span className="hidden sm:inline">{mockMode ? 'Mock ON' : 'Mock'}</span>
            </button>

            {/* Pause / Resume */}
            {connected && (
              <button
                data-testid="scheduler-toggle-btn"
                onClick={toggleScheduler}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                  schedulerPaused
                    ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                    : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                }`}
              >
                {schedulerPaused ? (
                  <>
                    <Play className="w-4 h-4" />
                    Resume
                  </>
                ) : (
                  <>
                    <Pause className="w-4 h-4" />
                    Pause
                  </>
                )}
              </button>
            )}

            {/* Kill Switch */}
            <button
              data-testid="kill-switch-btn"
              onClick={toggleKillSwitch}
              title="Emergency kill switch - immediately halts all trading"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                killSwitchActive
                  ? 'bg-red-500/80 text-white animate-pulse'
                  : 'bg-gray-700/40 text-gray-500 hover:bg-red-500/20 hover:text-red-400'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              <span className="hidden sm:inline">{killSwitchActive ? 'KILL' : 'Kill'}</span>
            </button>

            {/* Connection badge */}
            <div
              data-testid="connection-status"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                connected
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/20 text-red-400'
              }`}
            >
              {connected ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Connected
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4" />
                  {loading ? 'Connecting…' : 'Disconnected'}
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ── Tab navigation ── */}
      <nav
        className="border-b border-gray-800 bg-gray-900/50 sticky top-[57px] z-40 backdrop-blur-sm"
        data-testid="tab-navigation"
      >
        <div className="max-w-screen-2xl mx-auto px-6">
          <div className="flex gap-1 overflow-x-auto">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                data-testid={`tab-${id}`}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-5 py-4 text-sm font-medium whitespace-nowrap
                  border-b-2 transition-all duration-200 ${
                    activeTab === id
                      ? 'border-emerald-500 text-emerald-400'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600'
                  }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* ── Page content ── */}
      <main className="max-w-screen-2xl mx-auto px-6 py-8" data-testid="main-content">
        {activeTab === 'overview' && <TradingOverview />}
        {activeTab === 'health' && <HealthDashboard />}
        {activeTab === 'broker' && <BrokerHealth />}
        {activeTab === 'pnl' && <PnLTracking />}
        {activeTab === 'markets' && <MarketCoverage />}
        {activeTab === 'tutorials' && <TutorialsDashboard />}
      </main>
    </div>
  );
}

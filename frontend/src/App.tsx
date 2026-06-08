import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, Globe, CheckCircle, XCircle, Pause, Play, BookOpen, AlertTriangle, Gauge, Server, Wifi, AlertCircle, Wallet, Settings } from 'lucide-react';
import { TradingOverview } from './components/dashboards/TradingOverview';
import { PnLTracking } from './components/dashboards/PnLTracking';
import { MarketCoverage } from './components/dashboards/MarketCoverage';
import { PortfolioAnalytics } from './components/dashboards/PortfolioAnalytics';
import { SettingsDashboard } from './components/dashboards/SettingsDashboard';
import { TutorialsDashboard } from './components/tutorials';
import { AdvisorHealth } from './components/dashboards/AdvisorHealth';
import { useStore } from './store/useStore';
import { api } from './lib/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const TABS = [
  { id: 'overview', label: 'Trading Overview', icon: Activity },
  { id: 'health', label: 'Advisor Health', icon: Gauge },
  { id: 'pnl', label: 'P&L Tracking', icon: TrendingUp },
  { id: 'markets', label: 'Market Coverage', icon: Globe },
  { id: 'portfolio', label: 'Portfolio', icon: Wallet },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'tutorials', label: 'Tutorials', icon: BookOpen },
] as const;

type TabId = (typeof TABS)[number]['id'];

// ==================== Pulse Availability Modal ====================

interface PulseModalProps {
  isOpen: boolean;
  pulseAvailable: boolean;
  pulseUrl: string;
  onStartWithPulse: () => void;
  onStartStandalone: () => void;
}

function PulseStartupModal({ isOpen, pulseAvailable, pulseUrl, onStartWithPulse, onStartStandalone }: PulseModalProps) {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${pulseAvailable ? 'bg-emerald-500/20' : 'bg-amber-500/20'}`}>
            <Server className={`w-5 h-5 ${pulseAvailable ? 'text-emerald-400' : 'text-amber-400'}`} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Sentinel Pulse</h2>
            <p className="text-sm text-gray-400">Execution Broker Service</p>
          </div>
        </div>
        
        {pulseAvailable ? (
          <div className="mb-6">
            <div className="flex items-center gap-2 text-emerald-400 mb-3">
              <CheckCircle className="w-4 h-4" />
              <span className="font-medium">Pulse is available</span>
            </div>
            <p className="text-gray-400 text-sm">
              Sentinel Edge will connect to Pulse at <code className="text-gray-300">{pulseUrl}</code> for order execution and real-time position updates.
            </p>
          </div>
        ) : (
          <div className="mb-6">
            <div className="flex items-center gap-2 text-amber-400 mb-3">
              <AlertCircle className="w-4 h-4" />
              <span className="font-medium">Pulse not detected</span>
            </div>
            <p className="text-gray-400 text-sm mb-3">
              Sentinel Edge can run in standalone mode without Pulse. Decisions will be logged but no orders will be executed.
            </p>
            <div className="bg-gray-800 rounded-lg p-3 text-sm">
              <p className="text-gray-500 mb-1">Expected Pulse URL:</p>
              <code className="text-gray-300">{pulseUrl}</code>
            </div>
          </div>
        )}
        
        <div className="flex gap-3">
          {pulseAvailable ? (
            <button
              onClick={onStartWithPulse}
              className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <Wifi className="w-4 h-4" />
              Connect to Pulse
            </button>
          ) : (
            <button
              onClick={onStartWithPulse}
              className="flex-1 bg-amber-500 hover:bg-amber-600 text-white font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <Wifi className="w-4 h-4" />
              Try Connecting
            </button>
          )}
          <button
            onClick={onStartStandalone}
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-medium py-2.5 px-4 rounded-lg transition-colors"
          >
            Standalone Mode
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== Main App ====================

export default function App() {
  const { connected, setConnected } = useStore();
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [schedulerPaused, setSchedulerPaused] = useState(false);
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Pulse state
  const [showPulseModal, setShowPulseModal] = useState(true);
  const [pulseAvailable, setPulseAvailable] = useState(false);
  const [pulseUrl, setPulseUrl] = useState('http://pulse:8001');
  const [pulseChecked, setPulseChecked] = useState(false);
  
  // Get Pulse URL from environment or use default
  const PULSE_URL = process.env.REACT_APP_PULSE_URL || 'http://pulse:8001';

  useEffect(() => {
    // Check Pulse availability on mount
    checkPulseAvailability();
    
    checkBackend();
    const interval = setInterval(checkBackend, 15000);
    return () => clearInterval(interval);
  }, []);

  const checkPulseAvailability = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/pulse/status`);
      if (response.ok) {
        const data = await response.json();
        setPulseAvailable(data.available || false);
        setPulseUrl(data.base_url || PULSE_URL);
      }
    } catch {
      setPulseAvailable(false);
    }
    setPulseChecked(true);
  };

  const handleStartWithPulse = () => {
    setShowPulseModal(false);
    // Could trigger a retry connection to Pulse here
  };

  const handleStartStandalone = () => {
    setShowPulseModal(false);
  };

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

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Pulse Startup Modal ── */}
      <PulseStartupModal
        isOpen={showPulseModal && pulseChecked}
        pulseAvailable={pulseAvailable}
        pulseUrl={pulseUrl}
        onStartWithPulse={handleStartWithPulse}
        onStartStandalone={handleStartStandalone}
      />
      
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

            {/* Kill switch indicator - read-only in Edge UI */}
            <div
              data-testid="kill-switch-status"
              title="Emergency kill switch status is read-only in Sentinel Edge"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                killSwitchActive
                  ? 'bg-red-500/80 text-white animate-pulse'
                  : 'bg-gray-700/40 text-gray-500'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              <span className="hidden sm:inline">{killSwitchActive ? 'Kill Active' : 'Kill Clear'}</span>
            </div>

            {/* Pulse indicator */}
            <div
              title={`Pulse: ${pulseAvailable ? 'Connected' : 'Not connected'}`}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                pulseAvailable
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-amber-500/20 text-amber-400'
              }`}
            >
              <Server className="w-4 h-4" />
              <span className="hidden sm:inline">{pulseAvailable ? 'Pulse' : 'No Pulse'}</span>
            </div>

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
        {activeTab === 'health' && <AdvisorHealth />}
        {activeTab === 'pnl' && <PnLTracking />}
        {activeTab === 'markets' && <MarketCoverage />}
        {activeTab === 'portfolio' && <PortfolioAnalytics />}
        {activeTab === 'settings' && <SettingsDashboard />}
        {activeTab === 'tutorials' && <TutorialsDashboard />}
      </main>
    </div>
  );
}

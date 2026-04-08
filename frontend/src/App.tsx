import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, BarChart3, Globe, Menu, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from './store/useStore';
import { api } from './lib/api';

// Import dashboard components
import { TradingOverview } from './components/dashboards/TradingOverview';
import { BrokerHealth } from './components/dashboards/BrokerHealth';
import { PnLTracking } from './components/dashboards/PnLTracking';
import { MarketCoverage } from './components/dashboards/MarketCoverage';

const tabs = [
  { id: 'overview', name: 'Trading Overview', icon: Activity },
  { id: 'broker', name: 'Broker Health', icon: TrendingUp },
  { id: 'pnl', name: 'P&L Tracking', icon: BarChart3 },
  { id: 'markets', name: 'Market Coverage', icon: Globe },
];

function App() {
  const { activeTab, setActiveTab, stats, connected, setConnected, setStats } = useStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, []);

  const checkConnection = async () => {
    try {
      const health = await api.getHealth();
      setConnected(true);
      setStats({
        active_tickers: health.active_tickers || 0,
        running: health.running || false,
        paused: health.paused || false,
        orb_levels_count: 0,
        pulse_circuit_state: 'CLOSED',
        pulse_failures: 0,
      });
    } catch (error) {
      console.error('Connection check failed:', error);
      setConnected(false);
    }
  };

  const renderDashboard = () => {
    switch (activeTab) {
      case 'overview':
        return <TradingOverview />;
      case 'broker':
        return <BrokerHealth />;
      case 'pnl':
        return <PnLTracking />;
      case 'markets':
        return <MarketCoverage />;
      default:
        return <TradingOverview />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-lg bg-gray-900/80 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Sentinel Edge</h1>
                <p className="text-xs text-gray-400">Trading Analyst Sidecar</p>
              </div>
            </div>

            {/* Status Indicators */}
            <div className="hidden md:flex items-center gap-4">
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium transition-all
                ${connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                <div className={`w-2 h-2 rounded-full ${
                  connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                {connected ? 'Connected' : 'Disconnected'}
              </div>
              
              {stats && (
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium
                  ${stats.running ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'}`}>
                  {stats.running ? '▶ Running' : '⏸ Stopped'}
                  {stats.paused && ' (Paused)'}
                </div>
              )}

              {stats && stats.active_tickers > 0 && (
                <div className="flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-purple-500/20 text-purple-400">
                  <Activity className="w-4 h-4" />
                  {stats.active_tickers} Tickers
                </div>
              )}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-800 text-gray-400 transition-colors"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="sticky top-16 z-40 backdrop-blur-lg bg-gray-900/70 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-2 overflow-x-auto hide-scrollbar py-3">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative flex items-center gap-2 px-4 py-2 rounded-lg font-medium
                    transition-all whitespace-nowrap ${
                      isActive
                        ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-white'
                        : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                    }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.name}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-500"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {renderDashboard()}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="mt-16 border-t border-gray-800 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>Sentinel Edge v1.0.0 - Production-Ready Trading Analyst</p>
            <p className="mt-1">Powered by Prometheus & Grafana | TypeScript + React + FastAPI</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, BarChart3, Globe, Menu, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from './store/useStore';
import { api } from './lib/api';

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

export default function App() {
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
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-emerald-500 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-black" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Sentinel Edge</h1>
              <p className="text-xs text-gray-500 -mt-1">Trading Analyst Sidecar</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`px-3 py-1 rounded-full text-sm flex items-center gap-2 
              ${connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
              {connected ? '● Connected to Pulse' : '○ Disconnected'}
            </div>
            <button className="p-2 hover:bg-gray-800 rounded-lg">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-4 border-b border-gray-800">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-2xl transition-all whitespace-nowrap
                  ${isActive 
                    ? 'bg-white text-black shadow-lg' 
                    : 'hover:bg-gray-800 text-gray-400 hover:text-gray-200'}`}
              >
                <Icon className="w-4 h-4" />
                {tab.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {renderDashboard()}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

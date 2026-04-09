import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, Zap, CheckCircle, XCircle } from 'lucide-react';
import { api } from './lib/api';

export default function App() {
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkBackend();
  }, []);

  const checkBackend = async () => {
    try {
      const health = await api.getHealth();
      setConnected(true);
      setStats(health);
      setLoading(false);
      console.log('✅ Backend data:', health);
    } catch (error) {
      console.error('❌ API Error:', error);
      setConnected(false);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-black" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Sentinel Edge</h1>
              <p className="text-gray-400">Testing API without Zustand</p>
            </div>
          </div>

          {/* Connection Status */}
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
            connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {connected ? (
              <>
                <CheckCircle className="w-4 h-4" />
                <span>Connected</span>
              </>
            ) : (
              <>
                <XCircle className="w-4 h-4" />
                <span>Disconnected</span>
              </>
            )}
          </div>
        </div>

        {/* Success Box */}
        <div className="bg-emerald-500/10 border-2 border-emerald-500 rounded-xl p-6 mb-6">
          <h2 className="text-2xl font-bold text-emerald-400 mb-2">
            ✅ Testing: React + Tailwind + Icons + Axios (No Zustand)
          </h2>
          <p className="text-gray-300 mb-3">
            {loading ? 'Loading backend data...' : 
              connected ? 'Successfully fetched data from backend!' : 
              'Could not connect to backend'}
          </p>
          {stats && (
            <div className="text-sm text-gray-400 space-y-1">
              <p>• Backend Status: {stats.running ? '✓ Running' : '✗ Stopped'}</p>
              <p>• Active Tickers: {stats.active_tickers}</p>
              <p>• Paused: {stats.paused ? 'Yes' : 'No'}</p>
            </div>
          )}
        </div>

        {/* Cards with Live Data */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <Activity className="w-8 h-8 text-blue-400 mb-2" />
            <div className="text-2xl font-bold text-white">
              {stats?.running ? '✓' : '✗'}
            </div>
            <p className="text-sm text-gray-400">Backend Status</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <TrendingUp className="w-8 h-8 text-green-400 mb-2" />
            <div className="text-2xl font-bold text-white">
              {stats?.active_tickers || 0}
            </div>
            <p className="text-sm text-gray-400">Active Tickers</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <Zap className="w-8 h-8 text-purple-400 mb-2" />
            <div className="text-2xl font-bold text-white">30+</div>
            <p className="text-sm text-gray-400">Metrics</p>
          </div>
        </div>
      </div>
    </div>
  );
}

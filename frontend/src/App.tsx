import React from 'react';
import { Activity } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-black" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Sentinel Edge</h1>
            <p className="text-gray-400">Trading Analyst Sidecar - System Online</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">Backend Status</h3>
            <div className="text-emerald-400 text-2xl">✓ Running</div>
            <p className="text-sm text-gray-500 mt-2">Port 8001</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">Active Tickers</h3>
            <div className="text-blue-400 text-2xl">4</div>
            <p className="text-sm text-gray-500 mt-2">SPY, QQQ, NVDA, AAPL</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">Prometheus Metrics</h3>
            <div className="text-purple-400 text-2xl">30+</div>
            <p className="text-sm text-gray-500 mt-2">Real-time collection</p>
          </div>
        </div>

        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">✅ System Operational</h2>
          <p className="text-gray-300 mb-4">
            Sentinel Edge is running successfully! The backend is actively monitoring tickers
            and exposing Prometheus metrics.
          </p>
          <div className="flex gap-3">
            <a 
              href="http://localhost:8001/api/health"
              target="_blank"
              className="px-4 py-2 bg-emerald-500 text-black rounded-lg hover:bg-emerald-400 transition-colors"
            >
              View API Health
            </a>
            <a 
              href="http://localhost:8001/metrics"
              target="_blank"
              className="px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors"
            >
              View Metrics
            </a>
          </div>
        </div>

        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Sentinel Edge v1.0.0 | TypeScript + React + FastAPI + Prometheus</p>
        </div>
      </div>
    </div>
  );
}

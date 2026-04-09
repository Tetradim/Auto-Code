import React from 'react';
import { Activity, TrendingUp, Zap } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header with Icon */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-black" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Sentinel Edge</h1>
            <p className="text-gray-400">Icons Working!</p>
          </div>
        </div>

        <div className="bg-emerald-500/10 border-2 border-emerald-500 rounded-xl p-6 mb-6">
          <h2 className="text-2xl font-bold text-emerald-400 mb-2">
            ✅ React + Tailwind + Icons Working!
          </h2>
          <p className="text-gray-300">
            If you can see the ⚡ icon in the header above, Lucide React icons are loaded.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <Activity className="w-8 h-8 text-blue-400 mb-2" />
            <p className="text-sm text-gray-400">Backend Running</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <TrendingUp className="w-8 h-8 text-green-400 mb-2" />
            <p className="text-sm text-gray-400">4 Active Tickers</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <Zap className="w-8 h-8 text-purple-400 mb-2" />
            <p className="text-sm text-gray-400">30+ Metrics</p>
          </div>
        </div>
      </div>
    </div>
  );
}

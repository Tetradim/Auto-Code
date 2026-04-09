import React from 'react';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-emerald-500/10 border-2 border-emerald-500 rounded-xl p-6 mb-6">
          <h2 className="text-2xl font-bold text-emerald-400 mb-2">
            ✅ React + Tailwind Working!
          </h2>
          <p className="text-gray-300">
            If you can see this green box with proper styling, Tailwind CSS is working.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="text-blue-400 text-2xl font-bold">✓</div>
            <p className="text-sm text-gray-400 mt-2">Backend Running</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="text-green-400 text-2xl font-bold">4</div>
            <p className="text-sm text-gray-400 mt-2">Active Tickers</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="text-purple-400 text-2xl font-bold">30+</div>
            <p className="text-sm text-gray-400 mt-2">Metrics</p>
          </div>
        </div>
      </div>
    </div>
  );
}

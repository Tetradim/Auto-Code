/**
 * Greeks Dashboard
 * Displays Delta, Theta, Vega, Gamma analysis charts
 * Shows directional insights, time decay, volatility sensitivity, and delta acceleration
 */
import React, { useEffect, useState } from 'react';
import { TrendingUp, Clock, Wind, Zap, BarChart3, Activity } from 'lucide-react';
import { MetricCard } from '../cards/MetricCard';
import { ChartCard } from '../cards/ChartCard';
import { useStore } from '@/store/useStore';

// Mock data for Greeks - in production, this would come from the backend API
const generateMockGreeks = () => {
  const baseDelta = Math.random() * 2 - 1; // -1 to 1
  const baseTheta = -Math.random() * 50; // negative for buyers
  const baseVega = Math.random() * 100;
  const baseGamma = Math.random() * 50;
  
  return {
    delta: {
      value: baseDelta,
      direction: baseDelta > 0 ? 'bullish' : baseDelta < 0 ? 'bearish' : 'neutral',
      probItm: Math.abs(baseDelta) * 100,
      strength: Math.abs(baseDelta),
      support: 100 + Math.random() * 50,
      resistance: 200 + Math.random() * 50,
    },
    theta: {
      daily: baseTheta,
      weekly: baseTheta * 7,
      monthly: baseTheta * 30,
      regime: Math.abs(baseTheta) > 30 ? 'accelerating' : Math.abs(baseTheta) > 15 ? 'normal' : 'slow',
      drag: Math.abs(baseTheta) / 1000,
    },
    vega: {
      value: baseVega,
      iv: 0.15 + Math.random() * 0.3,
      ivSkew: (Math.random() - 0.5) * 0.1,
      sentiment: baseVega > 50 ? 'long_vol' : 'short_vol',
    },
    gamma: {
      value: baseGamma,
      callGamma: baseGamma * 0.6,
      putGamma: baseGamma * 0.4,
      risk: baseGamma > 30 ? 'high' : baseGamma > 15 ? 'medium' : 'low',
    }
  };
};

interface GreeksData {
  delta: {
    value: number;
    direction: string;
    probItm: number;
    strength: number;
    support: number;
    resistance: number;
  };
  theta: {
    daily: number;
    weekly: number;
    monthly: number;
    regime: string;
    drag: number;
  };
  vega: {
    value: number;
    iv: number;
    ivSkew: number;
    sentiment: string;
  };
  gamma: {
    value: number;
    callGamma: number;
    putGamma: number;
    risk: string;
  };
}

export const GreeksDashboard: React.FC = () => {
  const { greeksEnabled } = useStore();
  const [greeksData, setGreeksData] = useState<GreeksData | null>(null);
  const [loading, setLoading] = useState(true);

  // Load Greek data based on enabled checkboxes
  useEffect(() => {
    if (!Object.values(greeksEnabled).some(v => v)) {
      setLoading(false);
      setGreeksData(null);
      return;
    }

    setLoading(true);
    // Simulate API call - in production, fetch from backend
    const timer = setTimeout(() => {
      setGreeksData(generateMockGreeks());
      setLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, [greeksEnabled]);

  if (!Object.values(greeksEnabled).some(v => v)) {
    return (
      <div className="p-6 text-center">
        <Activity className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-400 mb-2">Greek Analysis Disabled</h3>
        <p className="text-sm text-gray-500">
          Enable Greek analysis in Settings to view Delta, Theta, Vega, and Gamma charts
        </p>
      </div>
    );
  }

  if (loading || !greeksData) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-purple-500/20">
          <TrendingUp className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">Greek Analysis</h2>
          <p className="text-sm text-gray-400">
            Options Greeks: Delta, Theta, Vega, Gamma
          </p>
        </div>
      </div>

      {/* Summary Table */}
      <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Summary for Long (Buying) Positions</h3>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div className="space-y-1">
            <span className="text-gray-500">Greek</span>
            <p className="text-white font-medium">Delta</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Measures</span>
            <p className="text-white">Direction Sensitivity</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Goal for Buyer</span>
            <p className="text-emerald-400">High (closer to ±1)</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Current</span>
            <p className={greeksData.delta.value > 0.5 || greeksData.delta.value < -0.5 ? 'text-emerald-400' : 'text-yellow-400'}>
              {greeksData.delta.value.toFixed(2)}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4 text-sm mt-3 pt-3 border-t border-gray-700">
          <div className="space-y-1">
            <span className="text-gray-500">Greek</span>
            <p className="text-white font-medium">Theta</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Measures</span>
            <p className="text-white">Daily Time Decay</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Goal for Buyer</span>
            <p className="text-emerald-400">Low (lower daily loss)</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Current</span>
            <p className={Math.abs(greeksData.theta.daily) < 15 ? 'text-emerald-400' : 'text-red-400'}>
              ${greeksData.theta.daily.toFixed(2)}/day
            </p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4 text-sm mt-3 pt-3 border-t border-gray-700">
          <div className="space-y-1">
            <span className="text-gray-500">Greek</span>
            <p className="text-white font-medium">Vega</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Measures</span>
            <p className="text-white">IV Sensitivity</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Goal for Buyer</span>
            <p className="text-emerald-400">Higher if IV rising</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Current</span>
            <p className={greeksData.vega.iv > 0.25 ? 'text-yellow-400' : 'text-emerald-400'}>
              {(greeksData.vega.iv * 100).toFixed(1)}% IV
            </p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4 text-sm mt-3 pt-3 border-t border-gray-700">
          <div className="space-y-1">
            <span className="text-gray-500">Greek</span>
            <p className="text-white font-medium">Gamma</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Measures</span>
            <p className="text-white">Delta Acceleration</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Goal for Buyer</span>
            <p className="text-emerald-400">High (leverage in your favor)</p>
          </div>
          <div className="space-y-1">
            <span className="text-gray-500">Current</span>
            <p className={greeksData.gamma.value > 20 ? 'text-emerald-400' : 'text-yellow-400'}>
              {greeksData.gamma.value.toFixed(2)}
            </p>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Delta Chart */}
        {(greeksEnabled.delta || greeksEnabled.gex) && (
          <ChartCard
            title="Delta Direction"
            icon={<TrendingUp className="w-4 h-4" />}
            className="col-span-1"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Direction</span>
                <span className={`text-sm font-medium ${
                  greeksData.delta.direction === 'bullish' ? 'text-emerald-400' :
                  greeksData.delta.direction === 'bearish' ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {greeksData.delta.direction.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Probability ITM</span>
                <span className="text-sm font-medium text-white">
                  {greeksData.delta.probItm.toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Strength</span>
                <div className="w-24 bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-purple-400 h-2 rounded-full" 
                    style={{ width: `${greeksData.delta.strength * 100}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Support</span>
                <span className="text-sm font-medium text-white">
                  ${greeksData.delta.support.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Resistance</span>
                <span className="text-sm font-medium text-white">
                  ${greeksData.delta.resistance.toFixed(2)}
                </span>
              </div>
            </div>
          </ChartCard>
        )}

        {/* Theta Chart */}
        {(greeksEnabled.theta || greeksEnabled.gex) && (
          <ChartCard
            title="Theta Time Decay"
            icon={<Clock className="w-4 h-4" />}
            className="col-span-1"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Daily Decay</span>
                <span className={`text-sm font-medium ${
                  Math.abs(greeksData.theta.daily) < 15 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  ${Math.abs(greeksData.theta.daily).toFixed(2)}/day
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Weekly Decay</span>
                <span className="text-sm font-medium text-white">
                  ${Math.abs(greeksData.theta.weekly).toFixed(2)}/week
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Monthly Decay</span>
                <span className="text-sm font-medium text-white">
                  ${Math.abs(greeksData.theta.monthly).toFixed(2)}/mo
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Regime</span>
                <span className={`text-sm font-medium ${
                  greeksData.theta.regime === 'accelerating' ? 'text-red-400' :
                  greeksData.theta.regime === 'normal' ? 'text-yellow-400' : 'text-emerald-400'
                }`}>
                  {greeksData.theta.regime}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Portfolio Drag</span>
                <span className="text-sm font-medium text-white">
                  {(greeksData.theta.drag * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          </ChartCard>
        )}

        {/* Vega Chart */}
        {(greeksEnabled.vega || greeksEnabled.vex) && (
          <ChartCard
            title="Vega Volatility"
            icon={<Wind className="w-4 h-4" />}
            className="col-span-1"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Implied Vol</span>
                <span className={`text-sm font-medium ${
                  greeksData.vega.iv > 0.30 ? 'text-red-400' :
                  greeksData.vega.iv > 0.20 ? 'text-yellow-400' : 'text-emerald-400'
                }`}>
                  {(greeksData.vega.iv * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">IV Skew</span>
                <span className="text-sm font-medium text-white">
                  {(greeksData.vega.ivSkew * 100).toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Vega Exposure</span>
                <span className="text-sm font-medium text-white">
                  {greeksData.vega.value.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Vol Sentiment</span>
                <span className={`text-sm font-medium ${
                  greeksData.vega.sentiment === 'long_vol' ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {greeksData.vega.sentiment}
                </span>
              </div>
            </div>
          </ChartCard>
        )}

        {/* Gamma Chart */}
        {(greeksEnabled.gamma || greeksEnabled.gex) && (
          <ChartCard
            title="Gamma Delta Acceleration"
            icon={<Zap className="w-4 h-4" />}
            className="col-span-1"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Net Gamma</span>
                <span className="text-sm font-medium text-white">
                  {greeksData.gamma.value.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Call Gamma</span>
                <span className="text-sm font-medium text-emerald-400">
                  {greeksData.gamma.callGamma.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Put Gamma</span>
                <span className="text-sm font-medium text-red-400">
                  {greeksData.gamma.putGamma.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Gamma Risk</span>
                <span className={`text-sm font-medium ${
                  greeksData.gamma.risk === 'high' ? 'text-red-400' :
                  greeksData.gamma.risk === 'medium' ? 'text-yellow-400' : 'text-emerald-400'
                }`}>
                  {greeksData.gamma.risk.toUpperCase()}
                </span>
              </div>
            </div>
          </ChartCard>
        )}
      </div>
    </div>
  );
};

export default GreeksDashboard;
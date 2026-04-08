import React, { useEffect, useState } from 'react';
import { Activity, TrendingUp, AlertCircle, Zap } from 'lucide-react';
import { MetricCard } from '../cards/MetricCard';
import { TickerCard } from '../cards/TickerCard';
import { ChartCard } from '../cards/ChartCard';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';

export const TradingOverview: React.FC = () => {
  const { tickers, stats, setTickers, setStats } = useStore();
  const [breakoutData, setBreakoutData] = useState<any[]>([]);
  const [tickerConfigs, setTickerConfigs] = useState<Record<string, any>>({});

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [tickersData, statsData] = await Promise.all([
        api.getTickers(),
        api.getStats(),
      ]);
      setTickers(tickersData.tickers || []);
      setStats(statsData);
      
      // Mock breakout data for chart
      setBreakoutData([
        { timestamp: '10:00', value: 2 },
        { timestamp: '10:30', value: 5 },
        { timestamp: '11:00', value: 3 },
        { timestamp: '11:30', value: 7 },
        { timestamp: '12:00', value: 4 },
        { timestamp: '12:30', value: 6 },
      ]);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleMetricToggle = async (symbol: string, metric: string) => {
    const currentConfig = tickerConfigs[symbol] || {
      orb: true,
      atr: true,
      signal: true,
      volume: true,
      price: true,
      breakouts: true,
    };

    const newConfig = {
      ...currentConfig,
      [metric]: !currentConfig[metric],
    };

    setTickerConfigs({
      ...tickerConfigs,
      [symbol]: newConfig,
    });

    // Update backend
    try {
      await api.updateTickerConfig(symbol, { metrics: newConfig });
      console.log(`Updated ${symbol} config:`, newConfig);
    } catch (error) {
      console.error(`Failed to update ${symbol} config:`, error);
    }
  };

  const activeTickers = tickers.filter(t => t.enabled);
  const totalBreakouts = breakoutData.reduce((sum, d) => sum + d.value, 0);
  const avgSignalStrength = activeTickers.length > 0
    ? (activeTickers.reduce((sum, t) => sum + (t.signal_strength || 0), 0) / activeTickers.length)
    : 0;

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Active Tickers"
          value={activeTickers.length}
          subtitle="Currently monitored"
          icon={Activity}
          color="blue"
          trend="neutral"
        />
        <MetricCard
          title="ORB Breakouts"
          value={totalBreakouts}
          subtitle="Today"
          icon={TrendingUp}
          color="green"
          change="+12.5%"
          trend="up"
        />
        <MetricCard
          title="Avg Signal Strength"
          value={avgSignalStrength.toFixed(1)}
          subtitle="Across all tickers"
          icon={Zap}
          color={avgSignalStrength >= 0 ? 'green' : 'red'}
        />
        <MetricCard
          title="System Status"
          value={stats?.running ? 'Running' : 'Stopped'}
          subtitle={stats?.paused ? 'Paused' : 'Active'}
          icon={AlertCircle}
          color={stats?.running ? 'green' : 'red'}
        />
      </div>

      {/* Breakout Activity Chart */}
      <ChartCard
        title="ORB Breakout Activity"
        data={breakoutData}
        type="area"
        color="#22c55e"
        height={250}
      />

      {/* Ticker Cards Grid */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-4">Active Tickers</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {activeTickers.map((ticker) => (
            <TickerCard
              key={ticker.symbol}
              symbol={ticker.symbol}
              enabled={ticker.enabled}
              currentPrice={ticker.current_price}
              signalStrength={ticker.signal_strength}
              trend={ticker.trend}
              orbHigh={ticker.orb_levels?.['15m']?.high}
              orbLow={ticker.orb_levels?.['15m']?.low}
              atr={ticker.atr}
              volumeRatio={ticker.volume_ratio}
              metricToggles={tickerConfigs[ticker.symbol]}
              onToggle={() => console.log('Toggle', ticker.symbol)}
              onConfigure={() => console.log('Configure', ticker.symbol)}
              onMetricToggle={(metric) => handleMetricToggle(ticker.symbol, metric)}
            />
          ))}
        </div>
        
        {activeTickers.length === 0 && (
          <div className="text-center py-12">
            <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No active tickers</p>
            <p className="text-gray-500 text-sm">Add tickers to start monitoring</p>
          </div>
        )}
      </div>
    </div>
  );
};

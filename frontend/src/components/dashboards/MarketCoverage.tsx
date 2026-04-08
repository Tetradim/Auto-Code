import React, { useEffect, useState } from 'react';
import { Globe, Clock, MapPin, DollarSign } from 'lucide-react';
import { MetricCard } from '../cards/MetricCard';
import { motion } from 'framer-motion';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';

interface Market {
  code: string;
  name: string;
  flag: string;
  timezone: string;
  currency: string;
  open: boolean;
  lunch_break: boolean;
  minutes_to_close: number;
}

export const MarketCoverage: React.FC = () => {
  const { markets, setMarkets } = useStore();
  const [marketsList, setMarketsList] = useState<Market[]>([
    { code: 'US', name: 'NYSE/NASDAQ', flag: '🇺🇸', timezone: 'ET', currency: 'USD', open: true, lunch_break: false, minutes_to_close: 240 },
    { code: 'HK', name: 'HKEX', flag: '🇭🇰', timezone: 'HKT', currency: 'HKD', open: false, lunch_break: false, minutes_to_close: 0 },
    { code: 'AU', name: 'ASX', flag: '🇦🇺', timezone: 'AEST', currency: 'AUD', open: false, lunch_break: false, minutes_to_close: 0 },
    { code: 'UK', name: 'LSE', flag: '🇬🇧', timezone: 'GMT', currency: 'GBP', open: false, lunch_break: false, minutes_to_close: 0 },
    { code: 'CA', name: 'TSX', flag: '🇨🇦', timezone: 'ET', currency: 'CAD', open: true, lunch_break: false, minutes_to_close: 240 },
    { code: 'CN_SS', name: 'Shanghai SSE', flag: '🇨🇳', timezone: 'CST', currency: 'CNY', open: false, lunch_break: false, minutes_to_close: 0 },
    { code: 'CN_SZ', name: 'Shenzhen SZSE', flag: '🇨🇳', timezone: 'CST', currency: 'CNY', open: false, lunch_break: false, minutes_to_close: 0 },
  ]);

  useEffect(() => {
    loadMarkets();
    const interval = setInterval(loadMarkets, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const loadMarkets = async () => {
    try {
      const data = await api.getMarkets();
      setMarkets(data);
    } catch (error) {
      console.error('Failed to load markets:', error);
    }
  };

  const openMarkets = marketsList.filter(m => m.open).length;
  const lunchBreakMarkets = marketsList.filter(m => m.lunch_break).length;
  const totalMarkets = marketsList.length;

  const getStatusColor = (market: Market) => {
    if (market.lunch_break) return 'from-yellow-500/30 to-yellow-600/10 border-yellow-500/50';
    if (market.open) return 'from-green-500/30 to-green-600/10 border-green-500/50';
    return 'from-gray-700/30 to-gray-800/10 border-gray-600/50';
  };

  const getStatusBadge = (market: Market) => {
    if (market.lunch_break) return (
      <span className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-500/20 text-yellow-400">
        Lunch Break
      </span>
    );
    if (market.open) return (
      <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-500/20 text-green-400">
        Open
      </span>
    );
    return (
      <span className="px-3 py-1 rounded-full text-sm font-medium bg-gray-500/20 text-gray-400">
        Closed
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Markets"
          value={totalMarkets}
          subtitle="Tracked globally"
          icon={Globe}
          color="blue"
        />
        <MetricCard
          title="Markets Open"
          value={openMarkets}
          subtitle={`${((openMarkets / totalMarkets) * 100).toFixed(0)}% active`}
          icon={Clock}
          color="green"
        />
        <MetricCard
          title="Lunch Break"
          value={lunchBreakMarkets}
          subtitle="Temporary pause"
          icon={MapPin}
          color="yellow"
        />
        <MetricCard
          title="Markets Closed"
          value={totalMarkets - openMarkets}
          subtitle="After hours"
          icon={DollarSign}
          color="red"
        />
      </div>

      {/* Market Cards Grid */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-4">Global Markets Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {marketsList.map((market, index) => (
            <motion.div
              key={market.code}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`relative overflow-hidden rounded-xl border backdrop-blur-sm
                bg-gradient-to-br ${getStatusColor(market)}
                shadow-lg hover:shadow-2xl transition-all duration-300`}
            >
              <div className="p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-4xl">{market.flag}</span>
                  {getStatusBadge(market)}
                </div>

                {/* Market Info */}
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white">{market.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span>{market.timezone}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <DollarSign className="w-4 h-4" />
                    <span>{market.currency}</span>
                  </div>
                </div>

                {/* Time to Close */}
                {market.open && market.minutes_to_close > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-700/50">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-400">Closes in</span>
                      <span className="text-lg font-semibold text-white">
                        {Math.floor(market.minutes_to_close / 60)}h {market.minutes_to_close % 60}m
                      </span>
                    </div>
                    <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                        style={{ width: `${(market.minutes_to_close / 390) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Glow effect */}
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Market Session Timeline */}
      <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50
        backdrop-blur-sm shadow-xl p-6">
        <h3 className="text-xl font-bold text-white mb-4">24-Hour Market Coverage</h3>
        <div className="space-y-2">
          {marketsList.map((market) => (
            <div key={market.code} className="flex items-center gap-4">
              <span className="text-2xl w-8">{market.flag}</span>
              <span className="text-sm text-gray-400 w-32">{market.name}</span>
              <div className="flex-1 h-8 bg-gray-800 rounded-lg overflow-hidden relative">
                {market.open && (
                  <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-green-500/50 to-green-400/30"
                    style={{ width: '60%' }}
                  />
                )}
              </div>
              <span className="text-sm text-gray-500 w-20">{market.timezone}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

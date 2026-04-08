import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { MetricCard } from '../cards/MetricCard';
import { ChartCard } from '../cards/ChartCard';
import { motion } from 'framer-motion';

interface BrokerStatus {
  id: string;
  name: string;
  state: string;
  failures: number;
  successRate: number;
}

export const BrokerHealth: React.FC = () => {
  const [brokers] = useState<BrokerStatus[]>([
    { id: 'pulse', name: 'Pulse API', state: 'CLOSED', failures: 0, successRate: 100 },
  ]);

  const [apiLatency] = useState([
    { timestamp: '10:00', value: 45 },
    { timestamp: '10:30', value: 52 },
    { timestamp: '11:00', value: 38 },
    { timestamp: '11:30', value: 41 },
    { timestamp: '12:00', value: 47 },
    { timestamp: '12:30', value: 39 },
  ]);

  const totalBrokers = brokers.length;
  const healthyBrokers = brokers.filter(b => b.state === 'CLOSED').length;
  const avgSuccessRate = brokers.reduce((sum, b) => sum + b.successRate, 0) / totalBrokers;
  const totalFailures = brokers.reduce((sum, b) => sum + b.failures, 0);

  const getStateColor = (state: string) => {
    switch (state) {
      case 'CLOSED': return 'text-green-400 bg-green-500/20';
      case 'HALF_OPEN': return 'text-yellow-400 bg-yellow-500/20';
      case 'OPEN': return 'text-red-400 bg-red-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'CLOSED': return <CheckCircle className="w-5 h-5" />;
      case 'HALF_OPEN': return <AlertTriangle className="w-5 h-5" />;
      case 'OPEN': return <XCircle className="w-5 h-5" />;
      default: return <Shield className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Brokers"
          value={totalBrokers}
          subtitle="Connected"
          icon={Shield}
          color="blue"
        />
        <MetricCard
          title="Healthy Brokers"
          value={healthyBrokers}
          subtitle={`${((healthyBrokers / totalBrokers) * 100).toFixed(0)}% operational`}
          icon={CheckCircle}
          color="green"
        />
        <MetricCard
          title="Success Rate"
          value={`${avgSuccessRate.toFixed(1)}%`}
          subtitle="Average across all"
          icon={CheckCircle}
          color="green"
        />
        <MetricCard
          title="Total Failures"
          value={totalFailures}
          subtitle="Last 24 hours"
          icon={AlertTriangle}
          color={totalFailures > 0 ? 'red' : 'green'}
        />
      </div>

      {/* API Latency Chart */}
      <ChartCard
        title="API Call Latency (ms)"
        data={apiLatency}
        type="line"
        color="#8b5cf6"
        height={250}
      />

      {/* Broker Status Cards */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-4">Broker Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {brokers.map((broker) => (
            <motion.div
              key={broker.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative overflow-hidden rounded-xl border border-gray-800 bg-gradient-to-br from-gray-900/90 to-gray-800/50
                backdrop-blur-sm shadow-xl hover:shadow-2xl transition-all duration-300"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-white">{broker.name}</h3>
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${getStateColor(broker.state)}`}>
                    {getStateIcon(broker.state)}
                    <span>{broker.state}</span>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Success Rate</span>
                    <span className="text-lg font-semibold text-green-400">{broker.successRate}%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Failures</span>
                    <span className={`text-lg font-semibold ${broker.failures > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {broker.failures}
                    </span>
                  </div>
                  
                  {/* Success Rate Bar */}
                  <div className="mt-4">
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-500"
                        style={{ width: `${broker.successRate}%` }}
                      />
                    </div>
                  </div>
                </div>

                {broker.state !== 'CLOSED' && (
                  <button className="mt-4 w-full px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg
                    font-medium transition-all">
                    Reset Circuit Breaker
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

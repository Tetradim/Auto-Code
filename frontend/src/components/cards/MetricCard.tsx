import React from 'react';
import { LucideIcon } from 'lucide-react';
import { motion } from 'framer-motion';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  change?: string;
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple';
  className?: string;
}

const colorClasses = {
  blue: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
  green: 'from-green-500/20 to-green-600/10 border-green-500/30',
  red: 'from-red-500/20 to-red-600/10 border-red-500/30',
  yellow: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30',
  purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/30',
};

const iconColorClasses = {
  blue: 'text-blue-400',
  green: 'text-green-400',
  red: 'text-red-400',
  yellow: 'text-yellow-400',
  purple: 'text-purple-400',
};

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  change,
  color = 'blue',
  className = '',
}) => {
  const getTrendColor = () => {
    if (trend === 'up') return 'text-green-400';
    if (trend === 'down') return 'text-red-400';
    return 'text-gray-400';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative overflow-hidden rounded-xl border backdrop-blur-sm
        bg-gradient-to-br ${colorClasses[color]} ${className}
        hover:border-opacity-50 transition-all duration-300
        shadow-lg hover:shadow-xl`}
    >
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-400 mb-1">{title}</p>
            <h3 className="text-3xl font-bold text-white mb-1">{value}</h3>
            {subtitle && (
              <p className="text-sm text-gray-500">{subtitle}</p>
            )}
          </div>
          {Icon && (
            <div className={`p-3 rounded-lg bg-black/20 ${iconColorClasses[color]}`}>
              <Icon className="w-6 h-6" />
            </div>
          )}
        </div>
        
        {change && (
          <div className="mt-4 flex items-center gap-2">
            <span className={`text-sm font-medium ${getTrendColor()}`}>
              {change}
            </span>
            {trend && (
              <span className="text-xs text-gray-500">vs last period</span>
            )}
          </div>
        )}
      </div>
      
      {/* Decorative gradient */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
    </motion.div>
  );
};

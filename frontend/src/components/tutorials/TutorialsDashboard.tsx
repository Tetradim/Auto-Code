import React, { useState } from 'react';
import { BookOpen, Zap, Target, Shield, ShieldOff, ChevronRight, X, Lightbulb } from 'lucide-react';

interface Tutorial {
  id: string;
  title: string;
  dashboard: string;
  icon: string;
  difficulty: 'Advanced' | 'Intermediate';
  color: 'blue' | 'emerald' | 'amber' | 'red';
  brief: string;
  significance: string;
  interpretation: string;
  keyInsight: string;
  bestPractices: string[];
}

const TUTORIALS: Tutorial[] = [
  {
    id: 'signal-engine',
    title: 'Signal Engine: 5-Layer Composite Scoring',
    dashboard: 'Live Trading',
    icon: 'zap',
    difficulty: 'Advanced',
    color: 'blue',
    brief: 'Understanding the ±10 composite signal that drives all trading decisions',
    significance: `The Signal Engine is the brain of Sentinel Edge. It combines 5 independent layers — ORB breakout proximity, ATR-normalized momentum, volume Z-score, trend alignment, and mean reversion signals — into a single score from -10 (strong sell) to +10 (strong buy). Each layer is weighted and can be toggled per-ticker via the Ticker Config panel. A score ≥ 5.0 in a bullish trend triggers a BUY decision, while ≤ -5.0 in bearish triggers STOP_BUYING. The composite nature means no single noisy indicator can dominate. Understanding which layers contribute most to current signals helps you tune weights and identify when the engine is acting on strong multi-factor confluence vs. a single strong signal.`,
    interpretation: `On the Live Trading dashboard, each ticker card shows the real-time signal_strength value. Values near 0 indicate indecision or conflicting signals across layers. Values ±3–5 represent moderate conviction. Values beyond ±7 indicate strong multi-layer agreement. Watch for divergence: if signal is +8 but trend shows 'neutral', the trend layer is fighting the other 4 layers, suggesting the score may be unstable. The decision feed shows how signal scores translate to actual decisions over time — look for patterns where scores oscillate around decision thresholds (3.0 and 5.0) causing rapid BUY/HOLD flipping, which indicates a ticker needs wider decision bands.`,
    keyInsight: 'Always look for confluence between signal strength and trend direction. Divergence often precedes a reversal.',
    bestPractices: [
      "Don't chase high signal scores — a sustained +6 is better than a spike to +9 that drops quickly.",
      "Use the Ticker Config to disable noisy layers for specific tickers. For example, volume Z-score may be unreliable for low-float stocks.",
      "Monitor the relationship between signal_strength and actual P&L. If high signals consistently produce losses, the engine parameters need recalibration.",
      "Use backtesting to validate signal threshold changes before applying them live.",
      "Consider disabling the signal layer entirely for highly correlated ticker pairs to avoid doubling down on the same market movement.",
    ],
  },
  {
    id: 'greeks-intro',
    title: 'Options Greeks: A Practical Framework',
    dashboard: 'Greeks Dashboard',
    icon: 'trending',
    difficulty: 'Intermediate',
    color: 'purple',
    brief: 'Understanding and using Delta, Theta, Vega, Gamma for better trades',
    significance: `The Greeks are mathematical sensitivities that quantify how option prices respond to changes in the underlying (Delta), time (Theta), volatility (Vega), and the rate of Delta change (Gamma). For long (buying) positions, your goals are: Delta high (strong directional exposure), Theta low (minimal daily decay), Vega positioned for your volatility view, Gamma high (leverage in your favor). Understanding which Greek drives your P&L helps you manage trades more actively. Enable Greek analysis in Settings first.`,
    interpretation: `The Greeks Dashboard shows all four Greeks with color-coded indicators. Green means favorable for buyers, red means unfavorable. Use the summary table to quickly check if your position goals align with current values. For example, if you're long calls and Theta shows red (high daily decay), you know time is working against you and should sell before decay accelerates.`,
    keyInsight: "Your P&L is the sum of all Greeks. Know which one you're betting on.",
    bestPractices: [
      "Before entering a position, decide which Greek is your primary driver.",
      "For directional bets without volatility view, prefer high Delta, low Theta, moderate Gamma.",
      "For volatile views, Vega exposure is your primary driver.",
      "Never ignore Theta when holding longer than a few days.",
      "High Gamma = high leverage both directions. It accelerates wins AND losses.",
    ],
  },
  {
    id: 'volatility-regimes',
    title: 'Volatility Regime Detection & Spike Protection',
    dashboard: 'Settings',
    icon: 'shield',
    difficulty: 'Advanced',
    color: 'amber',
    brief: 'Understanding market volatility regimes and protecting against IV spikes',
    significance: `Market volatility moves through regimes from suppressed (calm) to extreme (crisis). Sentinel Edge monitors IV percentiles against a 252-day historical window and can detect when IV spikes more than 50% above recent averages. This matters because option prices explode higher during volatility expansions. Enable IV tracking and spike protection in Settings under Advanced Options.`,
    interpretation: `Check the Greeks Dashboard for volatility regime indicators. The IV gauge shows current IV relative to historical percentiles — green (below 75th), yellow (75th-95th), red (above 95th). The spike warning appears as an alert. During elevated vol, consider taking profits on long options, rolling to later expirations, or reducing position size.`,
    keyInsight: 'IV regime changes often precede price regime changes. A vol spike can catalyze a directional move.',
    bestPractices: [
      "Enable IV percentile tracking in Settings to see historical IV context.",
      "When the gauge turns yellow, start taking profits on long options.",
      "Never hold into earnings with IV at 90th+ percentile — vega crush will decimate premiums.",
      "Use spike protection alerts as forced discipline to review positions.",
      "After a volatility spike, IV typically mean-reverts. Consider buying vol when extremely elevated.",
    ],
  },
  {
    id: 'orb-mechanics',
    title: 'Opening Range Breakout (ORB) Mechanics',
    dashboard: 'Ticker Config',
    icon: 'target',
    difficulty: 'Intermediate',
    color: 'emerald',
    brief: 'How ORB levels at 5m, 15m, and 30m timeframes anchor trading decisions',
    significance: `ORB is a foundational strategy where the high and low of the opening range (first N minutes of market open) define support and resistance levels. Sentinel Edge tracks three timeframes simultaneously — 5-minute (fast, tight range), 15-minute (standard), and 30-minute (wide, more reliable). Once the time window passes, the ORB level 'locks' and becomes a fixed reference. The range_width (high - low) indicates volatility at open — narrow ranges often precede large breakout moves. ORB levels are ET-anchored to US market hours (9:30 AM ET) and automatically reset each trading day. The ORB component feeds into the Signal Engine as a breakout proximity score.`,
    interpretation: `In the Ticker Config panel, the ORB toggle controls whether ORB data feeds the Signal Engine. When viewing ticker state, check if ORB levels are 'locked' — unlocked levels mean the time window is still forming and the range isn't final. A breakout occurs when price moves above ORB high (bullish) or below ORB low (bearish). False breakouts are common in the 5m timeframe but rarer at 30m. Compare the three timeframes: if all three show bullish breakout, it's a strong signal. If 5m shows breakout but 15m/30m don't, it's likely noise.`,
    keyInsight: 'The 15m ORB is generally the best balance of speed and reliability for most liquid stocks.',
    bestPractices: [
      "The 15m ORB is generally the best balance of speed and reliability for most liquid stocks.",
      "Disable ORB for after-hours or pre-market evaluation since the levels won't be meaningful.",
      "Use range_width as a volatility filter — if the opening range is unusually wide (>2x ATR), breakout signals may be less reliable.",
      "Pair ORB breakout signals with volume confirmation.",
      "For backtesting, test each ORB timeframe independently to see which performs best for your ticker universe.",
    ],
  },
  {
    id: 'risk-tuning',
    title: 'Risk Parameter Tuning Guide',
    dashboard: 'Backtesting',
    icon: 'shield',
    difficulty: 'Advanced',
    color: 'amber',
    brief: 'Optimizing max_consecutive_losses, max_drawdown, and trailing stop thresholds per ticker',
    significance: `Sentinel Edge's risk management operates at three levels: consecutive loss limits (momentum-based protection), drawdown percentage limits (capital preservation), and trailing stop profit thresholds (profit locking). These parameters directly control when the DecisionEngine overrides signal-based decisions with protective actions (EMERGENCY_EXIT, TIGHTEN_STOP). The defaults (3 consecutive losses, 10% max drawdown, 2% trailing threshold) are conservative baselines. Per-ticker overrides via the Ticker Config panel let you adapt risk profiles — volatile stocks like NVDA may need wider drawdown limits, while stable ETFs like SPY can use tighter stops. The relationship between these three parameters determines your strategy's risk/reward profile.`,
    interpretation: `Use the Backtesting dashboard to test parameter combinations. The key metrics to watch: (1) Win rate vs. max drawdown tradeoff — tighter stops increase win rate but may exit profitable trades early. (2) Monte Carlo probability of profit — this should be >60% for viable parameter sets. (3) The equity curve shape — smooth upward curves indicate good risk management, while sharp drops followed by recovery suggest the drawdown limit is set too high. Compare backtest results across different parameter sets for the same ticker and timeframe.`,
    keyInsight: 'Use Monte Carlo with ≥1000 simulations to validate that your parameter set is robust across different market conditions.',
    bestPractices: [
      "Start with backtesting: run the same symbol with 3, 5, and 7 consecutive loss limits and compare.",
      "Set max_drawdown_pct relative to the ticker's typical ATR — for high-ATR stocks, use 15-20%; for low-ATR, use 5-10%.",
      "The trailing stop threshold should be at least 2x the typical slippage + commission.",
      "Never set consecutive_losses below 2 — it causes excessive whipsawing.",
      "Use Monte Carlo with ≥1000 simulations to validate that your parameter set is robust across different market conditions, not just the specific historical period.",
    ],
  },
  {
    id: 'circuit-breaker',
    title: 'Circuit Breaker & Pulse Failover',
    dashboard: 'System Health',
    icon: 'shield-off',
    difficulty: 'Intermediate',
    color: 'red',
    brief: 'Understanding the circuit breaker pattern protecting broker communication',
    significance: `The PulseClient uses a circuit breaker pattern to protect against cascading failures when communicating with the Sentinel Pulse broker service. The circuit has three states: CLOSED (normal operation, requests flow through), OPEN (after 5 consecutive failures, all requests are blocked and queued for 60 seconds), and HALF_OPEN (after the 60s cooldown, a single probe request tests if Pulse is back). Failed decisions during OPEN state are automatically enqueued in the retry queue with priority ordering — EMERGENCY_EXIT has highest priority, followed by BUY, then HOLD. The circuit breaker prevents a single broker outage from cascading into system-wide failure.`,
    interpretation: `On the System Health dashboard, the Circuit Breaker panel shows the current state for each provider. Green = CLOSED (healthy), Yellow = HALF_OPEN (testing recovery), Red = OPEN (blocked). When the circuit is OPEN, you'll see queued decisions in the retry queue. The retry queue depth shows how many decisions are waiting. If you see frequent OPEN states, investigate the provider's API status page. The circuit breaker auto-recovers, but persistent failures may indicate a configuration issue.`,
    keyInsight: 'The retry queue preserves decision priority — EMERGENCY_EXIT decisions always get processed first after a broker recovers.',
    bestPractices: [
      "Monitor circuit breaker state changes — frequent transitions to OPEN suggest provider issues that need investigation.",
      "Use the retry queue depth as a leading indicator: growing depth means broker communication is degraded.",
      "When circuit opens, decisions are preserved but delayed. Check the decision feed for timing impact.",
      "The circuit breaker is automatic — you cannot manually override it, but you can switch primary providers in the Ticker Config.",
      "After a circuit transition to OPEN, expect 60-90 seconds of elevated latency as the retry queue drains.",
    ],
  },
];

const colorClasses = {
  blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: 'text-blue-400' },
  emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', icon: 'text-emerald-400' },
  amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', icon: 'text-amber-400' },
  red: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', icon: 'text-red-400' },
};

const difficultyColors = {
  Advanced: 'bg-purple-500/20 text-purple-400',
  Intermediate: 'bg-blue-500/20 text-blue-400',
};

const getIcon = (iconName: string, className: string) => {
  switch (iconName) {
    case 'zap': return <Zap className={className} />;
    case 'target': return <Target className={className} />;
    case 'shield': return <Shield className={className} />;
    case 'shield-off': return <ShieldOff className={className} />;
    default: return <BookOpen className={className} />;
  }
};

export const TutorialsDashboard: React.FC = () => {
  const [expandedTutorial, setExpandedTutorial] = useState<string>('');

  const expanded = TUTORIALS.find(t => t.id === expandedTutorial);

  if (expanded) {
    const colors = colorClasses[expanded.color];
    
    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
        {/* Back button */}
        <button
          onClick={() => setExpandedTutorial('')}
          className="flex items-center text-sm font-semibold text-gray-400 hover:text-white transition-colors mb-6"
        >
          <ChevronRight className="rotate-180 mr-2" size={16} />
          Back to all tutorials
        </button>

        {/* Header */}
        <div className="bg-gray-800 p-6 md:p-8 rounded-xl border border-gray-700 shadow-md mb-6">
          <div className="flex items-center mb-4">
            <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${colors.bg} ${colors.text} mr-2`}>
              {expanded.dashboard}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${difficultyColors[expanded.difficulty]}`}>
              {expanded.difficulty}
            </span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white">{expanded.title}</h2>
          <p className="text-base md:text-lg text-gray-400 mt-4">{expanded.brief}</p>
        </div>

        {/* Why This Matters */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 shadow-md mb-6 overflow-hidden">
          <div className="flex items-center p-4 border-b border-gray-700 bg-gray-900/50">
            <BookOpen size={20} className="text-blue-400 mr-3" />
            <h3 className="text-lg font-bold text-white">Why This Matters</h3>
          </div>
          <div className="p-6">
            <p className="text-gray-300 leading-relaxed">{expanded.significance}</p>
          </div>
        </div>

        {/* Reading the Dashboard */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 shadow-md mb-6 overflow-hidden">
          <div className="flex items-center p-4 border-b border-gray-700 bg-gray-900/50">
            <Target size={20} className="text-emerald-400 mr-3" />
            <h3 className="text-lg font-bold text-white">Reading the Dashboard</h3>
          </div>
          <div className="p-6">
            <p className="text-gray-300 leading-relaxed mb-4">{expanded.interpretation}</p>
            <div className="flex items-start bg-yellow-500/10 border border-yellow-500/20 p-4 rounded-lg">
              <Lightbulb size={18} className="text-yellow-400 mr-2 shrink-0 mt-0.5" />
              <div>
                <strong className="text-yellow-200">Key Insight: </strong>
                <span className="text-yellow-100">{expanded.keyInsight}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Best Practices */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 shadow-md mb-8 overflow-hidden">
          <div className="flex items-center p-4 border-b border-gray-700 bg-gray-900/50">
            <Shield size={20} className="text-amber-400 mr-3" />
            <h3 className="text-lg font-bold text-white">Best Practices</h3>
          </div>
          <div className="p-6 flex flex-col">
            {expanded.bestPractices.map((practice, idx) => (
              <div key={idx} className="flex items-start bg-gray-900/30 p-4 rounded-lg border border-gray-800 mb-3 last:mb-0">
                <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center mr-3 shrink-0 mt-0.5">
                  <span className="text-emerald-400 text-xs">✓</span>
                </div>
                <span className="text-gray-300 leading-relaxed">{practice}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Grid view
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-gray-800 p-8 rounded-xl border border-gray-700 shadow-md mb-8">
        <BookOpen size={32} className="text-blue-500 mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Sentinel Edge Learning Center</h2>
        <p className="text-gray-400 max-w-3xl">
          In-depth guides for intermediate to advanced users on core Sentinel Edge concepts. 
          Each tutorial covers a key system component with practical interpretation guidance and optimization best practices.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {TUTORIALS.map((tutorial) => {
          const colors = colorClasses[tutorial.color];
          return (
            <button
              key={tutorial.id}
              onClick={() => setExpandedTutorial(tutorial.id)}
              className={`text-left bg-gray-800 p-6 rounded-xl border ${colors.border} shadow-md hover:bg-gray-750 transition-all group`}
            >
              <div className="flex items-start mb-4">
                <div className={`p-3 rounded-xl ${colors.bg} mr-4`}>
                  {getIcon(tutorial.icon, `h-8 w-8 ${colors.icon}`)}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${colors.bg} ${colors.text}`}>
                      {tutorial.dashboard}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${difficultyColors[tutorial.difficulty]}`}>
                      {tutorial.difficulty}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">
                    {tutorial.title}
                  </h3>
                </div>
              </div>
              <p className="text-gray-400 text-sm">{tutorial.brief}</p>
              <div className="flex items-center text-blue-400 text-sm font-medium mt-4">
                View tutorial <ChevronRight size={16} className="ml-1" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default TutorialsDashboard;
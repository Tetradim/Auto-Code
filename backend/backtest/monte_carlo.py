"""Monte Carlo Simulation Engine - Phase 7"""
import logging
import numpy as np
from typing import Dict, List
import pandas as pd


logger = logging.getLogger(__name__)


class MonteCarloEngine:
    """Engine for Monte Carlo probabilistic simulations."""
    
    def __init__(self):
        logger.info("MonteCarloEngine initialized")


    async def run_simulation(
        self, 
        base_results: dict, 
        num_simulations: int = 1000, 
        volatility_multiplier: float = 1.0
    ):
        """
        Run Monte Carlo on top of a real backtest to simulate thousands of possible outcomes.
        
        Args:
            base_results: Results from a backtest run
            num_simulations: Number of Monte Carlo simulations to run
            volatility_multiplier: Multiply the observed volatility (1.0 = real, 1.5 = 50% more volatile)
        """
        if not base_results.get("trades"):
            return {"error": "No trades in base backtest"}


        trades = base_results["trades"]
        returns = [t["pnl_pct"] / 100 for t in trades]
        
        initial_capital = base_results.get("initial_capital", 10000.0)


        mean_return = np.mean(returns)
        std_return = np.std(returns) * volatility_multiplier


        simulated_final_equities = []
        win_rates = []
        max_drawdowns = []


        for _ in range(num_simulations):
            # Randomly sample trades with variation
            sim_returns = np.random.normal(mean_return, std_return, len(trades))
            equity = initial_capital
            equity_curve = [equity]
            peak = equity


            for r in sim_returns:
                equity *= (1 + r)
                equity_curve.append(equity)
                peak = max(peak, equity)


            final_equity = equity_curve[-1]
            simulated_final_equities.append(final_equity)


            # Stats
            win_rates.append(sum(1 for r in sim_returns if r > 0) / len(sim_returns) * 100)
            dd = max((peak - min(equity_curve)) / peak * 100, 0) if peak > 0 else 0
            max_drawdowns.append(dd)


        return {
            "simulations": num_simulations,
            "base_return_pct": base_results.get("total_return_pct", 0),
            "mean_final_equity": round(float(np.mean(simulated_final_equities)), 2),
            "median_final_equity": round(float(np.median(simulated_final_equities)), 2),
            "worst_case_equity": round(float(np.percentile(simulated_final_equities, 5)), 2),   # 5th percentile
            "best_case_equity": round(float(np.percentile(simulated_final_equities, 95)), 2),
            "mean_win_rate": round(float(np.mean(win_rates)), 1),
            "mean_max_drawdown": round(float(np.mean(max_drawdowns)), 2),
            "probability_of_profit": round(
                sum(1 for e in simulated_final_equities if e > initial_capital) / num_simulations * 100, 
                1
            )
        }
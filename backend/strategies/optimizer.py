"""Parameter Auto-Optimizer - Phase 8"""
import logging
from itertools import product
from typing import Dict, List


logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """Grid search optimizer for strategy parameters."""
    
    def __init__(self, backtest_engine):
        self.backtest_engine = backtest_engine


    async def optimize(
        self, 
        symbol: str, 
        param_grid: Dict[str, List], 
        start_date: str, 
        end_date: str,
        initial_capital: float = 10000.0
    ) -> Dict:
        """Grid search over parameter combinations to find best performing params."""
        
        # Calculate total combinations
        keys = list(param_grid.keys())
        total_combinations = 1
        for values in param_grid.values():
            total_combinations *= len(values)
        
        logger.info(
            f"Starting optimization for {symbol} with {total_combinations} combinations"
        )


        best_score = -999
        best_params = None
        best_results = None
        all_results = []


        # Generate all combinations
        for values in product(*param_grid.values()):
            params = dict(zip(keys, values))
            
            try:
                # Run backtest with these params
                # Note: Wire in actual params to decision engine
                results = await self.backtest_engine.run_backtest(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    **params
                )
                
                if "error" in results:
                    continue
                
                # Calculate optimization score
                mc = results.get("monte_carlo", {})
                return_pct = results.get("total_return_pct", 0)
                profit_prob = mc.get("probability_of_profit", 0)
                win_rate = results.get("win_rate", 0)
                
                # Combined score: return + profit probability + win rate
                score = return_pct + profit_prob + (win_rate * 0.3)
                
                all_results.append({
                    "params": params,
                    "score": round(score, 2),
                    "results": results
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_results = results
                    
            except Exception as e:
                logger.warning(f"Optimization iteration failed: {e}")
                continue


        logger.info(
            f"✅ Optimization complete. Best params: {best_params} | Score: {best_score}"
        )
        
        return {
            "best_params": best_params,
            "best_score": round(best_score, 2),
            "best_results": best_results,
            "total_combinations": total_combinations,
            "all_results": sorted(
                all_results, 
                key=lambda x: x["score"], 
                reverse=True
            )[:10]  # Top 10
        }
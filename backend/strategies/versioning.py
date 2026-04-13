"""Strategy Versioning & Auto-Optimization - Phase 8"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class StrategyVersionManager:
    """Manager for strategy version history and performance tracking."""
    
    def __init__(self, db=None):
        self.db = db
        self.versions = {}  # In-memory if no DB
        logger.info("StrategyVersionManager initialized")


    async def save_version(
        self, 
        strategy_name: str, 
        params: Dict[str, Any], 
        backtest_results: Dict
    ) -> Dict:
        """Save a new strategy version with its performance."""
        version = {
            "version_id": f"{strategy_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "strategy_name": strategy_name,
            "parameters": params,
            "backtest_results": backtest_results,
            "created_at": datetime.utcnow().isoformat(),
            "performance_score": self._calculate_score(backtest_results)
        }
        
        # Store in memory or DB
        if self.db:
            await self.db.strategy_versions.insert_one(version)
        else:
            if strategy_name not in self.versions:
                self.versions[strategy_name] = []
            self.versions[strategy_name].append(version)
        
        logger.info(f"✅ Saved new strategy version: {version['version_id']}")
        return version


    def _calculate_score(self, results: Dict) -> float:
        """Composite score: return, winrate, drawdown penalty"""
        if not results.get("total_return_pct"):
            return 0.0
        
        return_pct = results.get("total_return_pct", 0)
        win_rate = results.get("win_rate", 0)
        max_dd = results.get("max_drawdown_pct", 0)
        
        # Weighted scoring: 60% return, 30% win rate, 40% penalty for drawdown
        score = return_pct * 0.6 + win_rate * 0.3 - max_dd * 0.4
        return round(max(score, 0), 2)


    async def get_best_version(self, strategy_name: str) -> Optional[Dict]:
        """Get the best performing version of a strategy."""
        versions = self.versions.get(strategy_name, [])
        
        if not versions:
            return None
        
        return max(versions, key=lambda v: v.get("performance_score", 0))


    async def get_version_history(self, strategy_name: str) -> list:
        """Get all versions of a strategy, sorted by performance."""
        versions = self.versions.get(strategy_name, [])
        return sorted(versions, key=lambda v: v.get("performance_score", 0), reverse=True)


    async def get_latest_version(self, strategy_name: str) -> Optional[Dict]:
        """Get the most recent version of a strategy."""
        versions = self.versions.get(strategy_name, [])
        
        if not versions:
            return None
        
        return versions[-1] if versions else None
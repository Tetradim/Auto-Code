"""
Correlation Matrix Analytics

With heatmap rendering and cross-chart synchronization:
- Correlation matrix computation
- Cluster detection
- Heatmap visualization data
- Real-time updates
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CorrelationNode:
    """Single correlation node"""
    symbol_x: str
    symbol_y: str
    correlation: float  # -1 to 1
    
    @property
    def strength(self) -> str:
        abs_corr = abs(self.correlation)
        if abs_corr > 0.7:
            return "strong"
        elif abs_corr > 0.4:
            return "moderate"
        else:
            return "weak"
    
    @property
    def is_positive(self) -> bool:
        return self.correlation > 0


@dataclass
class CorrelationCluster:
    """Detected cluster"""
    symbols: List[str]
    avg_correlation: float
    
    @property
    def size(self) -> int:
        return len(self.symbols)


class CorrelationMatrix:
    """Correlation matrix computation"""
    
    def __init__(self):
        self._matrix: Dict[str, Dict[str, float]] = {}
        self._returns: Dict[str, List[float]] = {}
        self._threshold = 0.5  # Clustering threshold
    
    def add_returns(self, symbol: str, returns: List[float]):
        """Add price returns"""
        self._returns[symbol] = returns
    
    def compute(self) -> Dict[str, Dict[str, float]]:
        """Compute full correlation matrix"""
        symbols = list(self._returns.keys())
        matrix = {}
        
        for sym_x in symbols:
            matrix[sym_x] = {}
            for sym_y in symbols:
                if sym_x == sym_y:
                    matrix[sym_x][sym_y] = 1.0
                else:
                    corr = self._correlation(
                        self._returns.get(sym_x, []),
                        self._returns.get(sym_y, [])
                    )
                    matrix[sym_x][sym_y] = corr
        
        self._matrix = matrix
        return matrix
    
    def _correlation(self, returns_x: List[float], returns_y: List[float]) -> float:
        """Pearson correlation"""
        if len(returns_x) < 2 or len(returns_y) < 2:
            return 0.0
        
        min_len = min(len(returns_x), len(returns_y))
        x = returns_x[:min_len]
        y = returns_y[:min_len]
        
        # Means
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        
        # Covariance and std
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / min_len
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / min_len)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / min_len)
        
        if std_x == 0 or std_y == 0:
            return 0.0
        
        return cov / (std_x * std_y)
    
    def get_clusters(self, threshold: float = 0.5) -> List[CorrelationCluster]:
        """Detect clusters"""
        if not self._matrix:
            self.compute()
        
        self._threshold = threshold
        clusters = []
        used = set()
        
        for symbol in self._matrix:
            if symbol in used:
                continue
            
            # Find all correlated symbols
            cluster_symbols = [symbol]
            used.add(symbol)
            
            for other, corr in self._matrix[symbol].items():
                if abs(corr) >= threshold and other not in used:
                    cluster_symbols.append(other)
                    used.add(other)
            
            if len(cluster_symbols) > 1:
                avg = sum(
                    self._matrix[s][t] 
                    for s in cluster_symbols 
                    for t in cluster_symbols
                ) / (len(cluster_symbols) ** 2)
                
                clusters.append(CorrelationCluster(
                    symbols=cluster_symbols,
                    avg_correlation=avg
                ))
        
        return clusters
    
    def get_heatmap_data(
        self,
        symbols: List[str]
    ) -> Tuple[List[str], List[str], List[List[float]]]:
        """Get heatmap-ready data"""
        x_labels = symbols
        y_labels = symbols
        z_values = []
        
        if not self._matrix:
            self.compute()
        
        for sym_x in symbols:
            row = []
            for sym_y in symbols:
                row.append(self._matrix.get(sym_x, {}).get(sym_y, 0.0))
            z_values.append(row)
        
        return x_labels, y_labels, z_values
    
    def get_top_pairs(
        self,
        limit: int = 10,
        include_negative: bool = True
    ) -> List[Dict]:
        """Get most correlated pairs"""
        if not self._matrix:
            self.compute()
        
        pairs = []
        for sym_x in self._matrix:
            for sym_y, corr in self._matrix[sym_x].items():
                if sym_x < sym_y:  # Avoid duplicates
                    if include_negative or corr > 0:
                        pairs.append({
                            "symbol_x": sym_x,
                            "symbol_y": sym_y,
                            "correlation": corr,
                            "strength": "strong" if abs(corr) > 0.7 else "moderate"
                        })
        
        pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)
        return pairs[:limit]
    
    def get_isolated_symbols(self, threshold: float = 0.3) -> List[str]:
        """Get symbols with low correlation to others"""
        if not self._matrix:
            self.compute()
        
        isolated = []
        for symbol in self._matrix:
            avg_corr = sum(abs(c) for c in self._matrix[symbol].values()) / len(self._matrix)
            if avg_corr < threshold:
                isolated.append(symbol)
        
        return isolated


_correlation_matrix = CorrelationMatrix()


def get_correlation_matrix() -> CorrelationMatrix:
    """Get correlation matrix singleton"""
    return _correlation_matrix

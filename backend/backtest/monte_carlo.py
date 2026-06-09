"""Monte Carlo risk simulation for backtest trade results.

The engine intentionally uses only the Python standard library so the risk
math can be tested even in minimal local environments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
import os
from pathlib import Path
import random
from statistics import mean, median, pstdev
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4


SUPPORTED_METHODS = {"bootstrap", "shuffle", "normal", "block_bootstrap"}


@dataclass
class MonteCarloSettings:
    enabled: bool = True
    num_simulations: int = 1000
    method: str = "bootstrap"
    volatility_multiplier: float = 1.0
    confidence_level: float = 0.95
    random_seed: Optional[int] = None
    include_paths: bool = True
    saved_charts: bool = True
    chart_output_dir: Optional[str] = None
    sample_path_count: int = 25
    histogram_bins: int = 20
    ruin_threshold_pct: float = 50.0
    block_size: int = 5

    def normalized(self) -> "MonteCarloSettings":
        return MonteCarloSettings(
            enabled=bool(self.enabled),
            num_simulations=max(1, min(int(self.num_simulations), 50000)),
            method=self.method if self.method in SUPPORTED_METHODS else "bootstrap",
            volatility_multiplier=max(0.0, float(self.volatility_multiplier)),
            confidence_level=min(0.999, max(0.50, float(self.confidence_level))),
            random_seed=self.random_seed,
            include_paths=bool(self.include_paths),
            saved_charts=bool(self.saved_charts),
            chart_output_dir=self.chart_output_dir,
            sample_path_count=max(0, min(int(self.sample_path_count), 200)),
            histogram_bins=max(5, min(int(self.histogram_bins), 100)),
            ruin_threshold_pct=max(0.0, min(float(self.ruin_threshold_pct), 100.0)),
            block_size=max(1, int(self.block_size)),
        )


class MonteCarloEngine:
    """Run probabilistic simulations over realized backtest trade returns."""

    async def run_simulation(
        self,
        base_results: Dict[str, Any],
        settings: MonteCarloSettings | int | None = None,
        volatility_multiplier: Optional[float] = None,
    ) -> Dict[str, Any]:
        settings = self._coerce_settings(settings, volatility_multiplier).normalized()
        if not settings.enabled:
            return {"status": "disabled", "settings": asdict(settings)}

        returns = _extract_trade_returns(base_results.get("trades", []))
        if not returns:
            return {
                "status": "error",
                "error": "No trades in base backtest",
                "settings": asdict(settings),
            }

        symbol = str(base_results.get("symbol") or "UNKNOWN").upper()
        initial_capital = float(base_results.get("initial_capital") or base_results.get("initial_equity") or 10000.0)
        rng = random.Random(settings.random_seed)

        final_equities: List[float] = []
        final_return_pct: List[float] = []
        max_drawdowns: List[float] = []
        all_paths: List[List[float]] = []
        sample_paths: List[Dict[str, Any]] = []

        for index in range(settings.num_simulations):
            sampled_returns = self._sample_returns(returns, settings, rng)
            path = _equity_path(initial_capital, sampled_returns)
            drawdown = _max_drawdown_pct(path)
            final_equity = path[-1]

            final_equities.append(final_equity)
            final_return_pct.append((final_equity / initial_capital - 1.0) * 100)
            max_drawdowns.append(drawdown)
            all_paths.append(path)

            if settings.include_paths and len(sample_paths) < settings.sample_path_count:
                sample_paths.append(
                    {
                        "simulation": index + 1,
                        "points": _chart_points(path),
                    }
                )

        lower_tail = 1.0 - settings.confidence_level
        lower_equity = _percentile(final_equities, lower_tail)
        upper_equity = _percentile(final_equities, settings.confidence_level)
        lower_return = _percentile(final_return_pct, lower_tail)
        tail_equities = [value for value in final_equities if value <= lower_equity]
        tail_returns = [value for value in final_return_pct if value <= lower_return]

        confidence_band = _confidence_band(all_paths, lower_tail, settings.confidence_level)
        histogram = _histogram(final_equities, settings.histogram_bins)
        drawdown_distribution = _histogram(max_drawdowns, settings.histogram_bins)

        result: Dict[str, Any] = {
            "status": "completed",
            "symbol": symbol,
            "simulations": settings.num_simulations,
            "method": settings.method,
            "confidence_level": settings.confidence_level,
            "random_seed": settings.random_seed,
            "settings": asdict(settings),
            "base_return_pct": round(float(base_results.get("total_return_pct", 0.0)), 4),
            "mean_final_equity": round(mean(final_equities), 2),
            "median_final_equity": round(median(final_equities), 2),
            "worst_case_equity": round(lower_equity, 2),
            "best_case_equity": round(upper_equity, 2),
            "probability_of_profit": round(_ratio(final_equities, lambda value: value > initial_capital) * 100, 2),
            "probability_of_ruin": round(
                _ratio(final_equities, lambda value: value <= initial_capital * (1 - settings.ruin_threshold_pct / 100)) * 100,
                2,
            ),
            "mean_max_drawdown": round(mean(max_drawdowns), 2),
            "max_drawdown_percentiles": {
                "p50": round(_percentile(max_drawdowns, 0.50), 2),
                "p95": round(_percentile(max_drawdowns, 0.95), 2),
                "p99": round(_percentile(max_drawdowns, 0.99), 2),
            },
            "final_equity_percentiles": {
                "p05": round(_percentile(final_equities, 0.05), 2),
                "p25": round(_percentile(final_equities, 0.25), 2),
                "p50": round(_percentile(final_equities, 0.50), 2),
                "p75": round(_percentile(final_equities, 0.75), 2),
                "p95": round(_percentile(final_equities, 0.95), 2),
            },
            "value_at_risk": round(max(0.0, initial_capital - lower_equity), 2),
            "value_at_risk_pct": round(max(0.0, -lower_return), 2),
            "conditional_value_at_risk": round(max(0.0, initial_capital - mean(tail_equities or [lower_equity])), 2),
            "conditional_value_at_risk_pct": round(max(0.0, -mean(tail_returns or [lower_return])), 2),
            "final_equity_histogram": histogram,
            "drawdown_distribution": drawdown_distribution,
            "confidence_band": confidence_band,
            "sample_paths": sample_paths,
        }

        if settings.saved_charts:
            result["saved_chart_set"] = self._save_chart_set(result, settings)

        return result

    def _coerce_settings(
        self,
        settings: MonteCarloSettings | int | None,
        volatility_multiplier: Optional[float],
    ) -> MonteCarloSettings:
        if isinstance(settings, MonteCarloSettings):
            if volatility_multiplier is not None:
                settings.volatility_multiplier = volatility_multiplier
            return settings
        if isinstance(settings, int):
            return MonteCarloSettings(
                num_simulations=settings,
                volatility_multiplier=volatility_multiplier if volatility_multiplier is not None else 1.0,
            )
        return MonteCarloSettings(
            volatility_multiplier=volatility_multiplier if volatility_multiplier is not None else 1.0,
        )

    def _sample_returns(
        self,
        returns: List[float],
        settings: MonteCarloSettings,
        rng: random.Random,
    ) -> List[float]:
        trade_count = len(returns)
        if settings.method == "shuffle":
            shuffled = list(returns)
            rng.shuffle(shuffled)
            return shuffled
        if settings.method == "normal":
            center = mean(returns)
            spread = pstdev(returns) * settings.volatility_multiplier
            return [rng.gauss(center, spread) for _ in range(trade_count)]
        if settings.method == "block_bootstrap":
            sampled: List[float] = []
            while len(sampled) < trade_count:
                start = rng.randrange(0, trade_count)
                block = [returns[(start + offset) % trade_count] for offset in range(settings.block_size)]
                sampled.extend(block)
            return sampled[:trade_count]
        return [rng.choice(returns) * settings.volatility_multiplier for _ in range(trade_count)]

    def _save_chart_set(self, result: Dict[str, Any], settings: MonteCarloSettings) -> Dict[str, Any]:
        run_id = f"mc_{result['symbol'].lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        output_root = Path(
            settings.chart_output_dir
            or os.getenv("SENTINEL_EDGE_MONTE_CARLO_CHART_DIR", "data/monte_carlo_charts")
        )
        output_dir = output_root / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        chart_payloads = {
            "final_equity_histogram": result["final_equity_histogram"],
            "drawdown_distribution": result["drawdown_distribution"],
            "confidence_band": result["confidence_band"],
            "sample_paths": result["sample_paths"],
        }
        charts = []
        for chart_name, data in chart_payloads.items():
            path = output_dir / f"{chart_name}.json"
            payload = {
                "run_id": run_id,
                "symbol": result["symbol"],
                "chart": chart_name,
                "created_at": datetime.utcnow().isoformat(),
                "settings": result["settings"],
                "data": data,
            }
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            charts.append({"name": chart_name, "path": str(path.resolve())})

        manifest_path = output_dir / "manifest.json"
        manifest = {
            "run_id": run_id,
            "symbol": result["symbol"],
            "created_at": datetime.utcnow().isoformat(),
            "chart_count": len(charts),
            "charts": charts,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {**manifest, "manifest_path": str(manifest_path.resolve())}


def _extract_trade_returns(trades: Iterable[Dict[str, Any]]) -> List[float]:
    returns = []
    for trade in trades:
        if "pnl_pct" not in trade or trade["pnl_pct"] is None:
            continue
        returns.append(float(trade["pnl_pct"]) / 100.0)
    return returns


def _equity_path(initial_capital: float, returns: Iterable[float]) -> List[float]:
    equity = initial_capital
    path = [round(equity, 2)]
    for trade_return in returns:
        equity *= 1.0 + trade_return
        path.append(round(equity, 2))
    return path


def _max_drawdown_pct(path: List[float]) -> float:
    peak = path[0] if path else 0.0
    max_drawdown = 0.0
    for value in path:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100)
    return max_drawdown


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = max(0.0, min(1.0, percentile)) * (len(ordered) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _confidence_band(paths: List[List[float]], lower: float, upper: float) -> List[Dict[str, float]]:
    if not paths:
        return []
    steps = max(len(path) for path in paths)
    band = []
    for step in range(steps):
        values = [path[step] for path in paths if step < len(path)]
        band.append(
            {
                "step": step,
                "lower": round(_percentile(values, lower), 2),
                "median": round(_percentile(values, 0.50), 2),
                "upper": round(_percentile(values, upper), 2),
            }
        )
    return band


def _histogram(values: List[float], bins: int) -> List[Dict[str, float]]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if low == high:
        return [{"bin_start": round(low, 2), "bin_end": round(high, 2), "count": len(values)}]

    width = (high - low) / bins
    counts = [0 for _ in range(bins)]
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    return [
        {
            "bin_start": round(low + index * width, 2),
            "bin_end": round(low + (index + 1) * width, 2),
            "count": count,
        }
        for index, count in enumerate(counts)
    ]


def _chart_points(path: List[float]) -> List[Dict[str, float]]:
    return [{"step": index, "equity": value} for index, value in enumerate(path)]


def _ratio(values: List[float], predicate) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if predicate(value)) / len(values)

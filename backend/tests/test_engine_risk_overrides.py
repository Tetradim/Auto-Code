from backend.engine import Decision, DecisionEngine
from backend.signals import TrendDirection


def test_decision_engine_uses_per_ticker_max_drawdown_override():
    engine = DecisionEngine()
    decision = engine.decide(
        symbol="SPY",
        trend=TrendDirection.BULLISH,
        signal_strength=6.0,
        current_drawdown=4.0,
        has_position=True,
        max_drawdown_pct=3.0,
    )
    assert decision == Decision.EMERGENCY_EXIT


def test_decision_engine_uses_per_ticker_trailing_profit_override():
    engine = DecisionEngine()
    decision = engine.decide(
        symbol="SPY",
        trend=TrendDirection.BULLISH,
        signal_strength=1.0,
        pnl_pct=1.0,
        has_position=True,
        trailing_enabled=False,
        trailing_stop_profit_threshold=0.8,
    )
    assert decision == Decision.ENABLE_TRAILING_STOP

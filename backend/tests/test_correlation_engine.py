"""
Iteration 4 — Correlation Engine Tests
Tests for CorrelationEngine, /api/correlation endpoint, Signal dataclass,
breadth calculations, and regression of all previous endpoints.
"""
import pytest
import requests
import os
import sys

# Add backend directory to path for direct module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ── /api/correlation endpoint ─────────────────────────────────────────────────

class TestCorrelationEndpoint:
    """Tests for GET /api/correlation"""

    def test_correlation_returns_200(self):
        resp = requests.get(f"{BASE_URL}/api/correlation")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_correlation_response_has_all_fields(self):
        """Must return clusters, breadth, latest"""
        resp = requests.get(f"{BASE_URL}/api/correlation")
        data = resp.json()
        assert "clusters" in data, "Missing 'clusters' field"
        assert "breadth" in data, "Missing 'breadth' field"
        assert "latest" in data, "Missing 'latest' field"

    def test_correlation_latest_null_when_no_clusters(self):
        """When no clusters fired, latest must be null/None"""
        resp = requests.get(f"{BASE_URL}/api/correlation")
        data = resp.json()
        # In live mode with markets closed, there should be no clusters
        # latest should be null
        assert data["latest"] is None, f"Expected latest=null but got {data['latest']}"

    def test_correlation_clusters_is_list(self):
        resp = requests.get(f"{BASE_URL}/api/correlation")
        data = resp.json()
        assert isinstance(data["clusters"], list), "clusters must be a list"

    def test_correlation_breadth_has_required_fields(self):
        """breadth must have bullish, bearish, neutral, total, bullish_pct, bearish_pct"""
        resp = requests.get(f"{BASE_URL}/api/correlation")
        breadth = resp.json()["breadth"]
        for field in ["bullish", "bearish", "neutral", "total", "bullish_pct", "bearish_pct"]:
            assert field in breadth, f"breadth missing '{field}'"

    def test_correlation_breadth_total_minimum_one(self):
        """total must be >= 1 — protects against division by zero"""
        resp = requests.get(f"{BASE_URL}/api/correlation")
        breadth = resp.json()["breadth"]
        assert breadth["total"] >= 1, f"breadth.total={breadth['total']} violates minimum-1 protection"

    def test_correlation_breadth_pct_values_are_floats(self):
        resp = requests.get(f"{BASE_URL}/api/correlation")
        breadth = resp.json()["breadth"]
        assert isinstance(breadth["bullish_pct"], (int, float)), "bullish_pct must be numeric"
        assert isinstance(breadth["bearish_pct"], (int, float)), "bearish_pct must be numeric"

    def test_correlation_breadth_pct_in_valid_range(self):
        resp = requests.get(f"{BASE_URL}/api/correlation")
        breadth = resp.json()["breadth"]
        assert 0.0 <= breadth["bullish_pct"] <= 100.0
        assert 0.0 <= breadth["bearish_pct"] <= 100.0


# ── CorrelationEngine unit tests (direct import) ──────────────────────────────

class TestCorrelationEngineUnit:
    """Direct unit tests for CorrelationEngine class"""

    def _make_engine(self):
        from correlation import CorrelationEngine
        return CorrelationEngine(db=None, window_sec=120, min_symbols=3, cooldown_sec=300)

    def test_engine_instantiates_with_correct_window(self):
        eng = self._make_engine()
        assert eng.window_sec == 120, f"Expected window_sec=120, got {eng.window_sec}"

    def test_engine_instantiates_with_correct_cooldown(self):
        eng = self._make_engine()
        assert eng.cooldown_sec == 300, f"Expected cooldown_sec=300, got {eng.cooldown_sec}"

    def test_engine_instantiates_with_correct_min_symbols(self):
        eng = self._make_engine()
        assert eng.min_symbols == 3

    def test_signal_dataclass_importable(self):
        """Signal dataclass must exist in correlation module"""
        from correlation import Signal
        s = Signal(action="BUY", confidence=0.9)
        assert s.action == "BUY"
        assert s.confidence == 0.9

    def test_signal_dataclass_default_confidence(self):
        from correlation import Signal
        s = Signal(action="SELL")
        assert s.confidence == 1.0

    def test_get_latest_cluster_returns_none_when_empty(self):
        eng = self._make_engine()
        assert eng.get_latest_cluster() is None

    def test_get_recent_clusters_returns_empty_list_initially(self):
        eng = self._make_engine()
        assert eng.get_recent_clusters() == []

    def test_get_current_breadth_no_division_by_zero(self):
        """get_current_breadth must never divide by zero even with no events"""
        eng = self._make_engine()
        breadth = eng.get_current_breadth()
        assert breadth["total"] >= 1, "total should be >= 1"
        assert isinstance(breadth["bullish_pct"], float)
        assert isinstance(breadth["bearish_pct"], float)

    def test_record_signal_obj_wrapper(self):
        """record_signal_obj must accept Signal dataclass"""
        import asyncio
        from correlation import CorrelationEngine, Signal
        eng = CorrelationEngine(db=None, window_sec=120, min_symbols=3, cooldown_sec=300)
        sig = Signal(action="BUY", confidence=0.8)
        # Should not raise
        result = asyncio.run(eng.record_signal_obj("AAPL", sig))
        # No cluster since only 1 symbol
        assert result is None


class TestCorrelationEngineClusterDetection:
    """Cluster detection logic tests"""

    def _make_engine(self):
        from correlation import CorrelationEngine
        return CorrelationEngine(db=None, window_sec=120, min_symbols=3, cooldown_sec=300)

    def test_no_cluster_with_fewer_than_min_symbols(self):
        import asyncio
        eng = self._make_engine()
        # Only 2 bullish signals — below min_symbols=3
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        assert eng.get_latest_cluster() is None

    def test_bullish_cluster_detected_with_three_symbols(self):
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        cluster = asyncio.run(eng.record_signal("NVDA", "BUY", 0.85))
        assert cluster is not None, "Should detect cluster with 3 bullish signals"
        assert cluster["direction"] == "BULLISH"
        assert cluster["count"] == 3

    def test_cluster_has_strength_field(self):
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        cluster = asyncio.run(eng.record_signal("NVDA", "BUY", 0.85))
        assert cluster is not None
        assert "strength" in cluster, "Cluster must have 'strength' field"
        assert 0.0 <= cluster["strength"] <= 1.0

    def test_cluster_has_score_field_for_backward_compat(self):
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        cluster = asyncio.run(eng.record_signal("NVDA", "BUY", 0.85))
        assert cluster is not None
        assert "score" in cluster, "Cluster must have 'score' field for backward compat"

    def test_cluster_has_timestamp_field(self):
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        cluster = asyncio.run(eng.record_signal("NVDA", "BUY", 0.85))
        assert cluster is not None
        assert "timestamp" in cluster

    def test_cluster_has_symbols_field(self):
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        cluster = asyncio.run(eng.record_signal("NVDA", "BUY", 0.85))
        assert cluster is not None
        assert "symbols" in cluster
        assert isinstance(cluster["symbols"], list)
        assert len(cluster["symbols"]) == 3

    def test_strength_normalized_count_over_8(self):
        """strength = min(1.0, count/8)"""
        import asyncio
        eng = self._make_engine()
        # 4 symbols → strength = 4/8 = 0.5
        for sym in ["SPY", "QQQ", "NVDA", "AAPL"]:
            asyncio.run(eng.record_signal(sym, "BUY", 0.9))
        cluster = eng.get_latest_cluster()
        assert cluster is not None
        assert cluster["strength"] == 0.5, f"Expected 0.5, got {cluster['strength']}"

    def test_strength_capped_at_1_for_8_plus_symbols(self):
        """strength = min(1.0, count/8) — should cap at 1.0 for 8+ symbols"""
        import asyncio
        eng = self._make_engine()
        for i, sym in enumerate(["SPY", "QQQ", "NVDA", "AAPL", "TSLA", "AMZN", "GOOGL", "META"]):
            asyncio.run(eng.record_signal(sym, "BUY", 0.9))
        cluster = eng.get_latest_cluster()
        assert cluster is not None
        assert cluster["strength"] == 1.0, f"Expected 1.0, got {cluster['strength']}"

    def test_bearish_cluster_detected_with_sell(self):
        """SELL actions should trigger BEARISH cluster"""
        import asyncio
        eng = self._make_engine()
        for sym in ["SPY", "QQQ", "NVDA"]:
            asyncio.run(eng.record_signal(sym, "SELL", 0.9))
        cluster = eng.get_latest_cluster()
        assert cluster is not None
        assert cluster["direction"] == "BEARISH"

    def test_stop_buying_treated_as_bearish(self):
        """STOP_BUYING is treated as bearish signal"""
        import asyncio
        from correlation import _BEARISH_ACTIONS
        assert "STOP_BUYING" in _BEARISH_ACTIONS, "STOP_BUYING must be in _BEARISH_ACTIONS"

    def test_sell_treated_as_bearish(self):
        """SELL is treated as bearish signal"""
        import asyncio
        from correlation import _BEARISH_ACTIONS
        assert "SELL" in _BEARISH_ACTIONS

    def test_cooldown_prevents_second_cluster(self):
        """Per-direction cooldown should prevent immediate second cluster"""
        import asyncio
        eng = self._make_engine()
        # First cluster
        for sym in ["SPY", "QQQ", "NVDA"]:
            asyncio.run(eng.record_signal(sym, "BUY", 0.9))
        first = eng.get_latest_cluster()
        assert first is not None

        # Immediately try to fire another (cooldown still active)
        for sym in ["SPY", "QQQ", "NVDA"]:
            asyncio.run(eng.record_signal(sym, "BUY", 0.9))
        clusters = eng.get_recent_clusters()
        # Should still be only 1 cluster due to cooldown
        assert len(clusters) == 1, f"Cooldown not working: {len(clusters)} clusters"

    def test_recent_clusters_contains_latest(self):
        import asyncio
        eng = self._make_engine()
        for sym in ["SPY", "QQQ", "NVDA"]:
            asyncio.run(eng.record_signal(sym, "BUY", 0.9))
        latest = eng.get_latest_cluster()
        recent = eng.get_recent_clusters()
        assert latest is not None
        assert len(recent) >= 1
        assert recent[0] == latest, "get_latest_cluster should match first element of get_recent_clusters"

    def test_breadth_counts_bullish_correctly(self):
        """get_current_breadth should count BUY signals as bullish"""
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "BUY", 0.9))
        asyncio.run(eng.record_signal("QQQ", "BUY", 0.8))
        breadth = eng.get_current_breadth()
        assert breadth["bullish"] == 2, f"Expected 2 bullish, got {breadth['bullish']}"

    def test_breadth_counts_bearish_correctly(self):
        """get_current_breadth should count SELL signals as bearish"""
        import asyncio
        eng = self._make_engine()
        asyncio.run(eng.record_signal("SPY", "SELL", 0.9))
        asyncio.run(eng.record_signal("QQQ", "SELL", 0.8))
        breadth = eng.get_current_breadth()
        assert breadth["bearish"] == 2, f"Expected 2 bearish, got {breadth['bearish']}"


# ── Regression: /api/health still works ──────────────────────────────────────

class TestRegressionHealth:
    def test_health_still_healthy(self):
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ── Regression: /api/decisions still returns correct structure ────────────────

class TestRegressionDecisions:
    def test_decisions_returns_200(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        assert resp.status_code == 200

    def test_decisions_has_decisions_and_count(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        assert "decisions" in data
        assert "count" in data

    def test_decisions_list_is_list(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        assert isinstance(resp.json()["decisions"], list)


# ── Regression: /api/tickers ─────────────────────────────────────────────────

class TestRegressionTickers:
    def test_tickers_returns_200(self):
        resp = requests.get(f"{BASE_URL}/api/tickers")
        assert resp.status_code == 200

    def test_tickers_has_tickers_and_count(self):
        data = requests.get(f"{BASE_URL}/api/tickers").json()
        assert "tickers" in data
        assert "count" in data

    def test_tickers_has_default_four(self):
        data = requests.get(f"{BASE_URL}/api/tickers").json()
        # Default tickers: SPY, QQQ, NVDA, AAPL
        assert data["count"] >= 4, f"Expected >=4 default tickers, got {data['count']}"

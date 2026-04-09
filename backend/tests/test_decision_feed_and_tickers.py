"""
Sentinel Edge - Iteration 3: Decision Feed & Add/Remove Ticker Tests
Tests:
  - GET /api/decisions returns correct structure
  - POST /api/tickers/{symbol} adds ticker
  - DELETE /api/tickers/{symbol} removes ticker
  - Re-add ticker after removal
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ── /api/decisions ─────────────────────────────────────────────────────────────

class TestDecisionsFeed:
    """GET /api/decisions endpoint tests"""

    def test_decisions_returns_200(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        assert resp.status_code == 200

    def test_decisions_response_has_decisions_key(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        assert "decisions" in data, f"Missing 'decisions' key. Got: {data}"

    def test_decisions_response_has_count_key(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        assert "count" in data, f"Missing 'count' key. Got: {data}"

    def test_decisions_list_is_list(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        assert isinstance(data["decisions"], list), f"Expected list, got {type(data['decisions'])}"

    def test_decisions_count_matches_list_length(self):
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        assert data["count"] == len(data["decisions"]), \
            f"count={data['count']} does not match len(decisions)={len(data['decisions'])}"

    def test_decisions_in_normal_mode_returns_empty_or_valid(self):
        """Markets closed: all signals are HOLD, so decisions should be empty list with count 0"""
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        # In normal mode (markets closed), decisions list should be empty
        # but if market was open earlier, it could have entries
        assert data["count"] >= 0, "Count must be non-negative"
        assert isinstance(data["decisions"], list), "Decisions must be a list"

    def test_decisions_entries_have_required_fields_if_present(self):
        """If decisions exist, each must have required fields"""
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        required_fields = ["symbol", "decision", "signal_strength", "trend", "confidence", "price", "timestamp"]
        for entry in data["decisions"]:
            for field in required_fields:
                assert field in entry, f"Decision entry missing '{field}' field: {entry}"

    def test_decisions_max_50_entries(self):
        """API should return at most 50 decisions"""
        resp = requests.get(f"{BASE_URL}/api/decisions")
        data = resp.json()
        assert len(data["decisions"]) <= 50, f"Too many decisions: {len(data['decisions'])} (max 50)"


# ── /api/tickers Add/Remove ────────────────────────────────────────────────────

class TestTickerManagement:
    """POST /api/tickers/{symbol} and DELETE /api/tickers/{symbol}"""

    TEST_SYMBOL = "TEST_TST"

    def setup_method(self):
        """Ensure the test ticker is removed before each test"""
        requests.delete(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.2)

    def teardown_method(self):
        """Cleanup after each test"""
        requests.delete(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")

    def test_add_ticker_returns_200(self):
        resp = requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_add_ticker_response_message(self):
        resp = requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        data = resp.json()
        assert "message" in data, f"Missing 'message' in response: {data}"

    def test_add_ticker_appears_in_tickers_list(self):
        requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.3)
        resp = requests.get(f"{BASE_URL}/api/tickers")
        data = resp.json()
        symbols = [t["symbol"] if isinstance(t, dict) else t for t in data["tickers"]]
        assert self.TEST_SYMBOL in symbols, \
            f"Added ticker {self.TEST_SYMBOL} not found in tickers: {symbols}"

    def test_remove_ticker_returns_200(self):
        # First add it
        requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.2)
        resp = requests.delete(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_remove_ticker_disappears_from_list(self):
        # Add
        requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.2)
        # Remove
        requests.delete(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.2)
        # Verify removed
        resp = requests.get(f"{BASE_URL}/api/tickers")
        data = resp.json()
        symbols = [t["symbol"] if isinstance(t, dict) else t for t in data["tickers"]]
        assert self.TEST_SYMBOL not in symbols, \
            f"Ticker {self.TEST_SYMBOL} still in list after removal: {symbols}"

    def test_readd_ticker_after_removal(self):
        """Verify re-adding works after removal"""
        # Add
        requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.2)
        # Remove
        requests.delete(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        time.sleep(0.2)
        # Re-add
        resp = requests.post(f"{BASE_URL}/api/tickers/{self.TEST_SYMBOL}")
        assert resp.status_code == 200, f"Re-add failed: {resp.text}"
        time.sleep(0.3)
        # Verify re-added
        resp2 = requests.get(f"{BASE_URL}/api/tickers")
        data = resp2.json()
        symbols = [t["symbol"] if isinstance(t, dict) else t for t in data["tickers"]]
        assert self.TEST_SYMBOL in symbols, \
            f"Re-added ticker {self.TEST_SYMBOL} not found: {symbols}"


# ── Add TSLA specifically ────────────────────────────────────────────────────

class TestAddTsla:
    """Verify TSLA can be added (specific test case from requirements)"""

    def teardown_method(self):
        """Remove TSLA after test"""
        requests.delete(f"{BASE_URL}/api/tickers/TSLA")

    def test_add_tsla_ticker(self):
        resp = requests.post(f"{BASE_URL}/api/tickers/TSLA")
        assert resp.status_code == 200
        data = resp.json()
        assert "TSLA" in data.get("message", ""), f"Expected TSLA in message: {data}"

    def test_remove_tsla_ticker(self):
        requests.post(f"{BASE_URL}/api/tickers/TSLA")
        time.sleep(0.2)
        resp = requests.delete(f"{BASE_URL}/api/tickers/TSLA")
        assert resp.status_code == 200
        data = resp.json()
        assert "TSLA" in data.get("message", ""), f"Expected TSLA in message: {data}"

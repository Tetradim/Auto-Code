"""Static checks for Pulse circuit breaker alert runbook coverage."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTS = ROOT / "prometheus" / "alerts" / "sentinel_edge_rules.yml"
RUNBOOK = ROOT / "docs" / "runbooks" / "pulse-circuit-breaker.md"


class PulseCircuitBreakerRunbookStaticTests(unittest.TestCase):
    def test_pulse_circuit_breaker_alerts_link_runbook(self):
        text = ALERTS.read_text(encoding="utf-8")

        self.assertIn("CircuitBreakerOpen", text)
        self.assertIn("CircuitBreakerHalfOpen", text)
        self.assertIn('broker_circuit_state{broker_id="pulse"} == 2', text)
        self.assertIn('broker_circuit_state{broker_id="pulse"} == 1', text)
        self.assertEqual(text.count('runbook_url: "docs/runbooks/pulse-circuit-breaker.md"'), 2)

    def test_pulse_circuit_breaker_runbook_is_actionable(self):
        self.assertTrue(RUNBOOK.exists(), "Pulse circuit breaker runbook is missing")

        text = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("CircuitBreakerOpen", text)
        self.assertIn("CircuitBreakerHalfOpen", text)
        self.assertIn("broker_circuit_state", text)
        self.assertIn("/api/pulse/health", text)
        self.assertIn("/api/automation", text)
        self.assertIn("backend/pulse_client.py", text)
        self.assertIn("retry queue", text)


if __name__ == "__main__":
    unittest.main()

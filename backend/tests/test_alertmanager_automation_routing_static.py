"""Static checks for automation alert routing safety."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTMANAGER = ROOT / "prometheus" / "alertmanager.yml"


class AlertmanagerAutomationRoutingStaticTests(unittest.TestCase):
    def test_automation_route_precedes_broad_critical_override(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")

        automation_route = text.index('component = "automation"')
        critical_route = text.index('severity = "critical"')
        self.assertLess(automation_route, critical_route)

    def test_automation_route_does_not_trigger_pulse_override(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        route_start = text.index('component = "automation"')
        route_end = text.index('severity = "critical"')
        route = text[route_start:route_end]

        self.assertIn("receiver: 'automation-alerts'", route)
        self.assertIn("continue: false", route)
        self.assertNotIn("pulse-override", route)

    def test_automation_receiver_notifies_humans_and_general_webhook(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        receiver_start = text.index("- name: 'automation-alerts'")
        receiver_end = text.index("- name: 'pulse-override'")
        receiver = text[receiver_start:receiver_end]

        self.assertIn("slack_configs:", receiver)
        self.assertIn("channel: '#trading-alerts'", receiver)
        self.assertIn("Runbook: {{ .Annotations.runbook_url }}", receiver)
        self.assertIn("url: 'http://sentinel-edge:8001/api/webhook/general'", receiver)
        self.assertNotIn("url: 'http://sentinel-edge:8001/api/webhook/pulse-override'", receiver)

    def test_all_route_receivers_remain_defined(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        route_block = text[text.index("route:"):text.index("receivers:")]
        receiver_block = text[text.index("receivers:"):text.index("inhibit_rules:")]

        referenced_receivers = set(re.findall(r"^\s+receiver: '([^']+)'", route_block, re.MULTILINE))
        defined_receivers = set(re.findall(r"^\s+- name: '([^']+)'", receiver_block, re.MULTILINE))

        self.assertTrue(referenced_receivers)
        self.assertTrue(referenced_receivers.issubset(defined_receivers))


if __name__ == "__main__":
    unittest.main()

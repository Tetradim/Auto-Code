"""Static checks for Alertmanager routing of Pulse API SLO alerts."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
ALERTMANAGER = ROOT / "prometheus" / "alertmanager.yml"


class AlertmanagerSloRoutingStaticTests(unittest.TestCase):
    def test_pulse_api_slo_route_precedes_broad_critical_override(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")

        slo_route = text.index('slo = "pulse-api-availability"')
        critical_route = text.index('severity = "critical"')
        self.assertLess(slo_route, critical_route)

    def test_pulse_api_slo_route_does_not_trigger_pulse_override(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        route_start = text.index('slo = "pulse-api-availability"')
        route_end = text.index('severity = "critical"')
        route = text[route_start:route_end]

        self.assertIn("receiver: 'broker-slo-alerts'", route)
        self.assertIn("continue: false", route)
        self.assertNotIn("pulse-override", route)

    def test_broker_slo_receiver_notifies_humans_and_general_webhook(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        receiver_start = text.index("- name: 'broker-slo-alerts'")
        receiver_end = text.index("- name: 'trading-team'")
        receiver = text[receiver_start:receiver_end]

        self.assertIn("slack_configs:", receiver)
        self.assertIn("channel: '#trading-alerts'", receiver)
        self.assertIn("Runbook: {{ .Annotations.runbook_url }}", receiver)
        self.assertIn("url: 'http://sentinel-edge:8001/api/webhook/general'", receiver)
        self.assertNotIn("url: 'http://sentinel-edge:8001/api/webhook/pulse-override'", receiver)

    def test_fast_burn_inhibits_duplicate_slow_burn_notifications(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        rule_start = text.index('alertname = "PulseApiSloFastBurn"')
        rule_end = text.index("# Suppress warnings when a critical fires", rule_start)
        rule = text[rule_start:rule_end]

        self.assertIn('slo = "pulse-api-availability"', rule)
        self.assertIn('alertname = "PulseApiSloSlowBurn"', rule)
        self.assertIn("equal: ['slo']", rule)
        self.assertNotIn("severity = \"critical\"", rule)

    def test_all_route_receivers_are_defined_once(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        route_block = text[text.index("route:"):text.index("receivers:")]
        receiver_block = text[text.index("receivers:"):text.index("inhibit_rules:")]

        referenced_receivers = set(re.findall(r"^\s+receiver: '([^']+)'", route_block, re.MULTILINE))
        defined_receivers = re.findall(r"^\s+- name: '([^']+)'", receiver_block, re.MULTILINE)

        self.assertTrue(referenced_receivers)
        self.assertEqual(sorted(set(defined_receivers)), sorted(defined_receivers))
        self.assertTrue(referenced_receivers.issubset(set(defined_receivers)))

    def test_each_receiver_has_a_notification_integration(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        receiver_block = text[text.index("receivers:"):text.index("inhibit_rules:")]
        receiver_names = re.findall(r"^\s+- name: '([^']+)'", receiver_block, re.MULTILINE)

        for index, name in enumerate(receiver_names):
            start = receiver_block.index(f"- name: '{name}'")
            if index + 1 < len(receiver_names):
                end = receiver_block.index(f"- name: '{receiver_names[index + 1]}'")
            else:
                end = len(receiver_block)
            definition = receiver_block[start:end]

            self.assertRegex(
                definition,
                r"(webhook_configs|slack_configs|telegram_configs):",
                msg=f"{name} receiver has no notification integration",
            )

    def test_route_time_interval_references_are_defined(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        route_block = text[text.index("route:"):text.index("receivers:")]
        interval_block = text[text.rindex("mute_time_intervals:"):]

        referenced_intervals = set()
        for section_name in ("mute_time_intervals", "active_time_intervals"):
            for match in re.finditer(rf"{section_name}:\n((?:\s+-.+\n)+)", route_block):
                referenced_intervals.update(
                    item.strip().lstrip("-").strip("'\" ")
                    for item in match.group(1).splitlines()
                )

        defined_intervals = set(
            re.findall(r"^\s+- name: '([^']+)'", interval_block, re.MULTILINE)
        )

        self.assertTrue(referenced_intervals)
        self.assertTrue(referenced_intervals.issubset(defined_intervals))

    def test_defined_time_intervals_have_time_specs(self):
        text = ALERTMANAGER.read_text(encoding="utf-8")
        interval_block = text[text.rindex("mute_time_intervals:"):]
        interval_names = re.findall(r"^\s+- name: '([^']+)'", interval_block, re.MULTILINE)

        for index, name in enumerate(interval_names):
            start = interval_block.index(f"- name: '{name}'")
            if index + 1 < len(interval_names):
                end = interval_block.index(f"- name: '{interval_names[index + 1]}'")
            else:
                end = len(interval_block)
            definition = interval_block[start:end]

            self.assertIn("time_intervals:", definition)
            self.assertRegex(definition, r"(times|weekdays|location):")


if __name__ == "__main__":
    unittest.main()

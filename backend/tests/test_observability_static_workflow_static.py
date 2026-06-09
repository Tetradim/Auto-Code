"""Static checks for the observability-only CI workflow."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "observability-static.yml"


class ObservabilityStaticWorkflowTests(unittest.TestCase):
    def test_workflow_runs_for_observability_config_changes(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: Observability Static Checks", text)
        self.assertIn("pull_request:", text)
        self.assertIn("'prometheus/**'", text)
        self.assertIn("'grafana/dashboards/**'", text)
        self.assertIn("'docs/runbooks/**'", text)
        self.assertIn("'backend/tests/test_*static.py'", text)

    def test_workflow_runs_static_tests_and_dashboard_json_validation(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("runs-on: ubuntu-latest", text)
        self.assertIn("actions/setup-python@v5", text)
        self.assertIn('python -m unittest discover -s backend/tests -p "test_*static.py"', text)
        self.assertIn("python -m json.tool grafana/dashboards/broker_health.json", text)
        self.assertIn("python -m json.tool grafana/dashboards/frontend-experience.json", text)
        self.assertIn("> /dev/null", text)

    def test_workflow_runs_prometheus_and_alertmanager_validators(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("Validate Prometheus config and rules", text)
        self.assertIn("--entrypoint promtool", text)
        self.assertIn("prom/prometheus:latest", text)
        self.assertIn("check config /etc/prometheus/prometheus.yml", text)
        self.assertIn("check rules /etc/prometheus/rules.yml /etc/prometheus/alerts/sentinel_edge_rules.yml", text)
        self.assertIn("Validate Alertmanager config", text)
        self.assertIn("--entrypoint amtool", text)
        self.assertIn("prom/alertmanager:latest", text)
        self.assertIn("check-config /etc/alertmanager/alertmanager.yml", text)
        self.assertIn("https://hooks.slack.com/services/T000/B000/XXXXXXXXXXXXXXXXXXXXXXXX", text)


if __name__ == "__main__":
    unittest.main()

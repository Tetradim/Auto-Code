"""Static checks for container liveness health checks."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ROOT_DOCKERFILE = ROOT / "Dockerfile"
BACKEND_DOCKERFILE = ROOT / "backend" / "Dockerfile"
COMPOSE = ROOT / "docker-compose.yml"


class ContainerLivenessHealthcheckStaticTests(unittest.TestCase):
    def test_dockerfiles_probe_dependency_free_liveness(self):
        for path in (ROOT_DOCKERFILE, BACKEND_DOCKERFILE):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                self.assertIn("HEALTHCHECK", text)
                self.assertIn("http://localhost:8001/api/live", text)
                self.assertIn("--start-period=40s", text)
                self.assertNotIn("http://localhost:8001/api/health", text)

    def test_compose_edge_healthcheck_uses_liveness(self):
        text = COMPOSE.read_text(encoding="utf-8")

        self.assertIn('healthcheck:', text)
        self.assertIn('"http://localhost:8001/api/live"', text)
        self.assertIn("start_period: 40s", text)
        self.assertNotIn('"http://localhost:8001/api/health"', text)


if __name__ == "__main__":
    unittest.main()

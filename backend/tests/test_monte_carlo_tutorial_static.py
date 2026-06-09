"""Static checks for the user-facing Monte Carlo tutorial."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class MonteCarloTutorialStaticTests(unittest.TestCase):
    def test_learning_center_includes_monte_carlo_customization_guide(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("monte-carlo-lab", text)
        self.assertIn("Monte Carlo Lab", text)
        self.assertIn("Monte Carlo Settings", text)
        self.assertIn("Saved Chart Bundle", text)
        self.assertIn("probability_of_profit", text)
        self.assertIn("value_at_risk", text)
        self.assertIn("conditional_value_at_risk", text)
        self.assertIn("sample paths", text)
        self.assertIn("random seed", text)
        self.assertIn("block bootstrap", text)


if __name__ == "__main__":
    unittest.main()

"""Static checks for Learning Center no-results recovery actions."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialEmptyStateRecoveryStaticTests(unittest.TestCase):
    def test_no_results_state_offers_targeted_recovery_actions(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("clearSearchOnly", text)
        self.assertIn("Clear search only", text)
        self.assertIn("Search all guides", text)
        self.assertIn("Show in-progress guides", text)
        self.assertIn("Reset all filters", text)
        self.assertIn("activeLearningPath.id !== 'all-guides'", text)
        self.assertIn("setSelectedLearningPath('all-guides')", text)
        self.assertIn("applyTutorialFocusPreset('resume')", text)
        self.assertIn("onClick={clearFilters}", text)


if __name__ == "__main__":
    unittest.main()

"""Static checks for Learning Center search and filter controls."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialsFindabilityStaticTests(unittest.TestCase):
    def test_learning_center_has_search_and_filters(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("Search tutorials", text)
        self.assertIn("selectedDashboard", text)
        self.assertIn("selectedDifficulty", text)
        self.assertIn("filteredTutorials", text)
        self.assertIn("dashboardOptions", text)
        self.assertIn("difficultyOptions", text)
        self.assertIn("No tutorials match", text)
        self.assertIn("Clear filters", text)


if __name__ == "__main__":
    unittest.main()

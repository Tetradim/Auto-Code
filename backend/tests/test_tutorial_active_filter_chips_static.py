"""Static checks for active Learning Center filter chips."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialActiveFilterChipsStaticTests(unittest.TestCase):
    def test_learning_center_shows_removable_active_filters(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("activeFilterChips", text)
        self.assertIn("Active filters", text)
        self.assertIn("Remove filter", text)
        self.assertIn("Search:", text)
        self.assertIn("Path:", text)
        self.assertIn("Dashboard:", text)
        self.assertIn("Difficulty:", text)
        self.assertIn("Incomplete only", text)
        self.assertIn("Saved only", text)
        self.assertIn("Notes only", text)


if __name__ == "__main__":
    unittest.main()

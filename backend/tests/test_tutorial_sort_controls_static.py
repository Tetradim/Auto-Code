"""Static checks for Learning Center sort controls."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialSortControlsStaticTests(unittest.TestCase):
    def test_learning_center_can_sort_filtered_guides(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TutorialSortOption", text)
        self.assertIn("sortOptions", text)
        self.assertIn("selectedSort", text)
        self.assertIn("sortedTutorials", text)
        self.assertIn("Sort tutorials", text)
        self.assertIn("Path order", text)
        self.assertIn("Shortest first", text)
        self.assertIn("Longest first", text)
        self.assertIn("Incomplete first", text)
        self.assertIn("Saved first", text)
        self.assertIn("Notes first", text)


if __name__ == "__main__":
    unittest.main()

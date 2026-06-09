"""Static checks for Learning Center path navigation inside tutorial detail pages."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialPathNavigationStaticTests(unittest.TestCase):
    def test_tutorial_detail_has_path_aware_previous_next_navigation(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("expandedPathIndex", text)
        self.assertIn("previousPathTutorial", text)
        self.assertIn("nextPathTutorial", text)
        self.assertIn("expandedPathProgress", text)
        self.assertIn("Path position", text)
        self.assertIn("step {expandedPathIndex + 1} of {activePathTutorials.length}", text)
        self.assertIn("Previous guide", text)
        self.assertIn("Next guide", text)
        self.assertIn("Start of path", text)
        self.assertIn("Path complete", text)
        self.assertIn("setExpandedTutorial(previousPathTutorial.id)", text)
        self.assertIn("setExpandedTutorial(nextPathTutorial.id)", text)


if __name__ == "__main__":
    unittest.main()

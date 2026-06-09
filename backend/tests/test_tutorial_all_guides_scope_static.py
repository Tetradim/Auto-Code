"""Static checks for the Learning Center all-guides scope."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialAllGuidesScopeStaticTests(unittest.TestCase):
    def test_learning_center_can_show_all_guides(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("all-guides", text)
        self.assertIn("All Guides", text)
        self.assertIn("Search across every Learning Center guide", text)
        self.assertIn("activePathTutorials", text)
        self.assertIn("TUTORIALS.map((tutorial) => tutorial.id)", text)
        self.assertIn("path guides shown", text)


if __name__ == "__main__":
    unittest.main()

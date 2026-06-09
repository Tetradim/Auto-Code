"""Static checks for Learning Center display mode controls."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialDisplayModeStaticTests(unittest.TestCase):
    def test_learning_center_has_detailed_and_compact_modes(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TutorialDisplayMode", text)
        self.assertIn("selectedDisplayMode", text)
        self.assertIn("Detailed cards", text)
        self.assertIn("Compact list", text)
        self.assertIn("LayoutGrid", text)
        self.assertIn("List", text)
        self.assertIn("selectedDisplayMode === 'compact'", text)
        self.assertIn("selectedDisplayMode === 'compact' ? 'grid grid-cols-1 gap-3'", text)


if __name__ == "__main__":
    unittest.main()

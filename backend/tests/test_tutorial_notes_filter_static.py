"""Static checks for filtering tutorials with personal notes."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialNotesFilterStaticTests(unittest.TestCase):
    def test_learning_center_can_filter_to_guides_with_notes(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("showNotesOnly", text)
        self.assertIn("matchesNotes", text)
        self.assertIn("hasNote", text)
        self.assertIn("Show notes only", text)
        self.assertIn("Notes", text)
        self.assertIn("setShowNotesOnly(false)", text)


if __name__ == "__main__":
    unittest.main()

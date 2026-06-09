"""Static checks for Learning Center personal tutorial notes."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialPersonalNotesStaticTests(unittest.TestCase):
    def test_tutorial_detail_has_personal_notes(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TUTORIAL_NOTES_STORAGE_KEY", text)
        self.assertIn("loadTutorialNotes", text)
        self.assertIn("tutorialNotes", text)
        self.assertIn("updateTutorialNote", text)
        self.assertIn("Personal notes", text)
        self.assertIn("Saved locally", text)
        self.assertIn("Add your setup notes", text)
        self.assertIn("guides with notes", text)


if __name__ == "__main__":
    unittest.main()

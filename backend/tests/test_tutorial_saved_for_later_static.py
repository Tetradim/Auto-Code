"""Static checks for Learning Center saved-for-later controls."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialSavedForLaterStaticTests(unittest.TestCase):
    def test_learning_center_has_saved_for_later_controls(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("SAVED_TUTORIALS_STORAGE_KEY", text)
        self.assertIn("savedTutorialIds", text)
        self.assertIn("savedTutorialSet", text)
        self.assertIn("toggleSavedTutorial", text)
        self.assertIn("Save for later", text)
        self.assertIn("Saved for later", text)
        self.assertIn("Show saved only", text)
        self.assertIn("saved for later", text)


if __name__ == "__main__":
    unittest.main()

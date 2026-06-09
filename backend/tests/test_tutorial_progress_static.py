"""Static checks for Learning Center completion tracking."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialProgressStaticTests(unittest.TestCase):
    def test_learning_center_tracks_completion_progress(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("COMPLETED_TUTORIALS_STORAGE_KEY", text)
        self.assertIn("completedTutorialIds", text)
        self.assertIn("completionPercent", text)
        self.assertIn("toggleTutorialCompletion", text)
        self.assertIn("Show incomplete only", text)
        self.assertIn("Mark complete", text)
        self.assertIn("Marked complete", text)
        self.assertIn("guides complete", text)


if __name__ == "__main__":
    unittest.main()

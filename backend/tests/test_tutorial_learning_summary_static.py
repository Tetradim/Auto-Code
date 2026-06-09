"""Static checks for the Learning Center progress summary strip."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialLearningSummaryStaticTests(unittest.TestCase):
    def test_learning_center_home_shows_progress_summary_and_next_action(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("totalPracticeActions", text)
        self.assertIn("checkedPracticeActionCount", text)
        self.assertIn("practiceActionPercent", text)
        self.assertIn("nextPracticeTutorial", text)
        self.assertIn("Guides complete", text)
        self.assertIn("Action checklist", text)
        self.assertIn("Saved context", text)
        self.assertIn("Next action", text)
        self.assertIn("setExpandedTutorial(nextPracticeTutorial.id)", text)
        self.assertIn("style={{ width: `${practiceActionPercent}%` }}", text)


if __name__ == "__main__":
    unittest.main()

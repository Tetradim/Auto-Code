"""Static checks for per-guide Learning Center action progress meters."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialActionProgressCardsStaticTests(unittest.TestCase):
    def test_learning_center_cards_show_action_progress(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("getTutorialActionProgress", text)
        self.assertIn("actionProgress", text)
        self.assertGreaterEqual(text.count("Action progress"), 2)
        self.assertIn("{actionProgress.checked}/{actionProgress.total}", text)
        self.assertIn("style={{ width: `${actionProgress.percent}%` }}", text)
        self.assertIn("getTutorialActionProgress(tutorial, tutorialPracticeChecks).checked", text)
        self.assertIn("const actionProgress = getTutorialActionProgress(tutorial, tutorialPracticeChecks);", text)


if __name__ == "__main__":
    unittest.main()

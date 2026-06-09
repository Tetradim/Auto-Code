"""Static checks for Learning Center practice checklist progress."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialPracticeChecklistStaticTests(unittest.TestCase):
    def test_best_practices_are_trackable_and_portable(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TUTORIAL_PRACTICE_CHECKS_STORAGE_KEY", text)
        self.assertIn("sanitizeTutorialPracticeChecks", text)
        self.assertIn("loadTutorialPracticeChecks", text)
        self.assertIn("tutorialPracticeChecks", text)
        self.assertIn("toggleTutorialPracticeCheck", text)
        self.assertIn("expandedPracticeChecks", text)
        self.assertIn("expandedPracticePercent", text)
        self.assertIn("actions checked", text)
        self.assertIn("% complete", text)
        self.assertIn('type="checkbox"', text)
        self.assertIn("checked={expandedPracticeChecks.has(idx)}", text)
        self.assertIn("toggleTutorialPracticeCheck(expanded.id, idx)", text)
        self.assertIn("tutorialPracticeChecks,", text)
        self.assertIn("setTutorialPracticeChecks(sanitizeTutorialPracticeChecks(parsed.tutorialPracticeChecks))", text)


if __name__ == "__main__":
    unittest.main()

"""Static checks for Learning Center best-practice checklist bulk actions."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialPracticeBulkActionsStaticTests(unittest.TestCase):
    def test_best_practice_checklist_has_bulk_complete_and_reset(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("completeTutorialPracticeChecklist", text)
        self.assertIn("clearTutorialPracticeChecklist", text)
        self.assertIn("Mark all done", text)
        self.assertIn("Reset actions", text)
        self.assertIn("tutorial.bestPractices.map((_, index) => index)", text)
        self.assertIn("completeTutorialPracticeChecklist(expanded)", text)
        self.assertIn("clearTutorialPracticeChecklist(expanded.id)", text)
        self.assertIn("disabled={expandedPracticeChecks.size === expanded.bestPractices.length}", text)
        self.assertIn("disabled={expandedPracticeChecks.size === 0}", text)


if __name__ == "__main__":
    unittest.main()

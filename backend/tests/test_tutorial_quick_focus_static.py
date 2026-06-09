"""Static checks for Learning Center quick focus presets."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialQuickFocusStaticTests(unittest.TestCase):
    def test_learning_center_has_one_click_focus_presets(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TutorialFocusPreset", text)
        self.assertIn("quickFocusOptions", text)
        self.assertIn("applyTutorialFocusPreset", text)
        self.assertIn("Quick focus", text)
        self.assertIn("Apply common Learning Center views with one click.", text)
        self.assertIn("Applies across all guides", text)
        self.assertIn("Resume", text)
        self.assertIn("Saved", text)
        self.assertIn("Notes", text)
        self.assertIn("Complete", text)
        self.assertIn("setSelectedLearningPath('all-guides')", text)
        self.assertIn("setSelectedStatusFilter('in-progress')", text)
        self.assertIn("setShowSavedOnly(true)", text)
        self.assertIn("setShowNotesOnly(true)", text)
        self.assertIn("setSelectedStatusFilter('complete')", text)
        self.assertIn("onClick={() => applyTutorialFocusPreset(option.id)}", text)


if __name__ == "__main__":
    unittest.main()

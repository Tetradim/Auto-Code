"""Static checks for Learning Center learning-state export/import."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialLearningStatePortabilityStaticTests(unittest.TestCase):
    def test_learning_center_can_export_and_import_learning_state(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("LEARNING_CENTER_EXPORT_VERSION", text)
        self.assertIn("learningStateFileInputRef", text)
        self.assertIn("exportLearningCenterState", text)
        self.assertIn("importLearningCenterState", text)
        self.assertIn("sanitizeTutorialIds", text)
        self.assertIn("sanitizeTutorialNotes", text)
        self.assertIn("Download learning data", text)
        self.assertIn("Import learning data", text)
        self.assertIn("learning-center-state", text)
        self.assertIn("importStatus", text)


if __name__ == "__main__":
    unittest.main()

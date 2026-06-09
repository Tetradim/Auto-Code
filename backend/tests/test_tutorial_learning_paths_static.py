"""Static checks for Learning Center guided learning paths."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialLearningPathsStaticTests(unittest.TestCase):
    def test_learning_center_has_guided_paths(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("LEARNING_PATHS", text)
        self.assertIn("selectedLearningPath", text)
        self.assertIn("activeLearningPath", text)
        self.assertIn("recommendedTutorial", text)
        self.assertIn("Recommended Learning Path", text)
        self.assertIn("Continue path", text)
        self.assertIn("Strategy Builder", text)
        self.assertIn("Risk Control", text)
        self.assertIn("Options Readiness", text)


if __name__ == "__main__":
    unittest.main()

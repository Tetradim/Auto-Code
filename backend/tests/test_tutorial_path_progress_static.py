"""Static checks for Learning Center path progress previews."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialPathProgressStaticTests(unittest.TestCase):
    def test_learning_paths_show_completion_and_remaining_time(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("getLearningPathProgress", text)
        self.assertIn("activePathProgress", text)
        self.assertIn("pathProgress", text)
        self.assertIn("remainingMinutes", text)
        self.assertIn("{activePathProgress.completed}/{activePathProgress.total} complete", text)
        self.assertIn("{activePathProgress.remainingMinutes} min remaining", text)
        self.assertIn("{pathProgress.completed}/{pathProgress.total} complete", text)
        self.assertIn("{pathProgress.remainingMinutes} min left", text)
        self.assertIn("style={{ width: `${pathProgress.percent}%` }}", text)


if __name__ == "__main__":
    unittest.main()

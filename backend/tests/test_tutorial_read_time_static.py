"""Static checks for Learning Center estimated read time labels."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialReadTimeStaticTests(unittest.TestCase):
    def test_learning_center_has_estimated_read_time(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("READING_WORDS_PER_MINUTE", text)
        self.assertIn("getTutorialWordCount", text)
        self.assertIn("getTutorialReadTimeMinutes", text)
        self.assertIn("getLearningPathReadTime", text)
        self.assertIn("min read", text)
        self.assertIn("path minutes", text)
        self.assertIn("Clock", text)


if __name__ == "__main__":
    unittest.main()

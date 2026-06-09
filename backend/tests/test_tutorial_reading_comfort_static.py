"""Static checks for Learning Center reading comfort controls."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialReadingComfortStaticTests(unittest.TestCase):
    def test_tutorial_detail_has_persistent_reading_comfort(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TutorialReadingMode", text)
        self.assertIn("readingModeOptions", text)
        self.assertIn("readingModeClasses", text)
        self.assertIn("TUTORIAL_READING_MODE_STORAGE_KEY", text)
        self.assertIn("loadTutorialReadingMode", text)
        self.assertIn("sanitizeTutorialReadingMode", text)
        self.assertIn("selectedReadingMode", text)
        self.assertIn("setSelectedReadingMode", text)
        self.assertIn("Reading comfort", text)
        self.assertIn("Tutorial reading comfort", text)
        self.assertIn("selectedReadingMode,", text)
        self.assertIn("setSelectedReadingMode(sanitizeTutorialReadingMode(parsed.selectedReadingMode))", text)
        self.assertIn("readingModeClass.panel", text)
        self.assertIn("readingModeClass.body", text)
        self.assertIn("readingModeClass.practice", text)


if __name__ == "__main__":
    unittest.main()

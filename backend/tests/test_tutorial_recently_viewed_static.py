"""Static checks for Learning Center recently viewed guides."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialRecentlyViewedStaticTests(unittest.TestCase):
    def test_learning_center_tracks_and_renders_recently_viewed_guides(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("RECENT_TUTORIALS_STORAGE_KEY", text)
        self.assertIn("loadRecentTutorialIds", text)
        self.assertIn("recentTutorialIds", text)
        self.assertIn("setRecentTutorialIds", text)
        self.assertIn("recentTutorials", text)
        self.assertIn("Recently viewed", text)
        self.assertIn("Clear recent", text)
        self.assertIn("recentTutorials.slice(0, 3)", text)
        self.assertIn("setRecentTutorialIds([])", text)
        self.assertIn("setRecentTutorialIds((current) => [", text)
        self.assertIn("].slice(0, 5))", text)
        self.assertIn("recentTutorialIds,", text)
        self.assertIn("setRecentTutorialIds(sanitizeTutorialIds(parsed.recentTutorialIds).slice(0, 5))", text)


if __name__ == "__main__":
    unittest.main()

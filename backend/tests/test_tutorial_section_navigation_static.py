"""Static checks for Learning Center tutorial section navigation."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialSectionNavigationStaticTests(unittest.TestCase):
    def test_tutorial_detail_has_section_navigation(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TUTORIAL_SECTION_LINKS", text)
        self.assertIn("On this page", text)
        self.assertIn("why-this-matters", text)
        self.assertIn("reading-the-dashboard", text)
        self.assertIn("best-practices", text)
        self.assertIn("Jump to", text)
        self.assertIn("href={`#${section.id}`}", text)


if __name__ == "__main__":
    unittest.main()

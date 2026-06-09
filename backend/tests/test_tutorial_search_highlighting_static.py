"""Static checks for Learning Center search term highlighting."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialSearchHighlightingStaticTests(unittest.TestCase):
    def test_learning_center_highlights_search_matches_without_html_injection(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("escapeRegExp", text)
        self.assertIn("getSearchHighlightParts", text)
        self.assertIn("renderHighlightedText", text)
        self.assertIn("<mark", text)
        self.assertIn("highlightQuery", text)
        self.assertIn("renderHighlightedText(expanded.significance, highlightQuery)", text)
        self.assertIn("renderHighlightedText(expanded.interpretation, highlightQuery)", text)
        self.assertIn("renderHighlightedText(expanded.keyInsight, highlightQuery)", text)
        self.assertIn("renderHighlightedText(tutorial.title, highlightQuery)", text)
        self.assertIn("renderHighlightedText(tutorial.brief, highlightQuery)", text)
        self.assertIn("renderHighlightedText(practice, highlightQuery)", text)
        self.assertNotIn("dangerouslySetInnerHTML", text)


if __name__ == "__main__":
    unittest.main()

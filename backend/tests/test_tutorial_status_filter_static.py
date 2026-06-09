"""Static checks for Learning Center status filters and badges."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
TUTORIALS = ROOT / "frontend" / "src" / "components" / "tutorials" / "TutorialsDashboard.tsx"


class TutorialStatusFilterStaticTests(unittest.TestCase):
    def test_learning_center_has_status_filter_and_badges(self):
        text = TUTORIALS.read_text(encoding="utf-8")

        self.assertIn("TutorialProgressStatus", text)
        self.assertIn("TutorialStatusFilter", text)
        self.assertIn("tutorialStatusMeta", text)
        self.assertIn("statusFilterOptions", text)
        self.assertIn("selectedStatusFilter", text)
        self.assertIn("setSelectedStatusFilter", text)
        self.assertIn("getTutorialProgressStatus", text)
        self.assertIn("Status filter", text)
        self.assertIn("All status", text)
        self.assertIn("Not started", text)
        self.assertIn("In progress", text)
        self.assertIn("matchesStatus", text)
        self.assertIn("Status: ${tutorialStatusMeta[selectedStatusFilter].label}", text)
        self.assertIn("statusMeta.classes", text)
        self.assertIn("statusMeta.label", text)
        self.assertIn("setSelectedStatusFilter('all')", text)


if __name__ == "__main__":
    unittest.main()

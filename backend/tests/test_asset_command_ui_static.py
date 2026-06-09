"""Static regressions for the Asset Command UI integration."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ASSET_COMMAND = ROOT / "frontend" / "src" / "components" / "asset-command" / "AssetCommandConsole.tsx"
ASSET_COMMAND_CSS = ROOT / "frontend" / "src" / "components" / "asset-command" / "AssetCommandConsole.css"
MARKET_COVERAGE = ROOT / "frontend" / "src" / "components" / "dashboards" / "MarketCoverage.tsx"


class AssetCommandUiStaticTests(unittest.TestCase):
    def test_pulse_startup_choice_is_available(self):
        text = ASSET_COMMAND.read_text(encoding="utf-8")

        self.assertIn("PulseStartupPanel", text)
        self.assertIn("Connect to Pulse", text)
        self.assertIn("Try Connecting", text)
        self.assertIn("Standalone Mode", text)
        self.assertIn("setShowPulseStartup(false)", text)

    def test_scheduler_control_is_disabled_when_backend_is_not_connected(self):
        text = ASSET_COMMAND.read_text(encoding="utf-8")

        self.assertIn("disabled={runtime.loading || !runtime.connected}", text)
        self.assertIn("aria-disabled={runtime.loading || !runtime.connected}", text)
        self.assertIn("if (runtime.loading || !runtime.connected) return", text)

    def test_market_coverage_only_suppresses_vite_html_fallback(self):
        text = MARKET_COVERAGE.read_text(encoding="utf-8")

        self.assertIn("isFrontendFallbackApiError", text)
        self.assertIn("Expected JSON response", text)
        self.assertIn("setMarketStatusMessage", text)
        self.assertIn("console.error('Failed to load markets:', error)", text)
        self.assertNotIn("if (!(error instanceof ApiError)) {\n        console.error('Failed to load markets:', error)", text)

    def test_mode_and_operations_controls_have_tab_semantics(self):
        text = ASSET_COMMAND.read_text(encoding="utf-8")

        self.assertIn('role="tab"', text)
        self.assertIn("aria-selected=", text)
        self.assertIn("aria-controls=", text)
        self.assertIn('role="tabpanel"', text)
        self.assertIn("onKeyDown", text)

    def test_reel_motion_honors_reduced_motion(self):
        css = ASSET_COMMAND_CSS.read_text(encoding="utf-8")

        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("animation: none", css)

    def test_metric_reels_report_rendered_count_and_scroll_slots(self):
        text = ASSET_COMMAND.read_text(encoding="utf-8")
        css = ASSET_COMMAND_CSS.read_text(encoding="utf-8")

        self.assertIn("availableCount={selected.metrics.length}", text)
        self.assertIn("availableCount: number", text)
        self.assertIn("{reels.length} of {availableCount} visible", text)
        self.assertNotIn("{visibleReels} visible", text)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("grid-auto-flow: column", css)
        self.assertIn("grid-auto-columns", css)


if __name__ == "__main__":
    unittest.main()

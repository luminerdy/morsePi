import re
import unittest
from pathlib import Path


class TouchScreensaverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.app_source = (cls.root / "static" / "app.js").read_text(encoding="utf-8")
        cls.css_source = (cls.root / "static" / "touch.css").read_text(encoding="utf-8")

    def test_idle_guess_reveal_and_reset_timing_match_spec(self):
        self.assertIn("const TOUCH_SCREENSAVER_IDLE_MS = 3 * 60 * 1000;", self.app_source)
        self.assertIn("const TOUCH_SCREENSAVER_GUESS_MS = 5 * 1000;", self.app_source)
        self.assertIn("const TOUCH_SCREENSAVER_REVEAL_MS = 3 * 1000;", self.app_source)
        self.assertIn("const TOUCH_OPERATOR_RESET_MS = 10 * 60 * 1000;", self.app_source)

    def test_recall_cycle_hides_then_reveals_the_character(self):
        self.assertIn('item.classList.remove("answer-visible")', self.app_source)
        self.assertIn('character.setAttribute("aria-hidden", "true")', self.app_source)
        self.assertIn('character.innerText = ""', self.app_source)
        self.assertIn("pendingCharacter = choice.character", self.app_source)
        self.assertIn("character.innerText = pendingCharacter", self.app_source)
        self.assertIn('item.classList.add("answer-visible")', self.app_source)
        self.assertIn('character.setAttribute("aria-hidden", "false")', self.app_source)
        self.assertIn("window.setTimeout(revealCharacter, screensaverGuessMs)", self.app_source)
        self.assertIn("window.setTimeout(beginRecallCycle, screensaverRevealMs)", self.app_source)

    def test_character_pool_is_limited_to_letters_and_numbers(self):
        self.assertIn('/^[A-Z0-9]$/.test(character)', self.app_source)
        for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            self.assertRegex(
                self.app_source,
                rf'"[.\-]+": "{character}"',
                msg=f"missing Morse mapping for {character}",
            )

    def test_screensaver_is_silent_and_keyer_wake_is_cleared(self):
        start = self.app_source.index("function initializeTouchIdleExperience()")
        end = self.app_source.index("function initializeMessageControls()")
        implementation = self.app_source[start:end]

        self.assertNotIn("/api/play", implementation)
        self.assertNotIn("prompt-led", implementation)
        self.assertIn('fetch("/clear-key", { method: "POST" })', implementation)
        self.assertIn("notePhysicalKey: wakeFromPhysicalKey", implementation)
        self.assertIn("event.stopImmediatePropagation()", implementation)

    def test_all_active_touch_pages_load_current_assets(self):
        templates = sorted((self.root / "templates").glob("touch_*.html"))
        self.assertGreater(len(templates), 10)

        for path in templates:
            source = path.read_text(encoding="utf-8")
            self.assertIn("/static/touch.css?v=20260830-1", source, path.name)
            if path.name == "touch_shutdown.html":
                self.assertNotIn("/static/app.js", source, path.name)
            else:
                self.assertIn("/static/app.js?v=20260825-1", source, path.name)

    def test_overlay_is_full_screen_and_safe_at_800_by_480(self):
        self.assertRegex(
            self.css_source,
            re.compile(r"\.touch-screensaver\s*\{[^}]*position:\s*fixed;[^}]*inset:\s*0;", re.DOTALL),
        )
        self.assertIn("background: #020305;", self.css_source)
        self.assertIn("width: min(360px, 70%);", self.css_source)
        self.assertIn(".touch-screensaver-item.answer-visible .touch-screensaver-character", self.css_source)
        self.assertNotIn("visibility 0s linear 0.35s", self.css_source)
        self.assertIn("height: 101px", self.css_source)
        self.assertIn(".touch-screensaver-morse .morse-mark", self.css_source)
        self.assertIn("background: #62d6d1", self.css_source)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css_source)
        self.assertIn("25 + Math.random() * 50", self.app_source)

    def test_cursor_is_hidden_throughout_touch_ui(self):
        self.assertRegex(
            self.css_source,
            re.compile(r"\.touch-ui\s*\{[^}]*cursor:\s*none;", re.DOTALL),
        )
        self.assertRegex(
            self.css_source,
            re.compile(r"\.touch-ui \*\s*\{[^}]*cursor:\s*none\s*!important;", re.DOTALL),
        )

    def test_shutdown_route_is_explicitly_excluded(self):
        self.assertIn(
            'window.location.pathname.startsWith("/touch/shutdown")',
            self.app_source,
        )


if __name__ == "__main__":
    unittest.main()

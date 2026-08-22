import re
import unittest
from pathlib import Path

from morse_display import morse_accessible_label, morse_visual


class MorseDisplayTests(unittest.TestCase):
    def test_accessible_label_names_symbols_letters_and_words(self):
        self.assertEqual(
            "dot dash, dash dot; word gap; dot dot dot",
            morse_accessible_label(".- -. / ..."),
        )

    def test_visual_markup_uses_centered_symbol_classes(self):
        rendered = str(morse_visual(".-"))

        self.assertIn('class="morse-visual"', rendered)
        self.assertIn('aria-label="dot dash"', rendered)
        self.assertEqual(1, rendered.count("morse-dot"))
        self.assertEqual(1, rendered.count("morse-dash"))
        self.assertNotIn(".-", rendered)

    def test_visual_markup_preserves_letter_and_word_groups(self):
        rendered = str(morse_visual("... --- ... / .-"))

        self.assertEqual(2, rendered.count('class="morse-word"'))
        self.assertEqual(4, rendered.count('class="morse-letter"'))
        self.assertIn("word gap", rendered)

    def test_live_decoded_readouts_do_not_start_with_morse_like_dashes(self):
        root = Path(__file__).resolve().parents[1]
        files = [
            root / "static" / "app.js",
            *sorted((root / "templates").glob("*.html")),
        ]
        placeholder_pattern = re.compile(r'(id="liveDecoded"[^>]*>\s*---|liveDecoded\.innerText\s*=\s*"---")')

        offenders = []
        for path in files:
            if placeholder_pattern.search(path.read_text(encoding="utf-8")):
                offenders.append(path.relative_to(root).as_posix())

        self.assertEqual([], offenders)

    def test_practice_feedback_does_not_embed_raw_morse_strings(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "static" / "app.js").read_text(encoding="utf-8")

        raw_morse_feedback = re.compile(
            r"setPracticeFeedback\([^;]*(expected_morse|expectedMorse)",
            re.DOTALL,
        )

        self.assertIsNone(raw_morse_feedback.search(source))


if __name__ == "__main__":
    unittest.main()

import unittest

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


if __name__ == "__main__":
    unittest.main()

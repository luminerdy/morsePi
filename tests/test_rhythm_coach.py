import unittest

from rhythm_coach import rhythm_coach


class RhythmCoachTests(unittest.TestCase):
    def test_detects_word_gap_where_letter_gap_was_expected(self):
        result = rhythm_coach(
            ".. -.",
            ".. / -.",
            [
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
                {"type": "gap", "gap_type": "word", "duration_ms": 1100},
                {"type": "symbol", "symbol": "-", "duration_ms": 360},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
            ],
            correct=False,
        )

        statuses = [segment["status"] for segment in result["actual"] if segment["type"] == "gap"]
        self.assertIn("too-long", statuses)
        self.assertEqual("That pause was too long between letters. I heard a word break.", result["message"])

    def test_detects_missing_letter_gap(self):
        result = rhythm_coach(
            ".. -.",
            "...-.",
            [
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": "-", "duration_ms": 360},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
            ],
            correct=False,
        )

        statuses = [segment["status"] for segment in result["actual"] if segment["type"] == "gap"]
        self.assertIn("too-short", statuses)
        self.assertEqual("Add a little more pause between letters.", result["message"])

    def test_correct_rhythm_gets_encouragement(self):
        result = rhythm_coach(
            ".- --",
            ".- --",
            [
                {"type": "symbol", "symbol": ".", "duration_ms": 120},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": "-", "duration_ms": 360},
                {"type": "gap", "gap_type": "letter", "duration_ms": 360},
                {"type": "symbol", "symbol": "-", "duration_ms": 360},
                {"type": "gap", "gap_type": "symbol", "duration_ms": 120},
                {"type": "symbol", "symbol": "-", "duration_ms": 360},
            ],
            correct=True,
        )

        self.assertEqual("Great rhythm.", result["message"])


if __name__ == "__main__":
    unittest.main()

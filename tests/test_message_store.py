import json
import tempfile
import unittest
from pathlib import Path

from message_store import (
    MessageValidationError,
    advance_hint,
    answer_message,
    available_words,
    choice_letters,
    create_message,
    decoded_words,
    deliver_local_message,
    inbox_dir,
    list_messages,
    load_message,
    normalize_message_text,
    outbox_dir,
)


class MessageStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.allowed = list("ETANIMSO")

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_message(self, text="MEET ME"):
        return create_message("pappy", "astrid", "pappy-test", text, self.allowed)

    def test_normalize_rejects_punctuation_word_and_letter_limits(self):
        self.assertEqual("MEET ME", normalize_message_text("  meet   me "))
        with self.assertRaises(MessageValidationError):
            normalize_message_text("HI!")
        with self.assertRaises(MessageValidationError):
            normalize_message_text("ME AT TEN NOW")
        with self.assertRaises(MessageValidationError):
            normalize_message_text("E" * 21)

    def test_message_rejects_letter_outside_intersection(self):
        with self.assertRaisesRegex(MessageValidationError, "R"):
            create_message("pappy", "astrid", "pappy-test", "MORE", self.allowed)

    def test_available_words_use_only_allowed_letters(self):
        words = available_words(["ME", "MORE", "TEAM", "HELP"], self.allowed)
        self.assertEqual(["ME", "TEAM"], words)

    def test_local_delivery_is_duplicate_safe(self):
        message = self.make_message()
        deliver_local_message(self.data_dir, message)
        deliver_local_message(self.data_dir, message)

        self.assertEqual(1, len(list_messages(outbox_dir(self.data_dir, "pappy"))))
        self.assertEqual(1, len(list_messages(inbox_dir(self.data_dir, "astrid"))))
        loaded = load_message(inbox_dir(self.data_dir, "astrid"), message["message_id"])
        self.assertEqual("MEET ME", loaded["text"])

    def test_decode_hides_unsolved_letters_and_advances_in_order(self):
        message = self.make_message("ME")
        self.assertEqual(["__"], decoded_words(message))

        wrong, result = answer_message(message, 0, "T")
        self.assertFalse(result["correct"])
        self.assertEqual(["__"], decoded_words(wrong))

        first, result = answer_message(wrong, 0, "M")
        self.assertTrue(result["correct"])
        self.assertFalse(result["completed"])
        self.assertEqual(["M_"], decoded_words(first))

        complete, result = answer_message(first, 1, "E")
        self.assertTrue(result["completed"])
        self.assertEqual("decoded", complete["state"])
        self.assertEqual(["ME"], decoded_words(complete))

    def test_hint_progression_slows_shows_morse_then_reveals(self):
        message = self.make_message("M")
        first, result = advance_hint(message, 0)
        self.assertEqual(1, result["level"])
        self.assertEqual("", result["morse"])

        second, result = advance_hint(first, 0)
        self.assertEqual(2, result["level"])
        self.assertEqual("--", result["morse"])

        complete, result = advance_hint(second, 0)
        self.assertTrue(result["revealed"])
        self.assertTrue(result["completed"])
        self.assertEqual("decoded", complete["state"])

    def test_choices_are_stable_and_include_target(self):
        first = choice_letters("M", self.allowed, "message-1:0")
        second = choice_letters("M", self.allowed, "message-1:0")
        self.assertEqual(first, second)
        self.assertIn("M", first)
        self.assertEqual(4, len(first))

    def test_message_content_remains_unchanged_during_decode(self):
        message = self.make_message("ME")
        before = json.dumps({key: message[key] for key in ("text", "required_letters", "created_at")}, sort_keys=True)
        updated, _ = answer_message(message, 0, "M")
        after = json.dumps({key: updated[key] for key in ("text", "required_letters", "created_at")}, sort_keys=True)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

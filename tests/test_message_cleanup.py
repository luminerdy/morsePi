import json
import tempfile
import unittest
from pathlib import Path

from scripts.cleanup_removed_messages import cleanup


REMOVED_ID = "c7674cf3029e402b90fc91e24602052c"
KEPT_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


class MessageCleanupTests(unittest.TestCase):
    def test_cleanup_removes_known_rehearsal_without_touching_other_messages(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            pappy_outbox = data_dir / "students" / "pappy" / "message_outbox"
            astrid_inbox = data_dir / "students" / "astrid" / "message_inbox"
            pappy_outbox.mkdir(parents=True)
            astrid_inbox.mkdir(parents=True)
            removed_outbox = pappy_outbox / f"{REMOVED_ID}.json"
            removed_inbox = astrid_inbox / f"{REMOVED_ID}.json"
            kept_outbox = pappy_outbox / f"{KEPT_ID}.json"
            removed_outbox.write_text("{}", encoding="utf-8")
            removed_inbox.write_text("{}", encoding="utf-8")
            kept_outbox.write_text("{}", encoding="utf-8")

            events_path = data_dir / "students" / "astrid" / "message_events.jsonl"
            events_path.write_text(
                json.dumps({"message_id": REMOVED_ID, "event": "decode_attempt"}) + "\n"
                + json.dumps({"message_id": KEPT_ID, "event": "decode_attempt"}) + "\n",
                encoding="utf-8",
            )

            result = cleanup(data_dir)

            self.assertFalse(removed_outbox.exists())
            self.assertFalse(removed_inbox.exists())
            self.assertTrue(kept_outbox.exists())
            self.assertEqual(2, len(result["removed_files"]))
            self.assertEqual(1, len(result["filtered_event_files"]))
            remaining_events = events_path.read_text(encoding="utf-8")
            self.assertNotIn(REMOVED_ID, remaining_events)
            self.assertIn(KEPT_ID, remaining_events)


if __name__ == "__main__":
    unittest.main()

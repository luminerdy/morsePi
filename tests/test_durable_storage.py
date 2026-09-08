import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from morsepi.storage.durable_storage import (atomic_write_json, read_json, station_transaction,
                             append_jsonl, StorageBusy, StorageCorruption)


def increment(root):
    for _ in range(12):
        with station_transaction(root, timeout=10):
            path = Path(root) / "counter.json"
            value = read_json(path, {"count": 0})
            value["count"] += 1
            atomic_write_json(path, value)


def hold_lock(root, ready):
    import time
    with station_transaction(root):
        ready.set()
        time.sleep(20)


class DurableStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_failed_replace_preserves_original_and_cleans_temporary(self):
        path = self.root / "progress.json"
        atomic_write_json(path, {"count": 5})
        with patch("morsepi.storage.durable_storage.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                atomic_write_json(path, {"count": 6})
        self.assertEqual(read_json(path), {"count": 5})
        self.assertEqual(list(self.root.glob(".pending-*")), [])

    def test_failed_flush_never_replaces_valid_file(self):
        path = self.root / "progress.json"
        atomic_write_json(path, {"count": 5})
        with patch("morsepi.storage.durable_storage.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                atomic_write_json(path, {"count": 6})
        self.assertEqual(read_json(path), {"count": 5})

    def test_corruption_preserved_and_never_treated_as_empty(self):
        path = self.root / "progress.json"
        path.write_bytes(b'{"count":')
        for _ in range(2):
            with self.assertRaises(StorageCorruption):
                read_json(path, {})
        self.assertEqual(path.read_bytes(), b'{"count":')
        copies = list((self.root / "quarantine").iterdir())
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].read_bytes(), path.read_bytes())

    def test_torn_log_is_not_extended(self):
        path = self.root / "attempts.jsonl"
        path.write_bytes(b'{"attempt_id":')
        with self.assertRaises(StorageCorruption):
            append_jsonl(path, {"attempt_id": "next"})
        self.assertEqual(path.read_bytes(), b'{"attempt_id":')

    def test_router_archive_includes_storage_dependency(self):
        import subprocess
        import sys
        from scripts import package_message_router
        archive = self.root / "router.zip"
        with patch.object(package_message_router, "OUTPUT", archive):
            package_message_router.main()
        result = subprocess.run(
            [sys.executable, "-I", "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import morsepi.messaging.message_store; import cloud.message_router", str(archive)],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_two_processes_do_not_lose_updates(self):
        context = multiprocessing.get_context("spawn")
        processes = [context.Process(target=increment, args=(str(self.root),)) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
        self.assertEqual(read_json(self.root / "counter.json")["count"], 24)

    def test_lock_timeout_then_process_exit_releases_without_deleting_lock(self):
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        process = context.Process(target=hold_lock, args=(str(self.root), ready))
        process.start()
        try:
            self.assertTrue(ready.wait(10))
            with self.assertRaises(StorageBusy):
                with station_transaction(self.root, timeout=0.1):
                    self.fail("A second process entered a locked transaction")
        finally:
            process.terminate()
            process.join(10)
        with station_transaction(self.root):
            with station_transaction(self.root):
                atomic_write_json(self.root / "recovered.json", {"ok": True})
        self.assertTrue((self.root / ".storage.lock").exists())

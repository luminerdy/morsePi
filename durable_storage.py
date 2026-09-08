"""Durable single-file writes and short, reentrant station transactions.

Hold station_transaction across read/modify/write, never across network calls.
The OS releases its lock if a process exits; the lock file must not be deleted.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import time


class StorageCorruption(RuntimeError):
    pass


class StorageBusy(RuntimeError):
    pass


_locks = {}
_guard = threading.Lock()
_held = threading.local()


def _sync_directory(directory):
    if os.name != "nt":
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def atomic_write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.read_bytes() == text.encode("utf-8"):
            return
    except FileNotFoundError:
        pass
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".pending-", delete=False) as handle:
            temporary = Path(handle.name)
            if path.exists():
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write_json(path, value):
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_json(path, default=None, expected_type=None):
    path = Path(path)
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return default
    except OSError as error:
        raise StorageCorruption(f"Cannot read storage: {path.name}; recovery needed") from error
    try:
        value = json.loads(raw)
        if expected_type is not None and not isinstance(value, expected_type):
            raise ValueError("Unexpected JSON type")
        return value
    except (ValueError, UnicodeError) as error:
        # Preserve the original in place so subsequent loads cannot replace it
        # with empty defaults; keep one forensic copy per distinct damaged value.
        digest = hashlib.sha256(raw).hexdigest()[:16]
        quarantine = path.parent / "quarantine" / f"{path.name}.{digest}.corrupt"
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        if not quarantine.exists():
            with quarantine.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            _sync_directory(quarantine.parent)
        raise StorageCorruption(f"Damaged storage: {path.name}; preserved for recovery") from error


def append_jsonl(path, record):
    """Caller holds its station transaction; never append to a torn last line."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        with path.open("rb") as handle:
            handle.seek(-1, os.SEEK_END)
            if handle.read(1) != b"\n":
                raise StorageCorruption(f"Incomplete attempt log: {path.name}; recovery needed")
    with path.open("ab") as handle:
        handle.write((json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    _sync_directory(path.parent)


@contextmanager
def station_transaction(data_dir, timeout=2.0):
    root = Path(data_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    key = str(root)
    with _guard:
        local_lock = _locks.setdefault(key, threading.RLock())
    if not local_lock.acquire(timeout=timeout):
        raise StorageBusy("Station storage is busy; try again shortly")
    held = getattr(_held, "roots", set())
    _held.roots = held
    handle = None
    acquired = False
    nested = key in held
    try:
        if not nested:
            handle = (root / ".storage.lock").open("a+b")
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + timeout
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    held.add(key)
                    break
                except (BlockingIOError, PermissionError):
                    if time.monotonic() >= deadline:
                        raise StorageBusy("Station storage is busy; try again shortly")
                    time.sleep(0.02)
        yield
    finally:
        if acquired:
            held.remove(key)
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        if handle is not None:
            handle.close()
        local_lock.release()

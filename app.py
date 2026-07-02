import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, render_template, request, redirect, url_for, jsonify, g, has_request_context
from gpiozero import Button, LED
from morse import text_to_morse, morse_to_text
from practice_attempts import append_practice_attempt, normalize_timing_events, rounded_ms, set_attempts_path, timing_summary
from practice_progress import all_mode_details, choose_next_letter, mode_score, overall_score, progress_summary, record_attempt, save_progress, set_progress_path
import student_profiles as student_profile_store
from student_profiles import (
    STUDENT_COOKIE,
    add_profile,
    ensure_student_storage,
    load_profiles,
    profile_for_id,
    reset_student_storage,
    student_data_path,
    slugify_student_id,
)
from time import time, sleep
import threading
import wave
import math
import tempfile
import subprocess
import os
import random
import shutil

app = Flask(__name__)
SESSION_COOKIE = "morse_practice_session_id"
STATION_CONFIG_PATH = Path("data/station_config.json")
ADMIN_PIN_PATH = Path("data/admin_pin.txt")


@app.before_request
def configure_student_storage():
    global learning_state_path

    profiles = load_profiles()
    requested_student_id = slugify_student_id(request.cookies.get(STUDENT_COOKIE, ""))
    profile_ids = {profile["id"] for profile in profiles}

    if requested_student_id not in profile_ids:
        requested_student_id = profiles[0]["id"]

    ensure_student_storage(requested_student_id)
    g.current_student = profile_for_id(requested_student_id)
    g.student_profiles = profiles

    set_progress_path(student_data_path(requested_student_id, "practice_progress.json"))
    set_attempts_path(student_data_path(requested_student_id, "practice_attempts.jsonl"))
    learning_state_path = student_data_path(requested_student_id, "learning_state.json")
    g.practice_session_id = safe_session_id(request.cookies.get(SESSION_COOKIE, ""))


@app.after_request
def persist_practice_session(response):
    if not getattr(g, "practice_session_id", ""):
        g.practice_session_id = new_practice_session_id()

    response.set_cookie(SESSION_COOKIE, g.practice_session_id, max_age=60 * 60 * 12, samesite="Lax")
    return response


@app.context_processor
def inject_student_context():
    return {
        "current_student": getattr(g, "current_student", profile_for_id("pappy")),
        "student_profiles": getattr(g, "student_profiles", load_profiles()),
        "admin_pin_required": admin_pin_required(),
    }

# -----------------------------
# GPIO setup
# -----------------------------
KEY_GPIO = 17
LED_GPIO = 27

key = Button(KEY_GPIO, pull_up=True, bounce_time=0.03)
led = LED(LED_GPIO)

# -----------------------------
# Morse timing
# -----------------------------
DEFAULT_CHARACTER_WPM = 12
DEFAULT_EFFECTIVE_WPM = 6
DEFAULT_TONE_HZ = 700
TIMING_SETTINGS_PATH = Path("data/timing_settings.json")
KEY_TONE_RETRY_SECONDS = 1.25

LETTER_GAP_THRESHOLD_SECONDS = 0.80
WORD_GAP_THRESHOLD_SECONDS = 1.50
DOT_DASH_THRESHOLD_UNITS = 2.5

# -----------------------------
# USB speaker audio settings
# -----------------------------
SAMPLE_RATE = 44100
DEFAULT_STATION_VOLUME = 0.35
DAILY_MISSION_GOAL = 20
DAILY_CELEBRATION_MORSE = "...-"
BONUS_SPRINT_GOAL = 20
EFFORT_MIN_SECONDS_PER_ATTEMPT = 20
EFFORT_MAX_GAP_SECONDS = 180
FOCUSED_PRACTICE_MINUTES = 10

# Prefer the ALSA card name instead of a numeric card index so the USB speaker
# keeps working when the SD card moves to another Pi or USB port.
AUDIO_DEVICE = os.environ.get("MORSE_AUDIO_DEVICE", "default:CARD=UACDemoV10")

# -----------------------------
# App state
# -----------------------------
last_message = ""
last_morse = ""

station_volume = DEFAULT_STATION_VOLUME
morse_timing = {}

press_started_at = None
last_release_at = None

current_letter = ""
current_morse = ""
current_key_events = []

key_tone_process = None

starter_practice_letters = ["E", "T", "A", "N", "I", "M"]
learning_state_path = Path("data/learning_state.json")
learn_ready_attempts = 10
learn_ready_strength = 70
learn_ready_rest_hours = 3
word_ready_correct_attempts = 5
max_learning_groups_per_day = 2
all_practice_letters = [
    "E", "T", "A", "N", "I", "M",
    "S", "O", "R", "K", "D", "U",
    "C", "W", "H", "L", "P", "F", "Y", "G",
    "B", "V", "J", "X", "Q", "Z",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"
]
alphabet_letters = [letter for letter in all_practice_letters if letter.isalpha()]
word_practice_unlock_letters = ["S", "O"]
word_practice_bank = [
    "AM", "AN", "AS", "AT", "IN", "IS", "IT", "ME", "NO", "ON", "SO", "TO",
    "EAT", "SAT", "SIT", "SET", "SEE", "SEA", "TEA", "TEN", "NET", "MEN",
    "MET", "MAT", "MAN", "SON", "NOT", "TOO", "ANT", "MOM", "MINE", "NAME",
    "MEAN", "MEAT", "MOON", "SOON", "TEAM", "TONE", "NOTE", "SEAT", "STEM",
    "STONE"
]


def new_practice_session_id():
    return uuid4().hex


def is_practice_session_id(value):
    value = str(value or "").strip().lower()
    return len(value) == 32 and all(character in "0123456789abcdef" for character in value)


def safe_session_id(value):
    value = str(value or "").strip().lower()
    if is_practice_session_id(value):
        return value

    return new_practice_session_id()


def load_station_config():
    try:
        loaded = json.loads(STATION_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return loaded if isinstance(loaded, dict) else {}


def current_station_id():
    return str(load_station_config().get("station_id") or "unknown-station")


def configured_admin_pin():
    env_pin = os.environ.get("MORSE_ADMIN_PIN", "").strip()
    if env_pin:
        return env_pin

    config_pin = str(load_station_config().get("admin_pin") or "").strip()
    if config_pin:
        return config_pin

    try:
        return ADMIN_PIN_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def admin_pin_required():
    return bool(configured_admin_pin())


def admin_pin_valid(value):
    required_pin = configured_admin_pin()
    if not required_pin:
        return True

    return str(value or "").strip() == required_pin


def attempt_metadata():
    return {
        "station_id": current_station_id(),
        "practice_session_id": getattr(g, "practice_session_id", ""),
        "student_id": getattr(g, "current_student", {}).get("id", ""),
    }


letter_unlock_steps = [
    {
        "threshold": 100,
        "letters": ["S", "O"],
        "label": "Signal Builder"
    },
    {
        "threshold": 100,
        "letters": ["R", "K"],
        "label": "Rhythm Builder"
    },
    {
        "threshold": 100,
        "letters": ["D", "U"],
        "label": "Relay Builder"
    },
    {
        "threshold": 100,
        "letters": ["C", "W", "H", "L"],
        "label": "Word Builder"
    },
    {
        "threshold": 100,
        "letters": ["P", "F", "Y", "G"],
        "label": "Pattern Builder"
    },
    {
        "threshold": 100,
        "letters": ["B", "V", "J", "X"],
        "label": "Code Builder"
    },
    {
        "threshold": 100,
        "letters": ["Q", "Z"],
        "label": "Alphabet Builder"
    },
    {
        "threshold": 100,
        "letters": ["1", "2", "3", "4", "5"],
        "label": "Number Builder"
    },
    {
        "threshold": 100,
        "letters": ["6", "7", "8", "9", "0"],
        "label": "Full Station Operator"
    }
]
practice_target = "E"
practice_feedback = ""
practice_modes = {
    "send": {
        "label": "Send",
        "progress_label": "Send Progress"
    },
    "read": {
        "label": "Read",
        "progress_label": "Read Progress"
    },
    "listen": {
        "label": "Listen",
        "progress_label": "Listen Progress"
    },
    "echo": {
        "label": "Echo",
        "progress_label": "Echo Progress"
    },
    "learn": {
        "label": "Learn",
        "progress_label": "Learn Progress"
    }
}

key_lock = threading.Lock()
output_lock = threading.Lock()
prompt_led_lock = threading.Lock()
station_stop_event = threading.Event()
prompt_led_stop_event = threading.Event()
station_audio_process = None


# -----------------------------
# LED helpers
# -----------------------------
def led_on():
    led.on()


def led_off():
    led.off()


# -----------------------------
# Key tone helpers
# -----------------------------
def start_key_tone():
    """
    Starts a continuous tone through the USB speaker while the telegraph key is held down.
    """
    global key_tone_process

    if key_tone_process is not None:
        if key_tone_process.poll() is None:
            return

        key_tone_process = None

    key_tone_process = start_speaker_test_process()

    threading.Thread(target=retry_key_tone_if_needed, args=(key_tone_process,), daemon=True).start()


def start_speaker_test_process():
    return subprocess.Popen(
        [
            "speaker-test",
            "-D", AUDIO_DEVICE,
            "-t", "sine",
            "-f", str(morse_timing["tone_hz"])
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def retry_key_tone_if_needed(process):
    global key_tone_process

    deadline = time() + KEY_TONE_RETRY_SECONDS
    current_process = process

    while time() < deadline:
        sleep(0.08)

        if current_process.poll() is None:
            return

        with key_lock:
            key_is_still_down = press_started_at is not None

        if not key_is_still_down or key_tone_process is not current_process:
            return

        sleep(0.12)

        with key_lock:
            key_is_still_down = press_started_at is not None

        if not key_is_still_down or key_tone_process is not current_process:
            return

        current_process = start_speaker_test_process()
        key_tone_process = current_process


def stop_key_tone():
    """
    Stops the USB speaker tone when the telegraph key is released.
    """
    global key_tone_process

    if key_tone_process is None:
        return

    key_tone_process.terminate()

    try:
        key_tone_process.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        key_tone_process.kill()
        try:
            key_tone_process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass

    key_tone_process = None


def reset_audio_state():
    """
    Clears Pi-side audio processes so the next key press or playback starts fresh.
    """
    stop_key_tone()
    stop_station_playback()


# -----------------------------
# USB speaker audio helpers
# -----------------------------
def clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    return max(minimum, min(parsed, maximum))


def default_morse_timing_settings():
    return {
        "character_wpm": DEFAULT_CHARACTER_WPM,
        "effective_wpm": DEFAULT_EFFECTIVE_WPM,
        "tone_hz": DEFAULT_TONE_HZ
    }


def normalize_morse_timing(settings):
    defaults = default_morse_timing_settings()
    character_wpm = clamp_int(settings.get("character_wpm"), defaults["character_wpm"], 5, 35)
    effective_wpm = clamp_int(settings.get("effective_wpm"), defaults["effective_wpm"], 3, character_wpm)
    tone_hz = clamp_int(settings.get("tone_hz"), defaults["tone_hz"], 400, 1000)

    return {
        "character_wpm": character_wpm,
        "effective_wpm": effective_wpm,
        "tone_hz": tone_hz
    }


def load_morse_timing_settings():
    if TIMING_SETTINGS_PATH.exists():
        try:
            loaded = json.loads(TIMING_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = {}
    else:
        loaded = {}

    return normalize_morse_timing(loaded)


def save_morse_timing_settings():
    TIMING_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TIMING_SETTINGS_PATH.write_text(
        json.dumps(normalize_morse_timing(morse_timing), indent=2, sort_keys=True),
        encoding="utf-8"
    )


def get_morse_timing():
    settings = normalize_morse_timing(morse_timing)
    character_wpm = settings["character_wpm"]
    effective_wpm = settings["effective_wpm"]
    tone_hz = settings["tone_hz"]

    character_dot_seconds = 1.2 / character_wpm
    spacing_dot_seconds = 1.2 / effective_wpm

    return {
        "character_wpm": character_wpm,
        "effective_wpm": effective_wpm,
        "tone_hz": tone_hz,
        "dot_seconds": character_dot_seconds,
        "dash_seconds": character_dot_seconds * 3,
        "symbol_gap_seconds": character_dot_seconds,
        "letter_gap_seconds": spacing_dot_seconds * 3,
        "word_gap_seconds": spacing_dot_seconds * 7,
        "dot_ms": round(character_dot_seconds * 1000),
        "dash_ms": round(character_dot_seconds * 3000),
        "symbol_gap_ms": round(character_dot_seconds * 1000),
        "letter_gap_ms": round(spacing_dot_seconds * 3000),
        "word_gap_ms": round(spacing_dot_seconds * 7000),
        "input_dash_threshold_ms": round(character_dot_seconds * DOT_DASH_THRESHOLD_UNITS * 1000)
    }


def get_dot_dash_threshold_seconds():
    return get_morse_timing()["input_dash_threshold_ms"] / 1000


def get_practice_timing(mode, target=None):
    timing = dict(get_morse_timing())
    practice_letters = get_unlocked_practice_letters()

    if mode not in ("listen", "echo"):
        timing["adapted"] = False
        timing["adapted_reason"] = ""
        return timing

    listen_score = mode_score(practice_letters, mode)
    target_summary = next(
        (item for item in progress_summary(practice_letters, mode) if item["letter"] == (target or practice_target)),
        None
    )
    target_needs_help = bool(
        target_summary
        and (target_summary["attempts"] < 3 or target_summary["accuracy"] < 70)
    )

    if listen_score["attempts"] < 10 or listen_score["accuracy"] < 70 or target_needs_help:
        character_wpm = max(8, timing["character_wpm"] - 2)
        effective_wpm = max(4, min(character_wpm, timing["effective_wpm"] - 1))
        character_dot_seconds = 1.2 / character_wpm
        spacing_dot_seconds = 1.2 / effective_wpm

        timing.update({
            "character_wpm": character_wpm,
            "effective_wpm": effective_wpm,
            "dot_seconds": character_dot_seconds,
            "dash_seconds": character_dot_seconds * 3,
            "symbol_gap_seconds": character_dot_seconds,
            "letter_gap_seconds": spacing_dot_seconds * 3,
            "word_gap_seconds": spacing_dot_seconds * 7,
            "dot_ms": round(character_dot_seconds * 1000),
            "dash_ms": round(character_dot_seconds * 3000),
            "symbol_gap_ms": round(character_dot_seconds * 1000),
            "letter_gap_ms": round(spacing_dot_seconds * 3000),
            "word_gap_ms": round(spacing_dot_seconds * 7000),
            "input_dash_threshold_ms": round(character_dot_seconds * DOT_DASH_THRESHOLD_UNITS * 1000),
            "adapted": True,
            "adapted_reason": "Slower Listen practice until accuracy improves"
        })
    else:
        timing["adapted"] = False
        timing["adapted_reason"] = ""

    return timing


morse_timing = load_morse_timing_settings()


def add_tone(samples, frequency_hz, duration_seconds, volume):
    total_samples = int(SAMPLE_RATE * duration_seconds)

    for i in range(total_samples):
        value = int(
            32767
            * volume
            * math.sin(2 * math.pi * frequency_hz * i / SAMPLE_RATE)
        )
        samples.append(value)


def add_silence(samples, duration_seconds):
    total_samples = int(SAMPLE_RATE * duration_seconds)

    for _ in range(total_samples):
        samples.append(0)


def morse_to_audio_samples(morse: str, volume: float, timing):
    samples = []

    for character in morse:
        if character == ".":
            add_tone(samples, timing["tone_hz"], timing["dot_seconds"], volume)
            add_silence(samples, timing["symbol_gap_seconds"])

        elif character == "-":
            add_tone(samples, timing["tone_hz"], timing["dash_seconds"], volume)
            add_silence(samples, timing["symbol_gap_seconds"])

        elif character == " ":
            add_silence(samples, timing["letter_gap_seconds"])

        elif character == "/":
            add_silence(samples, timing["word_gap_seconds"])

    return samples


def write_wav_file(path, samples):
    with wave.open(path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)

        frames = bytearray()
        for sample in samples:
            frames.extend(int(sample).to_bytes(2, byteorder="little", signed=True))

        wav_file.writeframes(frames)


def play_morse_usb_speaker(morse: str, volume: float, timing=None):
    global station_audio_process

    samples = morse_to_audio_samples(morse, volume, timing or get_morse_timing())

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        wav_path = temp_file.name

    try:
        write_wav_file(wav_path, samples)

        # Plays through the configured Raspberry Pi USB speaker.
        station_audio_process = subprocess.Popen(
            ["aplay", "-D", AUDIO_DEVICE, wav_path],
        )

        while station_audio_process.poll() is None:
            if station_stop_event.is_set():
                station_audio_process.terminate()
                try:
                    station_audio_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    station_audio_process.kill()
                break
            sleep(0.05)

    finally:
        station_audio_process = None
        try:
            os.remove(wav_path)
        except FileNotFoundError:
            pass


# -----------------------------
# Station output helpers
# -----------------------------
def flash_morse_led(morse: str, timing=None):
    timing = timing or get_morse_timing()

    try:
        for character in morse:
            if station_stop_event.is_set():
                return

            if character == ".":
                led_on()
                sleep(timing["dot_seconds"])
                led_off()
                sleep(timing["symbol_gap_seconds"])

            elif character == "-":
                led_on()
                sleep(timing["dash_seconds"])
                led_off()
                sleep(timing["symbol_gap_seconds"])

            elif character == " ":
                sleep(timing["letter_gap_seconds"])

            elif character == "/":
                sleep(timing["word_gap_seconds"])

    finally:
        led_off()


def flash_prompt_led(morse: str, timing=None, start_delay_seconds: float = 0):
    timing = timing or get_morse_timing()

    with prompt_led_lock:
        prompt_led_stop_event.clear()

        try:
            delay_remaining = max(0, start_delay_seconds)
            while delay_remaining > 0:
                if prompt_led_stop_event.is_set():
                    return

                sleep_for = min(0.02, delay_remaining)
                sleep(sleep_for)
                delay_remaining -= sleep_for

            for character in morse:
                if prompt_led_stop_event.is_set():
                    return

                if character == ".":
                    led_on()
                    sleep(timing["dot_seconds"])
                    led_off()
                    sleep(timing["symbol_gap_seconds"])

                elif character == "-":
                    led_on()
                    sleep(timing["dash_seconds"])
                    led_off()
                    sleep(timing["symbol_gap_seconds"])

                elif character == " ":
                    sleep(timing["letter_gap_seconds"])

                elif character == "/":
                    sleep(timing["word_gap_seconds"])

        finally:
            led_off()


def flash_prompt_led_in_background(morse: str, timing=None, start_delay_seconds: float = 0):
    prompt_led_stop_event.set()

    thread = threading.Thread(target=flash_prompt_led, args=(morse, timing, start_delay_seconds))
    thread.daemon = True
    thread.start()


def play_morse_on_station(morse: str, timing=None):
    """
    Plays Morse on the Raspberry Pi station:
    - USB speaker for sound
    - LED for visual Morse flashing
    """
    with output_lock:
        station_stop_event.clear()
        volume = station_volume
        playback_timing = timing or get_morse_timing()

        led_thread = threading.Thread(target=flash_morse_led, args=(morse, playback_timing))
        led_thread.daemon = True
        led_thread.start()

        try:
            play_morse_usb_speaker(morse, volume, playback_timing)
        finally:
            led_off()


def play_in_background(morse: str):
    stop_station_playback()

    thread = threading.Thread(target=play_morse_on_station, args=(morse,))
    thread.daemon = True
    thread.start()


def play_daily_celebration_in_background():
    stop_station_playback()

    thread = threading.Thread(target=play_morse_on_station, args=(DAILY_CELEBRATION_MORSE,))
    thread.daemon = True
    thread.start()


def play_practice_prompt_in_background(mode: str):
    morse = text_to_morse(practice_target)
    timing = get_practice_timing(mode, practice_target)

    stop_station_playback()

    thread = threading.Thread(target=play_morse_on_station, args=(morse, timing))
    thread.daemon = True
    thread.start()


def stop_station_playback():
    station_stop_event.set()
    prompt_led_stop_event.set()
    led_off()

    if station_audio_process is not None and station_audio_process.poll() is None:
        station_audio_process.terminate()


# -----------------------------
# Key input helpers
# -----------------------------
def classify_gap(gap_seconds):
    if gap_seconds >= WORD_GAP_THRESHOLD_SECONDS:
        return "word"
    if gap_seconds >= LETTER_GAP_THRESHOLD_SECONDS:
        return "letter"
    return "symbol"


def on_key_down():
    global press_started_at, last_release_at, current_letter, current_morse, current_key_events

    now = time()

    with key_lock:
        if last_release_at is not None:
            gap = now - last_release_at
            gap_type = classify_gap(gap)
            current_key_events.append({
                "type": "gap",
                "gap_type": gap_type,
                "duration_ms": rounded_ms(gap)
            })

            if gap_type == "letter":
                if current_letter:
                    current_morse += current_letter + " "
                    current_letter = ""

            elif gap_type == "word":
                if current_letter:
                    current_morse += current_letter + " "
                    current_letter = ""
                current_morse += "/ "

        press_started_at = now

    # Physical key feedback: LED + USB speaker tone.
    led_on()
    start_key_tone()


def on_key_up():
    global press_started_at, last_release_at, current_letter, current_key_events

    now = time()

    led_off()
    stop_key_tone()

    with key_lock:
        if press_started_at is None:
            return

        duration = now - press_started_at
        symbol = "." if duration < get_dot_dash_threshold_seconds() else "-"

        current_letter += symbol
        current_key_events.append({
            "type": "symbol",
            "symbol": symbol,
            "duration_ms": rounded_ms(duration)
        })
        press_started_at = None
        last_release_at = now


key.when_pressed = on_key_down
key.when_released = on_key_up


def get_current_key_morse():
    with key_lock:
        return (current_morse + current_letter).strip()


def get_current_key_events():
    with key_lock:
        return list(current_key_events)


def clear_key_state():
    global current_letter, current_morse, last_release_at, press_started_at, current_key_events

    with key_lock:
        current_letter = ""
        current_morse = ""
        last_release_at = None
        press_started_at = None
        current_key_events = []


def get_practice_mode():
    mode = request.values.get("mode", "send")

    if request.is_json:
        data = request.get_json(silent=True) or {}
        mode = data.get("mode", mode)

    return mode if mode in practice_modes else "send"


def today_key():
    return datetime.now().date().isoformat()


def parse_attempt_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_attempt_records(path, today_only=False):
    path = Path(path)
    attempts = []
    today = today_key()

    if not path.exists():
        return attempts

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            attempt = json.loads(line)
        except json.JSONDecodeError:
            continue

        timestamp = str(attempt.get("timestamp", ""))
        if not today_only or timestamp[:10] == today:
            attempts.append(attempt)

    return attempts


SESSION_RECOVERY_FILES = ("practice_attempts.jsonl", "word_attempts.jsonl", "bonus_attempts.jsonl")


def write_attempt_records(path, attempts):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not attempts:
        try:
            path.unlink()
        except OSError:
            pass
        return

    path.write_text(
        "\n".join(json.dumps(attempt, sort_keys=True) for attempt in attempts) + "\n",
        encoding="utf-8"
    )


def session_recovery_backup_path(session_id):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_id = safe_session_id(session_id)
    return student_profile_store.DATA_DIR / "session_recovery_backups" / f"{timestamp}-{safe_id}"


def backup_session_recovery_files(backup_root, student_ids):
    for student_id in sorted({slugify_student_id(student_id) for student_id in student_ids}):
        for filename in SESSION_RECOVERY_FILES + ("practice_progress.json",):
            source = student_data_path(student_id, filename)
            if not source.exists():
                continue

            target = backup_root / student_id / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def summarize_practice_sessions(limit=20):
    sessions = {}

    for profile in load_profiles():
        student_id = profile["id"]
        student_name = profile["name"]
        for filename in SESSION_RECOVERY_FILES:
            for attempt in load_attempt_records(student_data_path(student_id, filename)):
                raw_session_id = str(attempt.get("practice_session_id", "")).strip().lower()
                if not is_practice_session_id(raw_session_id):
                    continue
                session_id = raw_session_id

                summary = sessions.setdefault(session_id, {
                    "id": session_id,
                    "students": {},
                    "station_ids": set(),
                    "counts": {name: 0 for name in SESSION_RECOVERY_FILES},
                    "attempts": 0,
                    "correct": 0,
                    "started_at": "",
                    "ended_at": "",
                })
                summary["students"][student_id] = student_name
                if attempt.get("station_id"):
                    summary["station_ids"].add(str(attempt.get("station_id")))
                summary["counts"][filename] += 1
                summary["attempts"] += 1
                if attempt.get("correct"):
                    summary["correct"] += 1

                timestamp = str(attempt.get("timestamp", ""))
                if timestamp:
                    if not summary["started_at"] or timestamp < summary["started_at"]:
                        summary["started_at"] = timestamp
                    if not summary["ended_at"] or timestamp > summary["ended_at"]:
                        summary["ended_at"] = timestamp

    normalized = []
    for summary in sessions.values():
        summary["student_label"] = ", ".join(summary["students"].values())
        summary["station_label"] = ", ".join(sorted(summary["station_ids"])) or "unknown-station"
        summary["accuracy"] = int(round((summary["correct"] / summary["attempts"]) * 100)) if summary["attempts"] else 0
        summary["practice_count"] = summary["counts"]["practice_attempts.jsonl"]
        summary["word_count"] = summary["counts"]["word_attempts.jsonl"]
        summary["bonus_count"] = summary["counts"]["bonus_attempts.jsonl"]
        normalized.append(summary)

    normalized.sort(key=lambda item: item["ended_at"], reverse=True)
    return normalized[:limit]


def rebuild_practice_progress_for_student(student_id):
    progress = {}
    attempts = load_attempt_records(student_data_path(student_id, "practice_attempts.jsonl"))
    attempts.sort(key=lambda attempt: str(attempt.get("timestamp", "")))

    for attempt in attempts:
        letter = str(attempt.get("target", "")).upper()
        mode = str(attempt.get("mode", "send")).lower()
        if not letter or mode not in practice_modes:
            continue

        letter_progress = progress.setdefault(letter, {})
        record = letter_progress.setdefault(mode, {
            "attempts": 0,
            "correct": 0,
            "streak": 0,
            "strength": 0.0,
            "last_seen": ""
        })
        record["attempts"] += 1
        record["last_seen"] = str(attempt.get("timestamp", "")) or datetime.now(timezone.utc).isoformat()

        if attempt.get("correct"):
            record["correct"] += 1
            record["streak"] += 1
            record["strength"] = min(1.0, record["strength"] + 0.18 + min(record["streak"], 4) * 0.02)
        else:
            record["streak"] = 0
            record["strength"] = max(0.0, record["strength"] - 0.35)

    original_path = student_data_path(g.current_student["id"], "practice_progress.json") if has_request_context() else None
    set_progress_path(student_data_path(student_id, "practice_progress.json"))
    save_progress(progress)
    if original_path is not None:
        set_progress_path(original_path)

    return progress


def recover_practice_session(session_id, action, target_student_id=""):
    if not is_practice_session_id(session_id):
        return {"status": "bad-session", "moved": 0, "discarded": 0}

    session_id = str(session_id).strip().lower()
    target_student_id = slugify_student_id(target_student_id)
    profiles = load_profiles()
    valid_student_ids = {profile["id"] for profile in profiles}

    if target_student_id and target_student_id not in valid_student_ids:
        target_student_id = ""

    if action == "move" and not target_student_id:
        return {"status": "missing-target", "moved": 0, "discarded": 0}

    if action not in ("move", "discard"):
        return {"status": "bad-action", "moved": 0, "discarded": 0}

    touched_students = set()
    moved_count = 0
    discarded_count = 0
    found_count = 0
    backup_root = session_recovery_backup_path(session_id)
    backed_up_students = set()

    for profile in profiles:
        student_id = profile["id"]
        for filename in SESSION_RECOVERY_FILES:
            path = student_data_path(student_id, filename)
            attempts = load_attempt_records(path)
            kept = []
            selected = []

            for attempt in attempts:
                raw_session_id = str(attempt.get("practice_session_id", "")).strip().lower()
                if raw_session_id == session_id:
                    selected.append(attempt)
                else:
                    kept.append(attempt)

            if not selected:
                continue

            found_count += len(selected)
            touched_students.add(student_id)

            students_to_backup = {student_id}
            if action == "move":
                students_to_backup.add(target_student_id)
            backup_session_recovery_files(backup_root, students_to_backup - backed_up_students)
            backed_up_students.update(students_to_backup)

            write_attempt_records(path, kept)

            if action == "move":
                target_path = student_data_path(target_student_id, filename)
                target_attempts = load_attempt_records(target_path)
                for attempt in selected:
                    moved_attempt = dict(attempt)
                    moved_attempt["student_id"] = target_student_id
                    target_attempts.append(moved_attempt)
                target_attempts.sort(key=lambda attempt: str(attempt.get("timestamp", "")))
                write_attempt_records(target_path, target_attempts)
                touched_students.add(target_student_id)
                moved_count += len(selected)
            else:
                discarded_count += len(selected)

    if not found_count:
        return {"status": "not-found", "moved": 0, "discarded": 0}

    for student_id in touched_students:
        rebuild_practice_progress_for_student(student_id)

    return {
        "status": "moved" if action == "move" else "discarded",
        "session_id": session_id,
        "target_student_id": target_student_id,
        "moved": moved_count,
        "discarded": discarded_count,
        "backup_path": str(backup_root),
        "students": sorted(touched_students),
    }


def load_today_attempts():
    return load_attempt_records(student_data_path(g.current_student["id"], "practice_attempts.jsonl"), today_only=True)


def load_today_effort_attempts():
    student_id = g.current_student["id"]
    attempts = []
    for filename in ("practice_attempts.jsonl", "word_attempts.jsonl", "bonus_attempts.jsonl"):
        attempts.extend(load_attempt_records(student_data_path(student_id, filename), today_only=True))
    return attempts


def load_all_effort_attempts():
    student_id = g.current_student["id"]
    attempts = []
    for filename in ("practice_attempts.jsonl", "word_attempts.jsonl", "bonus_attempts.jsonl"):
        attempts.extend(load_attempt_records(student_data_path(student_id, filename), today_only=False))
    return attempts


def effort_summary(attempts):
    timestamps = sorted(
        parsed for parsed in (parse_attempt_time(attempt.get("timestamp")) for attempt in attempts)
        if parsed is not None
    )
    attempt_count = len(timestamps)

    if not attempt_count:
        return {
            "attempts": 0,
            "seconds": 0,
            "minutes": 0,
            "label": "0 min",
        }

    seconds = attempt_count * EFFORT_MIN_SECONDS_PER_ATTEMPT

    for previous, current in zip(timestamps, timestamps[1:]):
        if previous.tzinfo and not current.tzinfo:
            current = current.replace(tzinfo=previous.tzinfo)
        elif current.tzinfo and not previous.tzinfo:
            previous = previous.replace(tzinfo=current.tzinfo)

        gap_seconds = max(0, int(round((current - previous).total_seconds())))
        if gap_seconds <= EFFORT_MAX_GAP_SECONDS:
            seconds += gap_seconds

    minutes = int(round(seconds / 60))
    if seconds > 0 and minutes == 0:
        minutes = 1

    if minutes < 60:
        label = f"{minutes} min"
    else:
        hours = minutes // 60
        remainder = minutes % 60
        label = f"{hours} hr {remainder} min" if remainder else f"{hours} hr"

    return {
        "attempts": attempt_count,
        "seconds": seconds,
        "minutes": minutes,
        "label": label,
    }


def has_try_again_win(attempts):
    sorted_attempts = sorted(
        (
            (parse_attempt_time(attempt.get("timestamp")), attempt)
            for attempt in attempts
            if parse_attempt_time(attempt.get("timestamp")) is not None
        ),
        key=lambda item: item[0],
    )
    saw_miss = False

    for _, attempt in sorted_attempts:
        if attempt.get("correct"):
            if saw_miss:
                return True
            continue

        saw_miss = True

    return False


def grit_coach_line(daily):
    if daily.get("try_again_win"):
        return "You missed one, tried again, and got stronger."

    effort = daily.get("effort", {})
    if effort.get("minutes", 0) >= FOCUSED_PRACTICE_MINUTES:
        return "You gave focused practice time. That is how Morse gets stronger."

    if daily.get("attempts", 0) > 0:
        return "Every careful try helps your signal grow."

    return "Start with one good try. Practice builds the signal."


def daily_mission_summary():
    attempts = load_today_attempts()
    effort_attempts = load_today_effort_attempts() if has_request_context() else attempts
    effort = effort_summary(effort_attempts)
    try_again_win = has_try_again_win(effort_attempts)
    total = len(attempts)
    correct = sum(1 for attempt in attempts if attempt.get("correct"))
    letters = sorted({str(attempt.get("target", "")).upper() for attempt in attempts if attempt.get("target")})
    modes = sorted({str(attempt.get("mode", "")).title() for attempt in attempts if attempt.get("mode")})
    state = get_practice_letter_state()
    remaining = max(0, DAILY_MISSION_GOAL - total)
    accuracy = int(round((correct / total) * 100)) if total else 0
    attempt_progress = min(100, int(round((total / DAILY_MISSION_GOAL) * 100))) if DAILY_MISSION_GOAL else 100
    learning_focus = daily_learning_focus(state["learning_letters"])
    progress = attempt_progress
    completed = total >= DAILY_MISSION_GOAL

    if learning_focus["active"]:
        progress = int(round((attempt_progress + learning_focus["progress"]) / 2))
        completed = completed and learning_focus["complete"]

    next_action = daily_next_action(state)

    if completed:
        if state["learning_status"] and state["learning_status"].get("needs"):
            message = f"Daily mission complete. {state['learning_status']['next_need'].capitalize()}."
        else:
            message = "Daily mission complete."
    elif learning_focus["active"] and learning_focus["next_need"]:
        message = f"Daily mission: {learning_focus['next_need']}."
    elif state["learning_letters"]:
        message = f"Daily mission: practice today and spend time with {' '.join(state['learning_letters'])}."
    else:
        message = "Daily mission: review every active signal and keep your rhythm steady."

    summary = {
        "date": today_key(),
        "goal": DAILY_MISSION_GOAL,
        "attempts": total,
        "display_attempts": min(total, DAILY_MISSION_GOAL),
        "correct": correct,
        "remaining": remaining,
        "accuracy": accuracy,
        "effort": effort,
        "try_again_win": try_again_win,
        "attempt_progress": attempt_progress,
        "progress": progress,
        "completed": completed,
        "letters": letters,
        "letters_preview": letters[:8],
        "letters_remaining_count": max(0, len(letters) - 8),
        "modes": modes,
        "active_letters": state["active_letters"],
        "active_letters_preview": state["active_letters"][:12],
        "active_letters_remaining_count": max(0, len(state["active_letters"]) - 12),
        "learning_letters": state["learning_letters"],
        "learning_focus": learning_focus,
        "letter_morse": get_practice_letter_morse(),
        "message": message,
        "next_action": next_action,
        "coach": daily_practice_coach(state)
    }
    summary["grit_message"] = grit_coach_line(summary)
    return summary


def bonus_attempts_path():
    return student_data_path(g.current_student["id"], "bonus_attempts.jsonl")


def append_bonus_attempt(record):
    path = bonus_attempts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = dict(record)
    normalized["timestamp"] = datetime.now(timezone.utc).isoformat()

    with path.open("a", encoding="utf-8") as attempts_file:
        attempts_file.write(json.dumps(normalized, sort_keys=True) + "\n")

    return normalized


def word_attempts_path():
    if not has_request_context():
        return learning_state_path.parent / "word_attempts.jsonl"

    return student_data_path(g.current_student["id"], "word_attempts.jsonl")


def append_word_attempt(record):
    path = word_attempts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = dict(record)
    normalized["timestamp"] = datetime.now(timezone.utc).isoformat()
    normalized["timing_events"] = normalize_timing_events(normalized.get("timing_events", []))
    normalized["timing_summary"] = timing_summary(normalized["timing_events"])

    with path.open("a", encoding="utf-8") as attempts_file:
        attempts_file.write(json.dumps(normalized, sort_keys=True) + "\n")

    return normalized


def load_bonus_attempts(session_id=None):
    path = bonus_attempts_path()

    if not path.exists():
        return []

    attempts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            attempt = json.loads(line)
        except json.JSONDecodeError:
            continue

        if session_id and attempt.get("session_id") != session_id:
            continue

        attempts.append(attempt)

    return attempts


def bonus_sprint_summary(session_id):
    attempts = load_bonus_attempts(session_id)
    total = len(attempts)
    correct = sum(1 for attempt in attempts if attempt.get("correct"))
    streak = 0
    best_streak = 0

    for attempt in attempts:
        if attempt.get("correct"):
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0

    return {
        "goal": BONUS_SPRINT_GOAL,
        "attempts": total,
        "correct": correct,
        "remaining": max(0, BONUS_SPRINT_GOAL - total),
        "accuracy": int(round((correct / total) * 100)) if total else 0,
        "streak": streak,
        "best_streak": best_streak,
        "complete": total >= BONUS_SPRINT_GOAL,
    }


def choose_bonus_sprint_target():
    global practice_target
    practice_target = random.choice(get_unlocked_practice_letters())
    clear_key_state()
    return practice_target


def student_badges(overall, daily):
    earned = []

    def add_badge(badge_id, label, detail, earned_when):
        badge = {
            "id": badge_id,
            "label": label,
            "detail": detail,
            "earned": bool(earned_when),
        }
        if badge["earned"]:
            earned.append(badge)
        return badge

    learning_focus = daily.get("learning_focus", {})
    add_badge(
        "daily-signal-complete",
        "Daily Signal Complete",
        "Finish today's practice count.",
        daily.get("completed"),
    )
    add_badge(
        "clean-copy",
        "Clean Copy",
        "Finish a daily mission with at least 90% accuracy.",
        daily.get("completed") and daily.get("accuracy", 0) >= 90,
    )
    add_badge(
        "focused-practice",
        "Focused Practice",
        f"Practice for {FOCUSED_PRACTICE_MINUTES} active minutes today.",
        daily.get("effort", {}).get("minutes", 0) >= FOCUSED_PRACTICE_MINUTES,
    )
    add_badge(
        "try-again-champ",
        "Try Again Champ",
        "Miss one, try again, and keep going.",
        daily.get("try_again_win"),
    )
    add_badge(
        "first-signals-mastered",
        "First Signals Mastered",
        "Master the first six signals.",
        overall.get("alphabet_mastered", 0) >= len(starter_practice_letters)
        and overall.get("current_mastery", 0) >= 100,
    )
    add_badge(
        "new-signals-ready",
        "New Signals Ready",
        "Complete the Learn burn-in for new signals.",
        learning_focus.get("active") and learning_focus.get("complete"),
    )
    add_badge(
        "signal-builder",
        "Signal Builder",
        "Master eight letters.",
        overall.get("alphabet_mastered", 0) >= 8,
    )

    if (
        learning_focus.get("active")
        and not learning_focus.get("complete")
        and daily.get("attempt_progress", 0) >= 100
    ):
        next_badge = {
            "label": "New Signals Ready",
            "detail": learning_focus.get("next_need") or "Finish the new-signal Learn work.",
        }
    elif daily.get("effort", {}).get("minutes", 0) < FOCUSED_PRACTICE_MINUTES:
        next_badge = {
            "label": "Focused Practice",
            "detail": f"{max(0, FOCUSED_PRACTICE_MINUTES - daily.get('effort', {}).get('minutes', 0))} active minutes left today.",
        }
    elif not daily.get("try_again_win"):
        next_badge = {
            "label": "Try Again Champ",
            "detail": "Keep going after a miss and get one right.",
        }
    elif not daily.get("completed"):
        next_badge = {
            "label": "Daily Signal Complete",
            "detail": f"{daily.get('remaining', 0)} signals left today.",
        }
    elif daily.get("accuracy", 0) < 90:
        next_badge = {
            "label": "Clean Copy",
            "detail": "Finish a daily mission at 90% accuracy or better.",
        }
    elif learning_focus.get("active") and not learning_focus.get("complete"):
        next_badge = {
            "label": "New Signals Ready",
            "detail": learning_focus.get("next_need") or "Finish the new-signal Learn work.",
        }
    elif overall.get("alphabet_mastered", 0) < 8:
        next_badge = {
            "label": "Signal Builder",
            "detail": "Unlock and master the next signal group.",
        }
    else:
        next_badge = {
            "label": "Keep Current",
            "detail": "Keep today's signals strong and watch for the next group.",
        }

    return {
        "earned": earned,
        "featured": earned[0] if earned else None,
        "next": next_badge,
    }


def daily_learning_focus(learning_letters):
    if not learning_letters:
        return {
            "active": False,
            "goal": 0,
            "correct": 0,
            "remaining": 0,
            "progress": 100,
            "complete": True,
            "next_need": "",
            "letters": []
        }

    items = progress_summary(learning_letters, "learn")
    goal = learn_ready_attempts * len(items)
    correct = sum(min(item["correct"], learn_ready_attempts) for item in items)
    remaining = max(0, goal - correct)
    progress = int(round((correct / goal) * 100)) if goal else 100
    needs = []

    for item in items:
        correct_remaining = max(0, learn_ready_attempts - item["correct"])
        if correct_remaining:
            needs.append(f"{item['letter']} needs {correct_remaining} more correct Learn tries")
            continue

        strength_remaining = max(0, learn_ready_strength - item["strength_percent"])
        if strength_remaining:
            needs.append(f"{item['letter']} needs {strength_remaining} more Learn strength points")

    return {
        "active": True,
        "goal": goal,
        "correct": correct,
        "remaining": remaining,
        "progress": min(100, progress),
        "complete": remaining == 0 and not needs,
        "next_need": needs[0] if needs else "",
        "letters": [
            {
                "letter": item["letter"],
                "correct": min(item["correct"], learn_ready_attempts),
                "goal": learn_ready_attempts,
                "remaining": max(0, learn_ready_attempts - item["correct"]),
                "progress": min(100, int(round((min(item["correct"], learn_ready_attempts) / learn_ready_attempts) * 100))) if learn_ready_attempts else 100
            }
            for item in items
        ]
    }


def mode_display_label(mode):
    return practice_modes.get(mode, {}).get("label", mode.title())


def daily_practice_coach(state):
    if state["learning_letters"]:
        letters = " ".join(state["learning_letters"])
        learning_items = progress_summary(state["learning_letters"], "learn")
        learning_order = {
            letter: index
            for index, letter in enumerate(state["learning_letters"])
        }
        boost_items = sorted(
            [
                {
                    "letter": item["letter"],
                    "strength": item["strength_percent"],
                    "attempts": item["attempts"],
                    "accuracy": item["accuracy"]
                }
                for item in learning_items
            ],
            key=lambda item: (item["strength"], item["attempts"], learning_order.get(item["letter"], 99))
        )

        return {
            "headline": "Practice Next",
            "message": f"Start with Learn for {letters}. New signals stay here until they are ready.",
            "practice_next": [
                {
                    "letter": item["letter"],
                    "mode": "learn",
                    "mode_label": "Learn",
                    "href": "/touch/practice/run?mode=learn",
                    "score": item["strength_percent"],
                    "reason": f"{min(item['correct'], learn_ready_attempts)}/{learn_ready_attempts}"
                }
                for item in learning_items[:3]
            ],
            "strong_label": "Mastered",
            "boost_label": "Learning",
            "strong_signals": strongest_letters(state["active_letters"]),
            "signal_boost": boost_items[:3]
        }

    active_letters = state["active_letters"]
    next_items = weakest_letter_mode_items(active_letters, limit=3)
    strong = strongest_letters(active_letters)
    strong_letters = {item["letter"] for item in strong}
    boost = weakest_letters(active_letters, exclude=strong_letters)

    if next_items:
        first = next_items[0]
        message = f"Try {first['mode_label']} with {first['letter']} next."
    else:
        message = "Start with any active signal. The coach will update after a few tries."

    return {
        "headline": "Practice Coach",
        "message": message,
        "practice_next": next_items,
        "strong_label": "Strong",
        "boost_label": "Boost",
        "strong_signals": strong,
        "signal_boost": boost
    }


def weakest_letter_mode_items(letters, limit=3):
    candidates = []

    for mode in practice_modes:
        for item in progress_summary(letters, mode):
            score = item["strength_percent"]
            attempts = item["attempts"]
            priority = score + min(attempts, 3) * 3

            candidates.append({
                "letter": item["letter"],
                "mode": mode,
                "mode_label": mode_display_label(mode),
                "href": f"/touch/practice/run?mode={mode}",
                "score": score,
                "attempts": attempts,
                "reason": "Start" if attempts == 0 else f"{score}%"
            } | {"priority": priority})

    candidates.sort(key=lambda item: (item["priority"], item["letter"], item["mode"]))

    return [
        {key: value for key, value in item.items() if key != "priority"}
        for item in candidates[:limit]
    ]


def letter_strength_rollup(letters):
    rollup = []

    for letter in letters:
        mode_items = [
            item for mode in practice_modes
            for item in progress_summary([letter], mode)
        ]
        attempts = sum(item["attempts"] for item in mode_items)
        strength = int(round(sum(item["strength_percent"] for item in mode_items) / len(mode_items))) if mode_items else 0
        accuracy_attempts = sum(item["attempts"] for item in mode_items)
        correct = sum(item["correct"] for item in mode_items)
        accuracy = int(round((correct / accuracy_attempts) * 100)) if accuracy_attempts else 0

        rollup.append({
            "letter": letter,
            "strength": strength,
            "attempts": attempts,
            "accuracy": accuracy
        })

    return rollup


def strongest_letters(letters, limit=3):
    practiced = [item for item in letter_strength_rollup(letters) if item["attempts"] > 0]
    practiced.sort(key=lambda item: (-item["strength"], -item["accuracy"], item["letter"]))
    return practiced[:limit]


def weakest_letters(letters, limit=3, exclude=None):
    exclude = set(exclude or [])
    rollup = [item for item in letter_strength_rollup(letters) if item["letter"] not in exclude]
    rollup.sort(key=lambda item: (item["strength"], item["attempts"], item["letter"]))
    return rollup[:limit]


def daily_next_action(state):
    if state["learning_letters"]:
        letters = " ".join(state["learning_letters"])
        status = state.get("learning_status") or {}
        focus = daily_learning_focus(state["learning_letters"])

        if focus["complete"] and status.get("needs"):
            next_need = status.get("next_need", "New signals can join practice after a short break.")
            needs_break = "break" in next_need
            return {
                "label": "Break" if needs_break else "Learn",
                "mode": "",
                "href": "/touch/daily",
                "title": "Take A Break" if needs_break else "Keep Learning",
                "detail": next_need.capitalize()
            }

        return {
            "label": "Learn",
            "mode": "learn",
            "href": "/touch/practice/run?mode=learn",
            "title": f"Learn {letters}",
            "detail": "New signals are waiting. Learn them before they join the other practice modes."
        }

    active_letters = state["active_letters"]
    mode_order = {mode: index for index, mode in enumerate(practice_modes)}
    mode_scores = [
        (mode, mode_score(active_letters, mode))
        for mode in practice_modes
    ]

    weakest_mode, weakest_score = min(
        mode_scores,
        key=lambda item: (item[1]["mastery"], item[1]["accuracy"], mode_order[item[0]])
    )
    mode_label = practice_modes[weakest_mode]["label"]

    if weakest_score["mastery"] < 100:
        return {
            "label": mode_label,
            "mode": weakest_mode,
            "href": f"/touch/practice/run?mode={weakest_mode}",
            "title": f"Practice {mode_label}",
            "detail": f"{mode_label} has the most room to improve today."
        }

    if state["locked_until_tomorrow"]:
        wait_status = state.get("unlock_wait_status") or {}
        return {
            "label": wait_status.get("label", "Next"),
            "mode": "",
            "href": wait_status.get("href", "/touch/daily"),
            "title": wait_status.get("title", "Keep Building"),
            "detail": wait_status.get("detail", "Finish the readiness work to open new signals.")
        }

    next_step = state["next_step"] or get_next_letter_unlock(active_letters)
    if next_step and next_step.get("letters"):
        letters = " ".join(next_step["letters"])
        return {
            "label": "Next",
            "mode": "",
            "href": "/touch/progress",
            "title": f"Next Signals: {letters}",
            "detail": "Keep today's active signals strong to unlock the next group."
        }

    return {
        "label": "Progress",
        "mode": "",
        "href": "/touch/progress",
        "title": "Review Progress",
        "detail": "All planned signals are open. Check progress for the next weak spot."
    }


def word_practice_unlocked(active_letters=None):
    letters = set(active_letters or get_unlocked_practice_letters())
    return all(letter in letters for letter in word_practice_unlock_letters)


def available_word_practice_words(active_letters=None):
    letters = set(active_letters or get_unlocked_practice_letters())

    if not word_practice_unlocked(letters):
        return []

    return [
        word for word in word_practice_bank
        if all(character in letters for character in word)
    ]


def word_practice_summary(active_letters=None):
    words = available_word_practice_words(active_letters)

    return {
        "unlocked": bool(words),
        "count": len(words),
        "unlock_letters": word_practice_unlock_letters,
        "words": words,
    }


def normalize_word_morse(value):
    cleaned = "".join(character for character in str(value).strip() if character in ".-/ ")
    return " ".join(cleaned.split())


def server_checked_keying_result(target, actual_morse):
    expected_morse = normalize_word_morse(text_to_morse(target))
    actual_morse = normalize_word_morse(actual_morse)
    return expected_morse, actual_morse, bool(actual_morse and actual_morse == expected_morse)


def server_checked_letter_answer(target, answer):
    normalized_target = str(target).strip().upper()
    normalized_answer = str(answer or "").strip().upper()[:1]
    return normalized_answer, bool(normalized_answer and normalized_answer == normalized_target)


def word_practice_item(index=0, active_letters=None):
    words = available_word_practice_words(active_letters)

    if not words:
        return None

    normalized_index = index % len(words)
    word = words[normalized_index]

    return {
        "word": word,
        "morse": text_to_morse(word),
        "index": normalized_index,
        "next_index": (normalized_index + 1) % len(words),
        "total": len(words),
        "letters": [
            {
                "letter": letter,
                "morse": text_to_morse(letter),
            }
            for letter in word
        ],
    }


def load_word_attempts():
    path = word_attempts_path()
    attempts = []

    if not path.exists():
        return attempts

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            attempts.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return attempts


def word_progress_summary():
    summary = word_practice_summary()
    attempts = load_word_attempts()
    total = len(attempts)
    correct = sum(1 for attempt in attempts if attempt.get("correct"))
    unique_correct = sorted({
        str(attempt.get("word", "")).upper()
        for attempt in attempts
        if attempt.get("correct") and attempt.get("word")
    })
    accuracy = int(round((correct / total) * 100)) if total else 0

    if not summary["unlocked"]:
        return {
            "unlocked": False,
            "accuracy": 0,
            "correct": 0,
            "total": 0,
            "unique_correct": 0,
            "available": 0,
            "label": "Unlock after S O",
            "detail": "Known-letter words",
        }

    return {
        "unlocked": True,
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "unique_correct": len(unique_correct),
        "available": summary["count"],
        "label": f"{len(unique_correct)}/{summary['count']} words",
        "detail": f"{correct}/{total} correct" if total else "No word tries yet",
    }


def timestamp_at_or_after(timestamp, started_at):
    if not timestamp:
        return False

    try:
        parsed = datetime.fromisoformat(str(timestamp))
    except ValueError:
        return False

    if parsed.tzinfo and not started_at.tzinfo:
        started_at = started_at.replace(tzinfo=parsed.tzinfo)
    elif started_at.tzinfo and not parsed.tzinfo:
        parsed = parsed.replace(tzinfo=started_at.tzinfo)

    return parsed >= started_at


def correct_word_attempts_since(started_at):
    return sum(
        1 for attempt in load_word_attempts()
        if attempt.get("correct") and timestamp_at_or_after(attempt.get("timestamp"), started_at)
    )


def learning_groups_started_today(state):
    today = today_key()
    return sum(
        1 for group_state in state.get("groups", {}).values()
        if str(group_state.get("first_learning_date", "")) == today
    )


def next_unlock_wait_status(active_letters, state, latest_group_state):
    if latest_group_state is None:
        return None

    if learning_groups_started_today(state) >= max_learning_groups_per_day:
        return {
            "label": "Tomorrow",
            "href": "/touch/daily",
            "title": "Come Back Tomorrow",
            "detail": "Great work. New signals can open tomorrow."
        }

    started_at = group_started_at(latest_group_state)
    rest = learning_rest_status(latest_group_state)
    correct_words = correct_word_attempts_since(started_at) if word_practice_unlocked(active_letters) else word_ready_correct_attempts
    words_remaining = max(0, word_ready_correct_attempts - correct_words)

    if words_remaining or not rest["ready"]:
        parts = []
        if words_remaining:
            parts.append(f"{words_remaining} more correct Word{'s' if words_remaining != 1 else ''}")
        if not rest["ready"]:
            parts.append(f"{rest['remaining_label']} of break time")

        return {
            "label": "Words" if words_remaining else "Break",
            "href": "/touch/words" if words_remaining else "/touch/daily",
            "title": "Practice Words" if words_remaining else "Take A Break",
            "detail": f"{' and '.join(parts)} before new signals can open."
        }

    return None


def step_key(step):
    return "".join(step["letters"])


def load_learning_state():
    if not learning_state_path.exists():
        return {
            "groups": {},
            "last_learning_start_date": ""
        }

    try:
        loaded = json.loads(learning_state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        loaded = {}

    return {
        "groups": loaded.get("groups", {}) if isinstance(loaded.get("groups"), dict) else {},
        "last_learning_start_date": str(loaded.get("last_learning_start_date", ""))
    }


def save_learning_state(state):
    learning_state_path.parent.mkdir(parents=True, exist_ok=True)
    learning_state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True),
        encoding="utf-8"
    )


def days_since(date_text):
    if not date_text:
        return 0

    try:
        start_date = datetime.fromisoformat(date_text).date()
    except ValueError:
        return 0

    return (datetime.now().date() - start_date).days + 1


def group_started_at(group_state):
    started_at = str(group_state.get("first_learning_started_at", ""))
    learned_since = str(group_state.get("first_learning_date", ""))

    if started_at:
        try:
            return datetime.fromisoformat(started_at)
        except ValueError:
            pass

    if not learned_since:
        return datetime.now()

    try:
        learned_date = datetime.fromisoformat(learned_since).date()
    except ValueError:
        return datetime.now()

    if learned_date == datetime.now().date():
        return datetime.now()

    try:
        return datetime.fromisoformat(f"{learned_date.isoformat()}T00:00:00")
    except ValueError:
        return datetime.now()


def hours_since(started_at):
    now = datetime.now(started_at.tzinfo) if started_at.tzinfo else datetime.now()
    return max(0, (now - started_at).total_seconds() / 3600)


def format_hours_remaining(hours):
    if hours <= 0:
        return "ready now"

    if hours < 1:
        minutes = max(1, int(round(hours * 60)))
        return f"about {minutes} minute{'s' if minutes != 1 else ''}"

    rounded = int(math.ceil(hours))
    return f"about {rounded} hour{'s' if rounded != 1 else ''}"


def learning_rest_status(group_state):
    started_at = group_started_at(group_state)
    elapsed_hours = hours_since(started_at)
    remaining_hours = max(0, learn_ready_rest_hours - elapsed_hours)

    return {
        "started_at": started_at.isoformat(timespec="seconds"),
        "elapsed_hours": elapsed_hours,
        "remaining_hours": remaining_hours,
        "remaining_label": format_hours_remaining(remaining_hours),
        "ready": remaining_hours <= 0,
    }


def learning_step_ready(step, group_state):
    progress = progress_summary(step["letters"], "learn")
    rest = learning_rest_status(group_state)

    practice_ready = all(
        item["correct"] >= learn_ready_attempts and item["strength_percent"] >= learn_ready_strength
        for item in progress
    )

    return practice_ready and rest["ready"]


def get_learning_step_status(step, group_state):
    progress = progress_summary(step["letters"], "learn")
    learned_since = str(group_state.get("first_learning_date", ""))
    days_learning = days_since(learned_since)
    rest = learning_rest_status(group_state)
    needs = []

    for item in progress:
        if item["correct"] < learn_ready_attempts:
            needs.append(f"{item['letter']} needs {learn_ready_attempts - item['correct']} more correct Learn tries")

        if item["strength_percent"] < learn_ready_strength:
            needs.append(f"{item['letter']} needs {learn_ready_strength - item['strength_percent']} more strength points")

    if not rest["ready"]:
        needs.append(f"take a short break; {rest['remaining_label']} left")

    return {
        "letters": step["letters"],
        "learned_since": learned_since,
        "started_at": rest["started_at"],
        "days_learning": days_learning,
        "rest_hours": rest["elapsed_hours"],
        "min_rest_hours": learn_ready_rest_hours,
        "ready": not needs,
        "needs": needs,
        "next_need": needs[0] if needs else "Ready to join practice"
    }


def get_practice_letter_state():
    active = list(starter_practice_letters)
    latest_group_state = None
    learning_step = None
    learning_status = None
    next_step = None
    locked_until_tomorrow = False
    unlock_wait_status = None
    state = load_learning_state()
    today = today_key()
    changed = False

    for index, step in enumerate(letter_unlock_steps):
        key = step_key(step)
        group_state = state["groups"].get(key)

        if group_state:
            if learning_step_ready(step, group_state):
                active.extend(letter for letter in step["letters"] if letter not in active)
                latest_group_state = group_state
                continue

            learning_step = step
            learning_status = get_learning_step_status(step, group_state)
            break

        scores = [mode_score(active, mode) for mode in practice_modes]

        if all(score["mastery"] >= step["threshold"] for score in scores):
            unlock_wait_status = next_unlock_wait_status(active, state, latest_group_state)
            if unlock_wait_status:
                next_step = step
                locked_until_tomorrow = True
                break

            group_state = {
                "letters": step["letters"],
                "first_learning_date": today,
                "first_learning_started_at": datetime.now().isoformat(timespec="seconds")
            }
            state["groups"][key] = group_state
            state["last_learning_start_date"] = today
            learning_step = step
            learning_status = get_learning_step_status(step, group_state)
            changed = True
            break
        else:
            stale_keys = [
                step_key(stale_step)
                for stale_step in letter_unlock_steps[index + 1:]
                if step_key(stale_step) in state["groups"]
            ]
            if stale_keys:
                for stale_key in stale_keys:
                    state["groups"].pop(stale_key, None)
                state["last_learning_start_date"] = ""
                changed = True

            next_step = step
            break

    if changed:
        save_learning_state(state)

    if learning_step is None and next_step is None:
        next_step = get_next_letter_unlock(active)

    learning_letters = learning_step["letters"] if learning_step else []

    return {
        "active_letters": [letter for letter in all_practice_letters if letter in active],
        "learning_letters": [letter for letter in all_practice_letters if letter in learning_letters],
        "learning_step": learning_step,
        "learning_status": learning_status,
        "next_step": next_step,
        "locked_until_tomorrow": locked_until_tomorrow,
        "unlock_wait_status": unlock_wait_status,
        "learn_ready_attempts": learn_ready_attempts,
        "learn_ready_strength": learn_ready_strength,
        "learn_ready_rest_hours": learn_ready_rest_hours,
        "word_ready_correct_attempts": word_ready_correct_attempts,
        "max_learning_groups_per_day": max_learning_groups_per_day
    }


def get_unlocked_practice_letters():
    return get_practice_letter_state()["active_letters"]


def get_practice_letters_for_mode(mode):
    state = get_practice_letter_state()

    if mode == "learn" and state["learning_letters"]:
        return state["learning_letters"]

    return state["active_letters"]


def get_next_letter_unlock(unlocked_letters):
    for step in letter_unlock_steps:
        if any(letter not in unlocked_letters for letter in step["letters"]):
            return step

    return {
        "threshold": None,
        "letters": [],
        "label": "All planned letters unlocked"
    }


def get_learning_overall(letters):
    state = get_practice_letter_state()
    overall = overall_score(state["active_letters"], practice_modes.keys())
    active_alphabet_count = sum(1 for letter in state["active_letters"] if letter in alphabet_letters)
    alphabet_total = len(alphabet_letters)
    alphabet_percent = int(round((active_alphabet_count / alphabet_total) * 100)) if alphabet_total else 100
    mode_masteries = [mode_score(state["active_letters"], mode)["mastery"] for mode in practice_modes]

    overall["current_mastery"] = overall["mastery"]
    overall["current_set_complete"] = bool(mode_masteries) and all(mastery >= 100 for mastery in mode_masteries)
    overall["alphabet_mastered"] = active_alphabet_count
    overall["alphabet_total"] = alphabet_total
    overall["alphabet_percent"] = alphabet_percent
    overall["alphabet_progress"] = f"{active_alphabet_count}/{alphabet_total}"
    overall["unlocked_letters"] = state["active_letters"]
    overall["active_letters"] = state["active_letters"]
    overall["learning_letters"] = state["learning_letters"]
    overall["learn_ready_attempts"] = state["learn_ready_attempts"]
    overall["learn_ready_strength"] = state["learn_ready_strength"]
    overall["learn_ready_rest_hours"] = state["learn_ready_rest_hours"]
    overall["word_ready_correct_attempts"] = state["word_ready_correct_attempts"]
    overall["max_learning_groups_per_day"] = state["max_learning_groups_per_day"]
    overall["learning_step"] = state["learning_step"]
    overall["learning_status"] = state["learning_status"]
    overall["learning_focus"] = daily_learning_focus(state["learning_letters"])
    overall["locked_until_tomorrow"] = state["locked_until_tomorrow"]
    overall["unlock_wait_status"] = state["unlock_wait_status"]
    overall["next_unlock"] = state["learning_step"] or state["next_step"] or get_next_letter_unlock(state["active_letters"])

    if state["learning_step"]:
        status = state["learning_status"] or {}
        overall["next_goal"] = status.get("next_need") or f"Learn {' '.join(state['learning_letters'])} before they join practice"
    elif state["locked_until_tomorrow"]:
        wait_status = state.get("unlock_wait_status") or {}
        overall["next_goal"] = wait_status.get("detail", "Finish the readiness work to open new signals.")
    elif overall["next_unlock"]["letters"]:
        threshold = overall["next_unlock"]["threshold"]
        points_to_unlock = max(0, threshold - min(mode_masteries))
        overall["next_goal"] = f"{points_to_unlock} current-set mastery points to unlock {' '.join(overall['next_unlock']['letters'])}"
    else:
        overall["next_goal"] = overall["next_unlock"]["label"]

    return overall


def get_progress_mode_details():
    state = get_practice_letter_state()
    details = all_mode_details(state["active_letters"], practice_modes.keys())

    for mode, mode_details in details.items():
        mode_details["scope"] = "current_set"
        mode_details["scope_label"] = "Current Set"
        mode_details["summary_label"] = "current set"
        mode_details["letters_label"] = "Current Set Letters"

    if state["learning_letters"]:
        learning_focus = daily_learning_focus(state["learning_letters"])
        learn_score = mode_score(state["learning_letters"], "learn")
        learn_score["mastery"] = learning_focus["progress"]
        learn_score["next_goal"] = learning_focus["next_need"] or learn_score["next_goal"]
        learn_score["completion_label"] = f"{learning_focus['correct']}/{learning_focus['goal']} Learn"

        details["learn"] = {
            "score": learn_score,
            "letters": progress_summary(state["learning_letters"], "learn"),
            "scope": "learning_now",
            "scope_label": "Learning Now",
            "summary_label": f"Learning {' '.join(state['learning_letters'])}",
            "letters_label": "Learning Now Letters"
        }

    return details


def get_read_choices(target):
    choices = [target]
    practice_letters = get_practice_letters_for_mode(get_practice_mode())
    others = [letter for letter in practice_letters if letter != target]
    choices.extend(random.sample(others, min(3, len(others))))
    return random.sample(choices, len(choices))


def get_practice_letter_morse():
    state = get_practice_letter_state()
    letters = state["active_letters"] + state["learning_letters"]
    return {letter: text_to_morse(letter) for letter in letters}


def choose_new_practice_target(mode="send"):
    global practice_target, practice_feedback

    practice_letters = get_practice_letters_for_mode(mode)
    practice_target = choose_next_letter(practice_letters, practice_target, mode)
    practice_feedback = ""
    clear_key_state()


def station_volume_percent():
    return int(station_volume * 100)


def update_message_from_request():
    global last_message, last_morse

    if request.method == "POST":
        last_message = request.form.get("message", "")
        last_morse = text_to_morse(last_message)


def render_home_template(template_name):
    update_message_from_request()

    return render_template(
        template_name,
        message=last_message,
        morse=last_morse,
        station_volume_percent=station_volume_percent(),
        timing=get_morse_timing()
    )


def render_practice_template(template_name):
    global practice_target

    mode = get_practice_mode()
    practice_letters = get_practice_letters_for_mode(mode)
    overall = get_learning_overall(practice_letters)

    if practice_target not in practice_letters:
        choose_new_practice_target(mode)

    expected_morse = text_to_morse(practice_target)
    feedback = practice_feedback

    if not feedback and overall["learning_letters"]:
        learning = " ".join(overall["learning_letters"])
        if mode == "learn":
            feedback = f"New letters unlocked: {learning}. Learn them here first."
        else:
            feedback = f"New letters unlocked: {learning}. Use Learn mode first; they are not in this practice mode yet."

    return render_template(
        template_name,
        mode=mode,
        modes=practice_modes,
        target=practice_target,
        expected_morse=expected_morse,
        read_choices=get_read_choices(practice_target),
        feedback=feedback,
        progress=progress_summary(practice_letters, mode),
        score=mode_score(practice_letters, mode),
        overall=overall,
        word_practice=word_practice_summary(overall["active_letters"]),
        letter_morse=get_practice_letter_morse(),
        progress_label=practice_modes[mode]["progress_label"],
        timing=get_practice_timing(mode, practice_target)
    )


def safe_next_url(default_endpoint="touch_index"):
    next_url = request.form.get("next") or request.args.get("next") or ""

    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url

    return url_for(default_endpoint)


# -----------------------------
# Main routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    return render_home_template("index.html")


@app.route("/touch", methods=["GET", "POST"])
def touch_index():
    if len(g.student_profiles) == 1:
        return redirect(url_for("touch_daily"))

    return redirect(url_for("touch_students"))


@app.route("/touch/menu", methods=["GET", "POST"])
def touch_menu():
    return render_practice_template("touch_menu.html")


@app.route("/touch/daily")
def touch_daily():
    practice_letters = get_unlocked_practice_letters()
    overall = get_learning_overall(practice_letters)
    daily = daily_mission_summary()

    return render_template(
        "touch_daily.html",
        modes=practice_modes,
        overall=overall,
        daily=daily,
        badges=student_badges(overall, daily),
        timing=get_morse_timing()
    )


@app.route("/touch/bonus/sprint")
def touch_bonus_sprint():
    target = choose_bonus_sprint_target()
    session_id = request.args.get("session") or uuid4().hex
    summary = bonus_sprint_summary(session_id)

    return render_template(
        "touch_bonus_sprint.html",
        target=target,
        expected_morse=text_to_morse(target),
        session_id=session_id,
        bonus=summary,
        timing=get_practice_timing("send", target)
    )


@app.route("/touch/daily/celebrate", methods=["POST"])
def touch_daily_celebrate():
    if daily_mission_summary()["completed"]:
        play_daily_celebration_in_background()
        return jsonify({"status": "celebrating"})

    return jsonify({"status": "not-complete"}), 409


@app.route("/students", methods=["GET", "POST"])
def students():
    global practice_target, practice_feedback

    if request.method == "POST":
        action = request.form.get("action", "select")
        default_next_endpoint = "touch_daily" if request.path.startswith("/touch/") else "students"

        if action == "reset":
            profile = profile_for_id(slugify_student_id(request.form.get("student_id", "")))
            if request.form.get("reset_confirm", "").strip().upper() != "RESET":
                return redirect(url_for("students", reset_error="type-reset"))

            if not admin_pin_valid(request.form.get("admin_pin", "")):
                return redirect(url_for("students", reset_error="admin-pin"))

            reset_student_storage(profile["id"])
            practice_target = "E"
            practice_feedback = ""
            clear_key_state()
            response = redirect(url_for("students", reset_student=profile["name"]))
            response.set_cookie(STUDENT_COOKIE, profile["id"], max_age=60 * 60 * 24 * 365)
            g.practice_session_id = new_practice_session_id()
            response.set_cookie(SESSION_COOKIE, g.practice_session_id, max_age=60 * 60 * 12, samesite="Lax")
            return response

        if action == "create":
            if not admin_pin_valid(request.form.get("admin_pin", "")):
                return redirect(url_for("students", reset_error="admin-pin"))

            profile = add_profile(request.form.get("student_name", ""))
        else:
            profile = profile_for_id(slugify_student_id(request.form.get("student_id", "")))

        ensure_student_storage(profile["id"])
        practice_target = "E"
        practice_feedback = ""
        clear_key_state()
        response = redirect(safe_next_url(default_next_endpoint))
        response.set_cookie(STUDENT_COOKIE, profile["id"], max_age=60 * 60 * 24 * 365)
        g.practice_session_id = new_practice_session_id()
        response.set_cookie(SESSION_COOKIE, g.practice_session_id, max_age=60 * 60 * 12, samesite="Lax")
        return response

    return render_template(
        "students.html",
        next_url=safe_next_url("index"),
        reset_student=request.args.get("reset_student", ""),
        reset_error=request.args.get("reset_error", "")
    )


@app.route("/touch/students", methods=["GET", "POST"])
def touch_students():
    if request.method == "POST":
        return students()

    return render_template(
        "touch_students.html",
        next_url=safe_next_url("touch_daily")
    )


@app.route("/touch/message", methods=["GET", "POST"])
def touch_message():
    return render_home_template("touch_message.html")


@app.route("/touch/progress")
def touch_progress():
    practice_letters = get_unlocked_practice_letters()
    overall = get_learning_overall(practice_letters)
    daily = daily_mission_summary()
    effort = effort_summary(load_all_effort_attempts())

    return render_template(
        "touch_progress.html",
        modes=practice_modes,
        overall=overall,
        daily=daily,
        effort=effort,
        words=word_progress_summary(),
        badges=student_badges(overall, daily),
        details=get_progress_mode_details()
    )


@app.route("/admin/sessions", methods=["GET", "POST"])
def admin_sessions():
    if request.method == "POST":
        if not admin_pin_valid(request.form.get("admin_pin", "")):
            return redirect(url_for("admin_sessions", recovery_error="admin-pin"))

        result = recover_practice_session(
            request.form.get("session_id", ""),
            request.form.get("action", ""),
            request.form.get("target_student_id", "")
        )

        if result["status"] in ("moved", "discarded"):
            return redirect(url_for(
                "admin_sessions",
                recovery_status=result["status"],
                count=result["moved"] or result["discarded"],
            ))

        return redirect(url_for("admin_sessions", recovery_error=result["status"]))

    return render_template(
        "admin_sessions.html",
        sessions=summarize_practice_sessions(),
        recovery_status=request.args.get("recovery_status", ""),
        recovery_error=request.args.get("recovery_error", ""),
        count=request.args.get("count", "0"),
    )


@app.route("/touch/key")
def touch_key():
    return render_home_template("touch_key.html")


@app.route("/touch/timing")
def touch_timing():
    return render_home_template("touch_timing.html")


@app.route("/play", methods=["POST"])
def play():
    if last_morse:
        play_in_background(last_morse)

    return redirect(request.form.get("next") or url_for("index"))


@app.route("/stop-playback", methods=["POST"])
def stop_playback():
    stop_station_playback()
    return redirect(request.form.get("next") or url_for("index"))


@app.route("/audio-reset", methods=["POST"])
def audio_reset():
    reset_audio_state()
    return jsonify({"status": "reset"})


@app.route("/station-volume", methods=["POST"])
def set_station_volume():
    global station_volume

    if not admin_pin_valid(request.form.get("admin_pin", "")):
        return "Admin PIN required", 403

    try:
        volume_percent = int(request.form.get("station_volume", "35"))
    except ValueError:
        volume_percent = 35

    volume_percent = max(0, min(volume_percent, 100))
    station_volume = volume_percent / 100.0

    return redirect(request.form.get("next") or url_for("index"))


@app.route("/timing-settings", methods=["POST"])
def set_timing_settings():
    if not admin_pin_valid(request.form.get("admin_pin", "")):
        return "Admin PIN required", 403

    morse_timing.update(normalize_morse_timing({
        "character_wpm": request.form.get("character_wpm"),
        "effective_wpm": request.form.get("effective_wpm"),
        "tone_hz": request.form.get("tone_hz")
    }))
    save_morse_timing_settings()

    return redirect(request.form.get("next") or url_for("index"))


@app.route("/live-key")
def live_key():
    full_morse = get_current_key_morse()
    decoded = morse_to_text(full_morse) if full_morse else ""

    return jsonify({
        "morse": full_morse,
        "decoded": decoded
    })


@app.route("/clear-key", methods=["POST"])
def clear_key():
    clear_key_state()
    return jsonify({"status": "cleared"})


# -----------------------------
# Practice routes
# -----------------------------
@app.route("/practice")
def practice():
    return render_practice_template("practice.html")


@app.route("/touch/practice")
def touch_practice():
    return render_practice_template("touch_practice_menu.html")


@app.route("/touch/practice/run")
def touch_practice_run():
    return render_practice_template("touch_practice.html")


@app.route("/touch/words")
def touch_words():
    active_letters = get_unlocked_practice_letters()
    overall = get_learning_overall(active_letters)
    summary = word_practice_summary(active_letters)

    try:
        word_index = int(request.args.get("i", "0"))
    except ValueError:
        word_index = 0

    return render_template(
        "touch_words.html",
        overall=overall,
        word_practice=summary,
        word_progress=word_progress_summary(),
        word_item=word_practice_item(word_index, active_letters),
        timing=get_morse_timing()
    )


@app.route("/practice/new", methods=["POST"])
def practice_new():
    mode = get_practice_mode()
    choose_new_practice_target(mode)
    return redirect(request.form.get("next") or url_for("practice", mode=mode))


@app.route("/practice/next", methods=["POST"])
def practice_next():
    mode = get_practice_mode()
    choose_new_practice_target(mode)
    practice_letters = get_practice_letters_for_mode(mode)

    return jsonify({
        "mode": mode,
        "target": practice_target,
        "expected_morse": text_to_morse(practice_target),
        "read_choices": get_read_choices(practice_target),
        "timing": get_practice_timing(mode, practice_target),
        "progress": progress_summary(practice_letters, mode),
        "score": mode_score(practice_letters, mode),
        "overall": get_learning_overall(practice_letters)
    })


@app.route("/practice/retry", methods=["POST"])
def practice_retry():
    mode = get_practice_mode()
    practice_letters = get_practice_letters_for_mode(mode)

    if practice_target not in practice_letters:
        choose_new_practice_target(mode)

    clear_key_state()

    return jsonify({
        "mode": mode,
        "target": practice_target,
        "expected_morse": text_to_morse(practice_target),
        "read_choices": get_read_choices(practice_target),
        "timing": get_practice_timing(mode, practice_target),
        "progress": progress_summary(practice_letters, mode),
        "score": mode_score(practice_letters, mode),
        "overall": get_learning_overall(practice_letters)
    })


@app.route("/practice/prompt-led", methods=["POST"])
def practice_prompt_led():
    mode = get_practice_mode()

    if mode not in ("listen", "echo", "learn"):
        return jsonify({"status": "ignored"})

    delay_ms = clamp_int(request.args.get("delay_ms"), 100, 0, 500)
    flash_prompt_led_in_background(
        text_to_morse(practice_target),
        get_practice_timing(mode, practice_target),
        delay_ms / 1000
    )
    return jsonify({"status": "flashing", "delay_ms": delay_ms})


@app.route("/practice/prompt-station", methods=["POST"])
def practice_prompt_station():
    mode = get_practice_mode()

    if mode not in ("listen", "echo", "learn"):
        return jsonify({"status": "ignored"})

    play_practice_prompt_in_background(mode)
    return jsonify({"status": "playing"})


@app.route("/words/prompt-station", methods=["POST"])
def words_prompt_station():
    data = request.get_json(silent=True) or {}
    morse = normalize_word_morse(data.get("morse", ""))

    if not morse:
        return jsonify({"status": "missing-morse"}), 400

    play_in_background(morse)
    return jsonify({"status": "playing"})


@app.route("/words/stop", methods=["POST"])
def words_stop():
    stop_station_playback()
    return jsonify({"status": "stopped"})


@app.route("/words/result", methods=["POST"])
def words_result():
    data = request.get_json(silent=True) or {}
    word = str(data.get("word", "")).upper()
    actual_morse = normalize_word_morse(data.get("actual_morse", get_current_key_morse()))
    expected_morse, actual_morse, is_correct = server_checked_keying_result(word, actual_morse)
    decoded = morse_to_text(actual_morse).upper() if actual_morse else ""
    elapsed_ms = data.get("elapsed_ms")

    try:
        elapsed_ms = max(0, int(round(float(elapsed_ms)))) if elapsed_ms is not None else None
    except (TypeError, ValueError):
        elapsed_ms = None

    if not word or word not in available_word_practice_words():
        return jsonify({"status": "ignored"}), 400

    attempt_record = append_word_attempt({
        "kind": "word-practice",
        **attempt_metadata(),
        "word": word,
        "expected_morse": expected_morse,
        "actual_morse": actual_morse,
        "decoded": decoded,
        "correct": is_correct,
        "elapsed_ms": elapsed_ms,
        "timing": get_morse_timing(),
        "timing_events": data.get("timing_events") or get_current_key_events(),
    })

    return jsonify({
        "status": "recorded",
        "attempt": attempt_record,
    })


@app.route("/bonus/next", methods=["POST"])
def bonus_next():
    target = choose_bonus_sprint_target()

    return jsonify({
        "target": target,
        "expected_morse": text_to_morse(target),
        "timing": get_practice_timing("send", target),
    })


@app.route("/bonus/result", methods=["POST"])
def bonus_result():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    letter = str(data.get("target", practice_target)).upper()
    expected_morse, actual_morse, is_correct = server_checked_keying_result(
        letter,
        data.get("actual_morse") or get_current_key_morse().strip()
    )
    timing_events = data.get("timing_events") or get_current_key_events()

    if not session_id:
        return jsonify({"status": "missing-session"}), 400

    if letter not in get_unlocked_practice_letters():
        return jsonify({
            "status": "ignored",
            "bonus": bonus_sprint_summary(session_id),
        })

    attempt_record = append_bonus_attempt({
        "kind": "signal-sprint",
        **attempt_metadata(),
        "session_id": session_id,
        "target": letter,
        "expected_morse": expected_morse,
        "actual_morse": actual_morse,
        "correct": is_correct,
        "timing": get_practice_timing("send", letter),
        "timing_events": timing_events,
    })

    return jsonify({
        "status": "recorded",
        "attempt": attempt_record,
        "timing": get_practice_timing("send", letter),
        "bonus": bonus_sprint_summary(session_id),
    })


@app.route("/practice/result", methods=["POST"])
def practice_result():
    data = request.get_json(silent=True) or {}
    letter = str(data.get("target", practice_target)).upper()
    mode = data.get("mode", "send")
    answer = data.get("answer", "")
    actual_morse = data.get("actual_morse") or get_current_key_morse().strip()
    timing_events = data.get("timing_events") or get_current_key_events()

    if mode not in practice_modes:
        mode = "send"

    expected_morse = normalize_word_morse(text_to_morse(letter))

    if mode in ("read", "listen"):
        answer, is_correct = server_checked_letter_answer(letter, answer)
        actual_morse = ""
    else:
        expected_morse, actual_morse, is_correct = server_checked_keying_result(letter, actual_morse)

    practice_letters = get_practice_letters_for_mode(mode)

    if letter not in practice_letters:
        return jsonify({
            "status": "ignored",
            "timing": get_practice_timing(mode, letter),
            "progress": progress_summary(practice_letters, mode),
            "score": mode_score(practice_letters, mode),
            "overall": get_learning_overall(practice_letters)
        })

    record_attempt(letter, is_correct, practice_letters, mode)
    attempt_record = append_practice_attempt({
        "mode": mode,
        **attempt_metadata(),
        "target": letter,
        "expected_morse": expected_morse,
        "actual_morse": actual_morse,
        "answer": answer,
        "correct": is_correct,
        "timing": get_practice_timing(mode, letter),
        "timing_events": timing_events
    })

    return jsonify({
        "status": "recorded",
        "attempt": attempt_record,
        "timing": get_practice_timing(mode, letter),
        "progress": progress_summary(practice_letters, mode),
        "score": mode_score(practice_letters, mode),
        "overall": get_learning_overall(practice_letters)
    })


@app.route("/progress")
def progress():
    mode = get_practice_mode()
    practice_letters = get_unlocked_practice_letters()
    effort = effort_summary(load_all_effort_attempts())

    return render_template(
        "progress.html",
        mode=mode,
        modes=practice_modes,
        overall=get_learning_overall(practice_letters),
        details=get_progress_mode_details(),
        effort=effort,
        letter_morse=get_practice_letter_morse()
    )


@app.route("/practice/play", methods=["POST"])
def practice_play():
    mode = get_practice_mode()
    expected_morse = text_to_morse(practice_target)
    play_in_background(expected_morse)
    return redirect(request.form.get("next") or url_for("practice", mode=mode))


@app.route("/practice/check", methods=["POST"])
def practice_check():
    global practice_feedback

    mode = get_practice_mode()
    practice_letters = get_practice_letters_for_mode(mode)
    expected_morse = text_to_morse(practice_target).strip()
    actual_morse = get_current_key_morse().strip()

    if not actual_morse:
        practice_feedback = "Tap the telegraph key first, then check your answer."

    elif actual_morse == expected_morse:
        record_attempt(practice_target, True, practice_letters, mode)
        practice_feedback = f"Great job! You tapped {practice_target} correctly."

    else:
        record_attempt(practice_target, False, practice_letters, mode)
        practice_feedback = (
            f"Good try. I heard {actual_morse}, but {practice_target} is {expected_morse}. "
            "Try again and listen to the rhythm."
        )

    return redirect(url_for("practice", mode=mode))


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        stop_key_tone()
        led_off()
        key.close()
        led.close()

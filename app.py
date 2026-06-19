import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, jsonify
from gpiozero import Button, LED
from morse import text_to_morse, morse_to_text
from practice_attempts import append_practice_attempt, rounded_ms
from practice_progress import all_mode_details, choose_next_letter, mode_score, overall_score, progress_summary, record_attempt
from time import time, sleep
import threading
import wave
import math
import tempfile
import subprocess
import os
import random

app = Flask(__name__)

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
learn_ready_min_days = 2
all_practice_letters = [
    "E", "T", "A", "N", "I", "M",
    "S", "O", "R", "K", "D", "U",
    "C", "W", "H", "L", "P", "F", "Y", "G",
    "B", "V", "J", "X", "Q", "Z",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"
]
letter_unlock_steps = [
    {
        "threshold": 50,
        "letters": ["S", "O"],
        "label": "Signal Builder"
    },
    {
        "threshold": 65,
        "letters": ["R", "K"],
        "label": "Rhythm Builder"
    },
    {
        "threshold": 80,
        "letters": ["D", "U"],
        "label": "Relay Builder"
    },
    {
        "threshold": 80,
        "letters": ["C", "W", "H", "L"],
        "label": "Word Builder"
    },
    {
        "threshold": 82,
        "letters": ["P", "F", "Y", "G"],
        "label": "Pattern Builder"
    },
    {
        "threshold": 85,
        "letters": ["B", "V", "J", "X"],
        "label": "Code Builder"
    },
    {
        "threshold": 85,
        "letters": ["Q", "Z"],
        "label": "Alphabet Builder"
    },
    {
        "threshold": 88,
        "letters": ["1", "2", "3", "4", "5"],
        "label": "Number Builder"
    },
    {
        "threshold": 88,
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


def play_morse_usb_speaker(morse: str, volume: float):
    global station_audio_process

    samples = morse_to_audio_samples(morse, volume, get_morse_timing())

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
def flash_morse_led(morse: str):
    timing = get_morse_timing()

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


def play_morse_on_station(morse: str):
    """
    Plays Morse on the Raspberry Pi station:
    - USB speaker for sound
    - LED for visual Morse flashing
    """
    with output_lock:
        station_stop_event.clear()
        volume = station_volume

        led_thread = threading.Thread(target=flash_morse_led, args=(morse,))
        led_thread.daemon = True
        led_thread.start()

        try:
            play_morse_usb_speaker(morse, volume)
        finally:
            led_off()


def play_in_background(morse: str):
    stop_station_playback()

    thread = threading.Thread(target=play_morse_on_station, args=(morse,))
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


def learning_step_ready(step, learned_since):
    progress = progress_summary(step["letters"], "learn")
    days_learning = days_since(learned_since)

    practice_ready = all(
        item["correct"] >= learn_ready_attempts and item["strength_percent"] >= learn_ready_strength
        for item in progress
    )

    return practice_ready and days_learning >= learn_ready_min_days


def get_learning_step_status(step, learned_since):
    progress = progress_summary(step["letters"], "learn")
    days_learning = days_since(learned_since)
    needs = []

    for item in progress:
        if item["correct"] < learn_ready_attempts:
            needs.append(f"{item['letter']} needs {learn_ready_attempts - item['correct']} more correct Learn tries")

        if item["strength_percent"] < learn_ready_strength:
            needs.append(f"{item['letter']} needs {learn_ready_strength - item['strength_percent']} more strength points")

    if days_learning < learn_ready_min_days:
        needs.append("come back tomorrow to lock it in")

    return {
        "letters": step["letters"],
        "learned_since": learned_since,
        "days_learning": days_learning,
        "min_days": learn_ready_min_days,
        "ready": not needs,
        "needs": needs,
        "next_need": needs[0] if needs else "Ready to join practice"
    }


def get_practice_letter_state():
    active = list(starter_practice_letters)
    learning_step = None
    learning_status = None
    next_step = None
    locked_until_tomorrow = False
    state = load_learning_state()
    today = today_key()
    changed = False

    for step in letter_unlock_steps:
        key = step_key(step)
        scores = [mode_score(active, mode) for mode in practice_modes]

        if all(score["mastery"] >= step["threshold"] for score in scores):
            group_state = state["groups"].get(key)

            if not group_state:
                if state["last_learning_start_date"] == today:
                    next_step = step
                    locked_until_tomorrow = True
                    break

                group_state = {
                    "letters": step["letters"],
                    "first_learning_date": today
                }
                state["groups"][key] = group_state
                state["last_learning_start_date"] = today
                changed = True

            learned_since = group_state.get("first_learning_date", "")
            if learning_step_ready(step, learned_since):
                active.extend(letter for letter in step["letters"] if letter not in active)
            else:
                learning_step = step
                learning_status = get_learning_step_status(step, learned_since)
                break
        else:
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
        "learn_ready_attempts": learn_ready_attempts,
        "learn_ready_strength": learn_ready_strength,
        "learn_ready_min_days": learn_ready_min_days
    }


def get_unlocked_practice_letters():
    return get_practice_letter_state()["active_letters"]


def get_practice_letters_for_mode(mode):
    state = get_practice_letter_state()

    if mode == "learn" and state["learning_letters"]:
        return state["active_letters"] + state["learning_letters"]

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
    overall["unlocked_letters"] = state["active_letters"]
    overall["active_letters"] = state["active_letters"]
    overall["learning_letters"] = state["learning_letters"]
    overall["learn_ready_attempts"] = state["learn_ready_attempts"]
    overall["learn_ready_strength"] = state["learn_ready_strength"]
    overall["learn_ready_min_days"] = state["learn_ready_min_days"]
    overall["learning_step"] = state["learning_step"]
    overall["learning_status"] = state["learning_status"]
    overall["locked_until_tomorrow"] = state["locked_until_tomorrow"]
    overall["next_unlock"] = state["learning_step"] or state["next_step"] or get_next_letter_unlock(state["active_letters"])

    if state["learning_step"]:
        status = state["learning_status"] or {}
        overall["next_goal"] = status.get("next_need") or f"Learn {' '.join(state['learning_letters'])} before they join practice"
    elif state["locked_until_tomorrow"]:
        overall["next_goal"] = "Great work. Next new letters can open tomorrow."
    elif overall["next_unlock"]["letters"]:
        threshold = overall["next_unlock"]["threshold"]
        mode_masteries = [mode_score(state["active_letters"], mode)["mastery"] for mode in practice_modes]
        points_to_unlock = max(0, threshold - min(mode_masteries))
        overall["next_goal"] = f"{points_to_unlock} mastery points to unlock {' '.join(overall['next_unlock']['letters'])}"
    else:
        overall["next_goal"] = overall["next_unlock"]["label"]

    return overall


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
        letter_morse=get_practice_letter_morse(),
        progress_label=practice_modes[mode]["progress_label"],
        timing=get_practice_timing(mode, practice_target)
    )


# -----------------------------
# Main routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    return render_home_template("index.html")


@app.route("/touch", methods=["GET", "POST"])
def touch_index():
    return render_practice_template("touch_menu.html")


@app.route("/touch/message", methods=["GET", "POST"])
def touch_message():
    return render_home_template("touch_message.html")


@app.route("/touch/progress")
def touch_progress():
    practice_letters = get_unlocked_practice_letters()
    return render_template(
        "touch_progress.html",
        modes=practice_modes,
        overall=get_learning_overall(practice_letters),
        details=all_mode_details(practice_letters, practice_modes.keys())
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

    try:
        volume_percent = int(request.form.get("station_volume", "35"))
    except ValueError:
        volume_percent = 35

    volume_percent = max(0, min(volume_percent, 100))
    station_volume = volume_percent / 100.0

    return redirect(request.form.get("next") or url_for("index"))


@app.route("/timing-settings", methods=["POST"])
def set_timing_settings():
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


@app.route("/practice/result", methods=["POST"])
def practice_result():
    data = request.get_json(silent=True) or {}
    letter = data.get("target", practice_target)
    is_correct = bool(data.get("correct", False))
    mode = data.get("mode", "send")
    expected_morse = data.get("expected_morse") or text_to_morse(letter)
    actual_morse = data.get("actual_morse") or get_current_key_morse().strip()
    answer = data.get("answer", "")
    timing_events = data.get("timing_events") or get_current_key_events()

    if mode not in practice_modes:
        mode = "send"

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

    return render_template(
        "progress.html",
        mode=mode,
        modes=practice_modes,
        overall=get_learning_overall(practice_letters),
        details=all_mode_details(practice_letters, practice_modes.keys()),
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

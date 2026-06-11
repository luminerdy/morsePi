from flask import Flask, render_template, request, redirect, url_for, jsonify
from gpiozero import Button, LED
from morse import text_to_morse, morse_to_text
from practice_progress import all_mode_details, choose_next_letter, mode_score, progress_summary, record_attempt
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
TONE_HZ = 700

DOT_SECONDS = 0.25
DASH_SECONDS = DOT_SECONDS * 3
SYMBOL_GAP_SECONDS = DOT_SECONDS
LETTER_GAP_SECONDS = DOT_SECONDS * 3
WORD_GAP_SECONDS = DOT_SECONDS * 7

DOT_DASH_THRESHOLD_SECONDS = 0.40
LETTER_GAP_THRESHOLD_SECONDS = 0.80
WORD_GAP_THRESHOLD_SECONDS = 1.50

# -----------------------------
# USB speaker audio settings
# -----------------------------
SAMPLE_RATE = 44100
DEFAULT_STATION_VOLUME = 0.35

# Your USB speaker showed up as:
# card 3: UACDemoV10 [UACDemoV1.0], device 0: USB Audio
AUDIO_DEVICE = os.environ.get("MORSE_AUDIO_DEVICE", "plughw:3,0")

# -----------------------------
# App state
# -----------------------------
last_message = ""
last_morse = ""

station_volume = DEFAULT_STATION_VOLUME

press_started_at = None
last_release_at = None

current_letter = ""
current_morse = ""

key_tone_process = None

practice_letters = ["E", "T", "A", "N", "I", "M"]
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
    }
}

key_lock = threading.Lock()
output_lock = threading.Lock()


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
        return

    key_tone_process = subprocess.Popen(
        [
            "speaker-test",
            "-D", AUDIO_DEVICE,
            "-t", "sine",
            "-f", str(TONE_HZ)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


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

    key_tone_process = None


# -----------------------------
# USB speaker audio helpers
# -----------------------------
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


def morse_to_audio_samples(morse: str, volume: float):
    samples = []

    for character in morse:
        if character == ".":
            add_tone(samples, TONE_HZ, DOT_SECONDS, volume)
            add_silence(samples, SYMBOL_GAP_SECONDS)

        elif character == "-":
            add_tone(samples, TONE_HZ, DASH_SECONDS, volume)
            add_silence(samples, SYMBOL_GAP_SECONDS)

        elif character == " ":
            add_silence(samples, LETTER_GAP_SECONDS)

        elif character == "/":
            add_silence(samples, WORD_GAP_SECONDS)

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
    samples = morse_to_audio_samples(morse, volume)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        wav_path = temp_file.name

    try:
        write_wav_file(wav_path, samples)

        # Plays through the configured Raspberry Pi USB speaker.
        subprocess.run(
            ["aplay", "-D", AUDIO_DEVICE, wav_path],
            check=False
        )

    finally:
        try:
            os.remove(wav_path)
        except FileNotFoundError:
            pass


# -----------------------------
# Station output helpers
# -----------------------------
def flash_morse_led(morse: str):
    try:
        for character in morse:
            if character == ".":
                led_on()
                sleep(DOT_SECONDS)
                led_off()
                sleep(SYMBOL_GAP_SECONDS)

            elif character == "-":
                led_on()
                sleep(DASH_SECONDS)
                led_off()
                sleep(SYMBOL_GAP_SECONDS)

            elif character == " ":
                sleep(LETTER_GAP_SECONDS)

            elif character == "/":
                sleep(WORD_GAP_SECONDS)

    finally:
        led_off()


def play_morse_on_station(morse: str):
    """
    Plays Morse on the Raspberry Pi station:
    - USB speaker for sound
    - LED for visual Morse flashing
    """
    with output_lock:
        volume = station_volume

        led_thread = threading.Thread(target=flash_morse_led, args=(morse,))
        led_thread.daemon = True
        led_thread.start()

        try:
            play_morse_usb_speaker(morse, volume)
        finally:
            led_off()


def play_in_background(morse: str):
    thread = threading.Thread(target=play_morse_on_station, args=(morse,))
    thread.daemon = True
    thread.start()


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
    global press_started_at, last_release_at, current_letter, current_morse

    now = time()

    with key_lock:
        if last_release_at is not None:
            gap = now - last_release_at
            gap_type = classify_gap(gap)

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
    global press_started_at, last_release_at, current_letter

    now = time()

    led_off()
    stop_key_tone()

    with key_lock:
        if press_started_at is None:
            return

        duration = now - press_started_at
        symbol = "." if duration < DOT_DASH_THRESHOLD_SECONDS else "-"

        current_letter += symbol
        press_started_at = None
        last_release_at = now


key.when_pressed = on_key_down
key.when_released = on_key_up


def get_current_key_morse():
    with key_lock:
        return (current_morse + current_letter).strip()


def clear_key_state():
    global current_letter, current_morse, last_release_at, press_started_at

    with key_lock:
        current_letter = ""
        current_morse = ""
        last_release_at = None
        press_started_at = None


def get_practice_mode():
    mode = request.values.get("mode", "send")

    if request.is_json:
        data = request.get_json(silent=True) or {}
        mode = data.get("mode", mode)

    return mode if mode in practice_modes else "send"


def get_read_choices(target):
    choices = [target]
    others = [letter for letter in practice_letters if letter != target]
    choices.extend(random.sample(others, min(3, len(others))))
    return random.sample(choices, len(choices))


def choose_new_practice_target(mode="send"):
    global practice_target, practice_feedback

    practice_target = choose_next_letter(practice_letters, practice_target, mode)
    practice_feedback = ""
    clear_key_state()


def station_volume_percent():
    return int(station_volume * 100)


# -----------------------------
# Main routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    global last_message, last_morse

    if request.method == "POST":
        last_message = request.form.get("message", "")
        last_morse = text_to_morse(last_message)

    return render_template(
        "index.html",
        message=last_message,
        morse=last_morse,
        station_volume_percent=station_volume_percent()
    )


@app.route("/play", methods=["POST"])
def play():
    if last_morse:
        play_in_background(last_morse)

    return redirect(url_for("index"))


@app.route("/station-volume", methods=["POST"])
def set_station_volume():
    global station_volume

    try:
        volume_percent = int(request.form.get("station_volume", "35"))
    except ValueError:
        volume_percent = 35

    volume_percent = max(0, min(volume_percent, 100))
    station_volume = volume_percent / 100.0

    return redirect(url_for("index"))


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
    mode = get_practice_mode()
    expected_morse = text_to_morse(practice_target)

    return render_template(
        "practice.html",
        mode=mode,
        modes=practice_modes,
        target=practice_target,
        expected_morse=expected_morse,
        read_choices=get_read_choices(practice_target),
        feedback=practice_feedback,
        progress=progress_summary(practice_letters, mode),
        score=mode_score(practice_letters, mode),
        progress_label=practice_modes[mode]["progress_label"]
    )


@app.route("/practice/new", methods=["POST"])
def practice_new():
    mode = get_practice_mode()
    choose_new_practice_target(mode)
    return redirect(url_for("practice", mode=mode))


@app.route("/practice/next", methods=["POST"])
def practice_next():
    mode = get_practice_mode()
    choose_new_practice_target(mode)

    return jsonify({
        "mode": mode,
        "target": practice_target,
        "expected_morse": text_to_morse(practice_target),
        "read_choices": get_read_choices(practice_target),
        "progress": progress_summary(practice_letters, mode),
        "score": mode_score(practice_letters, mode)
    })


@app.route("/practice/retry", methods=["POST"])
def practice_retry():
    mode = get_practice_mode()
    clear_key_state()

    return jsonify({
        "mode": mode,
        "target": practice_target,
        "expected_morse": text_to_morse(practice_target),
        "read_choices": get_read_choices(practice_target),
        "progress": progress_summary(practice_letters, mode),
        "score": mode_score(practice_letters, mode)
    })


@app.route("/practice/result", methods=["POST"])
def practice_result():
    data = request.get_json(silent=True) or {}
    letter = data.get("target", practice_target)
    is_correct = bool(data.get("correct", False))
    mode = data.get("mode", "send")

    if mode not in practice_modes:
        mode = "send"

    if letter not in practice_letters:
        return jsonify({
            "status": "ignored",
            "progress": progress_summary(practice_letters, mode),
            "score": mode_score(practice_letters, mode)
        })

    record_attempt(letter, is_correct, practice_letters, mode)

    return jsonify({
        "status": "recorded",
        "progress": progress_summary(practice_letters, mode),
        "score": mode_score(practice_letters, mode)
    })


@app.route("/progress")
def progress():
    mode = get_practice_mode()

    return render_template(
        "progress.html",
        mode=mode,
        modes=practice_modes,
        details=all_mode_details(practice_letters, practice_modes.keys())
    )


@app.route("/practice/play", methods=["POST"])
def practice_play():
    expected_morse = text_to_morse(practice_target)
    play_in_background(expected_morse)
    return redirect(url_for("practice"))


@app.route("/practice/check", methods=["POST"])
def practice_check():
    global practice_feedback

    expected_morse = text_to_morse(practice_target).strip()
    actual_morse = get_current_key_morse().strip()

    if not actual_morse:
        practice_feedback = "Tap the telegraph key first, then check your answer."

    elif actual_morse == expected_morse:
        record_attempt(practice_target, True, practice_letters, "send")
        practice_feedback = f"Great job! You tapped {practice_target} correctly."

    else:
        record_attempt(practice_target, False, practice_letters, "send")
        practice_feedback = (
            f"Good try. I heard {actual_morse}, but {practice_target} is {expected_morse}. "
            "Try again and listen to the rhythm."
        )

    return redirect(url_for("practice"))


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        stop_key_tone()
        led_off()
        key.close()
        led.close()

from flask import Flask, render_template, request, redirect, url_for, jsonify
from gpiozero import Button, LED, TonalBuzzer
from gpiozero.tones import Tone
from morse import text_to_morse, morse_to_text
from morse_output import play_morse
from time import time
import threading

app = Flask(__name__)

# -----------------------------
# GPIO setup
# -----------------------------
KEY_GPIO = 17
LED_GPIO = 27
BUZZER_GPIO = 18

TONE_HZ = 700

DOT_DASH_THRESHOLD_SECONDS = 0.40
LETTER_GAP_THRESHOLD_SECONDS = 0.80
WORD_GAP_THRESHOLD_SECONDS = 1.50

key = Button(KEY_GPIO, pull_up=True, bounce_time=0.03)
led = LED(LED_GPIO)
buzzer = TonalBuzzer(BUZZER_GPIO)

# -----------------------------
# App state
# -----------------------------
last_message = ""
last_morse = ""

press_started_at = None
last_release_at = None

current_letter = ""
current_morse = ""

key_lock = threading.Lock()


def tone_on():
    led.on()
    buzzer.play(Tone(TONE_HZ))


def tone_off():
    led.off()
    buzzer.stop()


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

    tone_on()


def on_key_up():
    global press_started_at, last_release_at, current_letter

    now = time()
    tone_off()

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


def play_in_background(morse):
    thread = threading.Thread(target=play_morse, args=(morse,))
    thread.daemon = True
    thread.start()


@app.route("/", methods=["GET", "POST"])
def index():
    global last_message, last_morse

    if request.method == "POST":
        last_message = request.form.get("message", "")
        last_morse = text_to_morse(last_message)

    return render_template(
        "index.html",
        message=last_message,
        morse=last_morse
    )


@app.route("/play", methods=["POST"])
def play():
    if last_morse:
        play_in_background(last_morse)

    return redirect(url_for("index"))


@app.route("/live-key")
def live_key():
    with key_lock:
        full_morse = (current_morse + current_letter).strip()

    decoded = morse_to_text(full_morse) if full_morse else ""

    return jsonify({
        "morse": full_morse,
        "decoded": decoded
    })


@app.route("/clear-key", methods=["POST"])
def clear_key():
    global current_letter, current_morse, last_release_at

    with key_lock:
        current_letter = ""
        current_morse = ""
        last_release_at = None

    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        tone_off()
        key.close()
        led.close()
        buzzer.close()

from gpiozero import Button
from signal import pause
from time import time

KEY_GPIO = 17

# Short press = dot, long press = dash
DOT_DASH_THRESHOLD_SECONDS = 0.25

key = Button(KEY_GPIO, pull_up=True, bounce_time=0.02)

press_started_at = None


def on_key_down():
    global press_started_at
    press_started_at = time()
    print("KEY DOWN")


def on_key_up():
    global press_started_at

    if press_started_at is None:
        return

    duration = time() - press_started_at
    symbol = "." if duration < DOT_DASH_THRESHOLD_SECONDS else "-"

    print(f"KEY UP   duration={duration:.3f}s   symbol={symbol}")

    press_started_at = None


key.when_pressed = on_key_down
key.when_released = on_key_up

print("Telegraph key test running.")
print("Tap short for dot, hold longer for dash.")
print("Press Ctrl+C to stop.")

pause()

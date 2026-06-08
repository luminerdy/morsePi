from gpiozero import Button, LED, TonalBuzzer
from gpiozero.tones import Tone
from signal import pause
from time import time

KEY_GPIO = 17
LED_GPIO = 27
BUZZER_GPIO = 18

TONE_HZ = 700
DOT_DASH_THRESHOLD_SECONDS = 0.40

key = Button(KEY_GPIO, pull_up=True, bounce_time=0.03)
led = LED(LED_GPIO)
buzzer = TonalBuzzer(BUZZER_GPIO)

press_started_at = None


def on_key_down():
    global press_started_at

    press_started_at = time()
    led.on()
    buzzer.play(Tone(TONE_HZ))

    print("KEY DOWN")


def on_key_up():
    global press_started_at

    led.off()
    buzzer.stop()

    if press_started_at is None:
        return

    duration = time() - press_started_at
    symbol = "." if duration < DOT_DASH_THRESHOLD_SECONDS else "-"

    print(f"KEY UP   duration={duration:.3f}s   symbol={symbol}")

    press_started_at = None


key.when_pressed = on_key_down
key.when_released = on_key_up

print("Telegraph key + LED + passive buzzer test running.")
print("Press the key: LED should turn on and buzzer should beep.")
print("Short tap = dot, long hold = dash.")
print("Press Ctrl+C to stop.")

try:
    pause()
except KeyboardInterrupt:
    led.off()
    buzzer.stop()
    print("\nStopped.")

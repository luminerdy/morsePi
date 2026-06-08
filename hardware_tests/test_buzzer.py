from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

BUZZER_GPIO = 18

buzzer = TonalBuzzer(BUZZER_GPIO)

print("Passive piezo buzzer test on GPIO18.")
print("Playing 700 Hz beeps. Press Ctrl+C to stop.")

try:
    while True:
        print("BEEP")
        buzzer.play(Tone(700))
        sleep(0.25)
        buzzer.stop()
        sleep(0.25)

except KeyboardInterrupt:
    buzzer.stop()
    print("\nBuzzer test stopped.")

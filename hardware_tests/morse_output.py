from gpiozero import LED, TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

LED_GPIO = 27
BUZZER_GPIO = 18

TONE_HZ = 700

DOT_SECONDS = 0.25
DASH_SECONDS = DOT_SECONDS * 3
SYMBOL_GAP_SECONDS = DOT_SECONDS
LETTER_GAP_SECONDS = DOT_SECONDS * 3
WORD_GAP_SECONDS = DOT_SECONDS * 7

led = LED(LED_GPIO)
buzzer = TonalBuzzer(BUZZER_GPIO)


def tone_on():
    led.on()
    buzzer.play(Tone(TONE_HZ))


def tone_off():
    led.off()
    buzzer.stop()


def play_symbol(symbol: str):
    if symbol == ".":
        tone_on()
        sleep(DOT_SECONDS)
        tone_off()
        sleep(SYMBOL_GAP_SECONDS)

    elif symbol == "-":
        tone_on()
        sleep(DASH_SECONDS)
        tone_off()
        sleep(SYMBOL_GAP_SECONDS)


def play_morse(morse: str):
    try:
        for character in morse:
            if character in [".", "-"]:
                play_symbol(character)

            elif character == " ":
                sleep(LETTER_GAP_SECONDS)

            elif character == "/":
                sleep(WORD_GAP_SECONDS)

    finally:
        tone_off()

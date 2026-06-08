from gpiozero import LED
from time import sleep

LED_GPIO = 27

DOT_SECONDS = 0.25
DASH_SECONDS = DOT_SECONDS * 3
SYMBOL_GAP_SECONDS = DOT_SECONDS
LETTER_GAP_SECONDS = DOT_SECONDS * 3
WORD_GAP_SECONDS = DOT_SECONDS * 7

MORSE_CODE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..",
    "E": ".", "F": "..-.", "G": "--.", "H": "....",
    "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.",
    "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..",
    "9": "----.", "0": "-----"
}

led = LED(LED_GPIO)


def text_to_morse(text: str) -> str:
    words = text.upper().split()
    morse_words = []

    for word in words:
        letters = []
        for character in word:
            if character in MORSE_CODE:
                letters.append(MORSE_CODE[character])
        morse_words.append(" ".join(letters))

    return " / ".join(morse_words)


def flash_symbol(symbol: str):
    if symbol == ".":
        led.on()
        sleep(DOT_SECONDS)
        led.off()
        sleep(SYMBOL_GAP_SECONDS)

    elif symbol == "-":
        led.on()
        sleep(DASH_SECONDS)
        led.off()
        sleep(SYMBOL_GAP_SECONDS)


def flash_morse(morse: str):
    for character in morse:
        if character in [".", "-"]:
            flash_symbol(character)

        elif character == " ":
            sleep(LETTER_GAP_SECONDS)

        elif character == "/":
            sleep(WORD_GAP_SECONDS)


if __name__ == "__main__":
    print("Morse LED flasher on GPIO27.")
    print("Type a message and watch the LED flash it.")
    print("Press Ctrl+C to quit.")

    try:
        while True:
            message = input("\nMessage: ")
            morse = text_to_morse(message)

            print("Morse:", morse)
            flash_morse(morse)

    except KeyboardInterrupt:
        led.off()
        print("\nStopped.")

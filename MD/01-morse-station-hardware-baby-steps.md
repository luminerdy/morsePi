# Morse Station Hardware Baby Steps

Build a Raspberry Pi Morse code station one small step at a time.

This guide walks you through the hardware foundation for **Pappy's Internet Telegraph**. By the end, you will have a Raspberry Pi that can:

- Read a real telegraph key
- Flash an LED
- Play a tone with a passive piezo buzzer
- Combine the key, LED, and buzzer into a simple Morse practice station

The web app comes later in a separate tutorial.

---

## 1. What You Are Building

A Morse code station has three basic parts:

| Part | What it does |
|---|---|
| Telegraph key | Lets you tap dots and dashes |
| LED | Gives visual feedback |
| Passive piezo buzzer | Makes Morse beeps |

The goal is to build and test each part separately before combining them.

This is an important engineering habit:

> Build one small thing. Test it. Then add the next small thing.

---

## 2. Hardware Needed

You need:

- Raspberry Pi 4
- microSD card with Raspberry Pi OS
- TGKY01 telegraph key, or similar simple key/switch
- LED
- 220Ω to 330Ω resistor for the LED
- Passive piezo buzzer
- Jumper wires
- Breadboard, optional but helpful

Optional:

- Extra resistor, 100Ω to 330Ω, for the passive buzzer
- USB speaker for a later tutorial

---

## 3. GPIO Pin Plan

We will use this layout:

| Function | GPIO | Physical Pin | Notes |
|---|---:|---:|---|
| Telegraph key input | GPIO17 | Pin 11 | Reads key press |
| Key ground | GND | Pin 9 | Ground |
| LED output | GPIO27 | Pin 13 | Flashes for key/Morse |
| LED ground | GND | Pin 14 | Ground |
| Passive piezo buzzer | GPIO18 | Pin 12 | Plays tone |
| Buzzer ground | GND | Pin 20 | Ground |

Raspberry Pi pin numbers can be confusing. In this guide:

- **GPIO number** means the Broadcom GPIO number used in Python.
- **Physical pin** means the actual numbered pin on the Raspberry Pi header.

For example:

```text
GPIO17 = physical pin 11
GPIO27 = physical pin 13
GPIO18 = physical pin 12
```

---

## 4. Set Up the Project Folder

Log in to your Raspberry Pi and create a project folder:

```bash
mkdir -p ~/morse-station
cd ~/morse-station
```

Install the Python packages we need:

```bash
sudo apt update
sudo apt install -y python3-gpiozero python3-lgpio python3-rpi.gpio
```

We are using system Python for this project to keep GPIO access simple.

---

# Part 1: Test the Telegraph Key

## 5. Wire the Telegraph Key

A telegraph key works like a button.

Wire it like this:

```text
GPIO17 / physical pin 11  → one side of telegraph key
GND / physical pin 9      → other side of telegraph key
```

Simple diagram:

```text
Pi GPIO17 ───── Telegraph Key ───── Pi GND
```

The Python program will use the Raspberry Pi's internal pull-up resistor.

That means:

- Key not pressed = GPIO reads high
- Key pressed = GPIO connects to ground

---

## 6. Create `key_reader.py`

Create the file:

```bash
nano key_reader.py
```

Paste this code:

```python
from gpiozero import Button
from signal import pause
from time import time

KEY_GPIO = 17

# Beginner setting:
# short press = dot
# long press = dash
DOT_DASH_THRESHOLD_SECONDS = 0.40

key = Button(KEY_GPIO, pull_up=True, bounce_time=0.03)

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
print("Short tap = dot")
print("Long hold = dash")
print("Press Ctrl+C to stop.")

pause()
```

Save and exit:

```text
Ctrl+O
Enter
Ctrl+X
```

---

## 7. Run the Key Test

Run:

```bash
python3 key_reader.py
```

Tap the telegraph key quickly.

You should see something like:

```text
KEY DOWN
KEY UP   duration=0.120s   symbol=.
```

Hold the key longer.

You should see something like:

```text
KEY DOWN
KEY UP   duration=0.650s   symbol=-
```

If this works, the Raspberry Pi can read your telegraph key.

Stop the program with:

```text
Ctrl+C
```

---

## 8. What You Learned

You learned that Morse input can be measured by time:

| Input | Meaning |
|---|---|
| Short press | Dot |
| Long press | Dash |

For beginners, we use a forgiving rule:

```text
less than 0.40 seconds = dot
0.40 seconds or more   = dash
```

Later, the program can adjust this timing for each student.

---

# Part 2: Test the LED

## 9. Wire the LED

Use a resistor with the LED.

Wire it like this:

```text
GPIO27 / physical pin 13  → resistor → LED long leg (+)
LED short leg (-)         → GND / physical pin 14
```

LED leg reminder:

| LED leg | Meaning |
|---|---|
| Long leg | Positive / anode |
| Short leg | Negative / cathode / ground |

Simple diagram:

```text
GPIO27 ─── resistor ─── LED +
GND    ───────────────── LED -
```

---

## 10. Create `test_led.py`

Create the file:

```bash
nano test_led.py
```

Paste this code:

```python
from gpiozero import LED
from time import sleep

LED_GPIO = 27

led = LED(LED_GPIO)

print("LED test running on GPIO27.")
print("Press Ctrl+C to stop.")

try:
    while True:
        print("LED ON")
        led.on()
        sleep(0.5)

        print("LED OFF")
        led.off()
        sleep(0.5)

except KeyboardInterrupt:
    led.off()
    print("\nLED test stopped.")
```

---

## 11. Run the LED Test

Run:

```bash
python3 test_led.py
```

The LED should blink on and off.

If it does not blink, check:

- Is the LED backward?
- Is the resistor connected?
- Is the LED connected to GPIO27 / physical pin 13?
- Is the ground connected to physical pin 14?

Stop with:

```text
Ctrl+C
```

---

# Part 3: Combine the Key and LED

## 12. Why Combine Them?

Now we know:

- The key works by itself.
- The LED works by itself.

Next, we combine them.

When the key is pressed, the LED should turn on.

When the key is released, the LED should turn off.

---

## 13. Create `key_reader_led.py`

Create the file:

```bash
nano key_reader_led.py
```

Paste this code:

```python
from gpiozero import Button, LED
from signal import pause
from time import time

KEY_GPIO = 17
LED_GPIO = 27

DOT_DASH_THRESHOLD_SECONDS = 0.40

key = Button(KEY_GPIO, pull_up=True, bounce_time=0.03)
led = LED(LED_GPIO)

press_started_at = None


def on_key_down():
    global press_started_at
    press_started_at = time()
    led.on()
    print("KEY DOWN")


def on_key_up():
    global press_started_at

    led.off()

    if press_started_at is None:
        return

    duration = time() - press_started_at
    symbol = "." if duration < DOT_DASH_THRESHOLD_SECONDS else "-"

    print(f"KEY UP   duration={duration:.3f}s   symbol={symbol}")

    press_started_at = None


key.when_pressed = on_key_down
key.when_released = on_key_up

print("Telegraph key + LED test running.")
print("Press the key and the LED should turn on.")
print("Short tap = dot, long hold = dash.")
print("Press Ctrl+C to stop.")

pause()
```

---

## 14. Run the Key + LED Test

Run:

```bash
python3 key_reader_led.py
```

Press the key.

You should see:

```text
KEY DOWN
```

And the LED should turn on.

Release the key.

You should see:

```text
KEY UP   duration=0.130s   symbol=.
```

And the LED should turn off.

Stop with:

```text
Ctrl+C
```

---

# Part 4: Test the Passive Piezo Buzzer

## 15. Wire the Passive Piezo Buzzer

Wire the passive piezo buzzer like this:

```text
GPIO18 / physical pin 12  → piezo buzzer +
GND / physical pin 20     → piezo buzzer -
```

Optional:

```text
GPIO18 → 100Ω to 330Ω resistor → piezo buzzer +
GND    → piezo buzzer -
```

A passive piezo buzzer needs a tone signal. We will use a 700 Hz tone.

---

## 16. Create `test_buzzer.py`

Create the file:

```bash
nano test_buzzer.py
```

Paste this code:

```python
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

BUZZER_GPIO = 18
TONE_HZ = 700

buzzer = TonalBuzzer(BUZZER_GPIO)

print("Passive piezo buzzer test on GPIO18.")
print("Playing 700 Hz beeps. Press Ctrl+C to stop.")

try:
    while True:
        print("BEEP")
        buzzer.play(Tone(TONE_HZ))
        sleep(0.25)
        buzzer.stop()
        sleep(0.25)

except KeyboardInterrupt:
    buzzer.stop()
    print("\nBuzzer test stopped.")
```

---

## 17. Run the Buzzer Test

Run:

```bash
python3 test_buzzer.py
```

You should hear short beeps.

If you do not hear anything, check:

- Is the buzzer passive or active?
- Is the positive side connected to GPIO18 / physical pin 12?
- Is the negative side connected to ground?
- Try reversing the buzzer wires if needed.

Stop with:

```text
Ctrl+C
```

---

# Part 5: Combine Key + LED + Buzzer

## 18. Why This Step Matters

This is the first version that feels like a real Morse station.

When you press the key:

- The LED turns on.
- The buzzer makes a tone.
- The program measures the press.

When you release the key:

- The LED turns off.
- The buzzer stops.
- The program prints dot or dash.

---

## 19. Create `key_reader_led_buzzer.py`

Create the file:

```bash
nano key_reader_led_buzzer.py
```

Paste this code:

```python
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
```

---

## 20. Run the Combined Test

Run:

```bash
python3 key_reader_led_buzzer.py
```

Try a short tap.

You should get:

```text
KEY DOWN
KEY UP   duration=0.120s   symbol=.
```

Try a longer hold.

You should get:

```text
KEY DOWN
KEY UP   duration=0.620s   symbol=-
```

You should also see and hear:

- LED on while key is pressed
- Buzzer on while key is pressed
- LED and buzzer off when key is released

Stop with:

```text
Ctrl+C
```

---

# Part 6: Play a Typed Message as Morse

## 21. What This Script Does

Now we will type a message like:

```text
HI
```

The program will convert it to Morse:

```text
.... ..
```

Then it will flash the LED and beep the buzzer.

---

## 22. Create `morse_output.py`

Create the file:

```bash
nano morse_output.py
```

Paste this code:

```python
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
buzzer = TonalBuzzer(BUZZER_GPIO)


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
    for character in morse:
        if character in [".", "-"]:
            play_symbol(character)

        elif character == " ":
            sleep(LETTER_GAP_SECONDS)

        elif character == "/":
            sleep(WORD_GAP_SECONDS)


if __name__ == "__main__":
    print("Morse LED + buzzer output test.")
    print("Type a message and hear/watch it in Morse.")
    print("Press Ctrl+C to quit.")

    try:
        while True:
            message = input("\nMessage: ")
            morse = text_to_morse(message)

            print("Morse:", morse)
            play_morse(morse)

    except KeyboardInterrupt:
        tone_off()
        print("\nStopped.")
```

---

## 23. Run the Morse Output Test

Run:

```bash
python3 morse_output.py
```

Type:

```text
HI
```

Expected Morse:

```text
.... ..
```

The LED and buzzer should play:

```text
dit dit dit dit    dit dit
```

Try:

```text
SOS
```

Expected Morse:

```text
... --- ...
```

Stop with:

```text
Ctrl+C
```

---

# Part 7: Understanding Morse Timing

## 24. Morse Timing Basics

Morse timing is based on one unit.

| Morse part | Timing |
|---|---:|
| Dot | 1 unit |
| Dash | 3 units |
| Gap between dots/dashes | 1 unit |
| Gap between letters | 3 units |
| Gap between words | 7 units |

For beginner mode, we use:

```python
DOT_SECONDS = 0.25
DASH_SECONDS = DOT_SECONDS * 3
SYMBOL_GAP_SECONDS = DOT_SECONDS
LETTER_GAP_SECONDS = DOT_SECONDS * 3
WORD_GAP_SECONDS = DOT_SECONDS * 7
```

That means:

| Morse part | Beginner timing |
|---|---:|
| Dot | 250 ms |
| Dash | 750 ms |
| Letter gap | 750 ms |
| Word gap | 1750 ms |

---

## 25. Beginner Letters

Start with these letters:

| Letter | Morse | Say it |
|---|---|---|
| E | `.` | dit |
| T | `-` | dah |
| A | `.-` | dit dah |
| N | `-.` | dah dit |
| I | `..` | dit dit |
| M | `--` | dah dah |

These are good first letters because they teach the difference between dots and dashes.

---

# Part 8: Troubleshooting

## 26. GPIO Busy Error

If you see an error like:

```text
GPIO busy
```

Another Python script may still be using the GPIO pins.

Stop old scripts:

```bash
pkill -f key_reader.py
pkill -f key_reader_led.py
pkill -f key_reader_led_buzzer.py
pkill -f test_led.py
pkill -f test_buzzer.py
pkill -f morse_output.py
```

Then run your script again.

---

## 27. LED Does Not Light

Check:

- LED direction: long leg should go toward GPIO through the resistor
- Short leg should go to ground
- Resistor is connected
- Correct pin: GPIO27 / physical pin 13
- Ground pin: physical pin 14

---

## 28. Buzzer Does Not Beep

Check:

- Is it a passive piezo buzzer?
- Is positive connected to GPIO18 / physical pin 12?
- Is negative connected to ground?
- Try reversing the buzzer wires
- Try a different tone, such as 500 Hz or 1000 Hz

---

## 29. Key Does Not Respond

Check:

- One side of key goes to GPIO17 / physical pin 11
- Other side goes to GND / physical pin 9
- Make sure your Python script uses `pull_up=True`
- Try another ground pin

---

# Part 9: Checkpoint

Before moving to the web app tutorial, confirm that each script works:

| Script | What it proves |
|---|---|
| `key_reader.py` | Telegraph key input works |
| `test_led.py` | LED output works |
| `key_reader_led.py` | Key can control LED |
| `test_buzzer.py` | Passive piezo buzzer works |
| `key_reader_led_buzzer.py` | Key, LED, and buzzer work together |
| `morse_output.py` | Typed messages can play as Morse |

If all of these work, your hardware foundation is ready.

Next tutorial:

> Build the Flask web app for Pappy's Internet Telegraph.

---

## 30. What You Built

You built the hardware foundation for a Morse code learning station.

You can now:

- Tap a real telegraph key
- Detect dots and dashes in Python
- Flash an LED
- Play Morse beeps
- Convert typed messages into Morse output

This is the first big step toward building a personalized Morse code learning system.

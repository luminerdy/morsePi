# Pappy's Internet Telegraph — Project Requirements and Status

## 1. Project Summary

**Pappy's Internet Telegraph** is a Raspberry Pi-based Morse code learning station for 3rd–6th grade students.

The goal is to help students learn Morse code by using a real telegraph key, visual feedback, sound feedback, practice activities, student progress tracking, and eventually secure family messaging over the internet.

The project is intentionally being built in **baby steps** so students can understand each part before everything is combined into a web application.

Core learning idea:

```text
See Morse → Hear Morse → Tap Morse → Decode Morse → Send Morse
```

---

## 2. Primary Goals

The system should help students:

1. Learn Morse code letters, numbers, and simple messages.
2. Hear Morse code as beeps.
3. Tap Morse code using a physical telegraph key.
4. See immediate feedback from an LED and buzzer.
5. Practice with short, encouraging lessons.
6. Log in using a Morse code password.
7. Track individual progress over time.
8. Receive customized lessons based on progress.
9. Eventually send and receive secure family messages over the internet.

---

## 3. Current Hardware Platform

Current target hardware:

```text
Raspberry Pi 4, 2GB
TGKY01 telegraph key
LED with resistor
Passive piezo buzzer
USB speaker
Wi-Fi or Ethernet network connection
```

The Raspberry Pi is currently using system Python instead of a virtual environment. This keeps GPIO setup simpler for a dedicated project device.

---

## 4. Current GPIO Layout

| Function | GPIO | Physical Pin | Notes |
|---|---:|---:|---|
| Telegraph key input | GPIO17 | Pin 11 | Key acts like a button to ground |
| Telegraph key ground | GND | Pin 9 | Shared ground |
| Status LED | GPIO27 | Pin 13 | Visual key/Morse feedback |
| LED ground | GND | Pin 14 | Use resistor in series with LED |
| Passive piezo buzzer | GPIO18 | Pin 12 | Optional hardware test output |
| Buzzer ground | GND | Pin 20 | Shared ground |

Recommended wiring:

```text
GPIO17 / Pin 11 ─── Telegraph Key ─── GND / Pin 9
GPIO27 / Pin 13 ─── Resistor ─── LED + ; LED - ─── GND / Pin 14
GPIO18 / Pin 12 ─── Passive Piezo + ; Piezo - ─── GND / Pin 20
```

---

## 5. What Has Been Completed So Far

### 5.1 Raspberry Pi setup

Completed:

- Raspberry Pi OS installed.
- SSH access working.
- System Python being used.
- GPIO Zero and required GPIO packages installed through `apt`.
- Virtual environment removed because it added GPIO backend issues.

Key decision:

```text
Use system Python on the Raspberry Pi for this project.
```

Reason:

- Simpler for a dedicated learning station.
- GPIO libraries work more reliably.
- Easier for students/helpers to run.

---

### 5.2 Telegraph key test

Completed:

- Telegraph key connected to GPIO17 and GND.
- `key_reader.py` created.
- Script detects key press and release.
- Script classifies short taps as dots and longer holds as dashes.

Current beginner timing:

```text
Less than 0.40 seconds = dot
0.40 seconds or more   = dash
```

This validates the physical key input.

---

### 5.3 LED test

Completed:

- LED connected to GPIO27 through a resistor.
- Basic LED blink test created.
- LED turns on and off from Python.

Purpose:

- Provides visual feedback.
- Helps students see Morse timing.
- Useful before audio is working.

---

### 5.4 Key + LED integration

Completed:

- Combined telegraph key input with LED output.
- LED turns on while the key is pressed.
- LED turns off when the key is released.
- Dot/dash duration is still printed to the terminal.

This created the first real physical Morse interaction:

```text
press key → LED turns on → release key → dot/dash is detected
```

---

### 5.5 Passive piezo buzzer test

Completed:

- Passive piezo buzzer connected to GPIO18 and GND.
- Python script created to play a 700 Hz tone.
- Buzzer successfully produces Morse-style beeps.

Important design decision:

```text
Keep the passive piezo buzzer tests available for troubleshooting, but use the USB speaker for the current web app station audio.
```

---

### 5.6 Key + LED + buzzer integration

Completed:

- Telegraph key, LED, and passive piezo buzzer combined.
- When the key is pressed:

```text
LED turns on
buzzer plays tone
```

- When the key is released:

```text
LED turns off
buzzer stops
dot/dash is classified
```

This now feels like a working electronic telegraph station.

---

### 5.7 Text-to-Morse output test

Completed:

- Morse conversion code created.
- Typed messages can be converted to Morse.
- Morse can be played through LED and buzzer.

Example:

```text
Text:  HI
Morse: .... ..
```

Output:

```text
LED flashes four short blinks, pauses, then two short blinks.
Buzzer beeps at the same time.
```

---

### 5.8 Initial web app created

Completed:

- Flask web app created.
- Home page allows typed text to be converted to Morse.
- Morse code is displayed visually.
- Browser playback added using JavaScript/Web Audio.
- Pi station playback added using LED + piezo buzzer.
- Live telegraph key input appears in the web app.

Important Flask/GPIO decision:

```text
Run Flask with debug=False and use_reloader=False.
```

Reason:

- Flask debug reloader can start multiple processes.
- Multiple processes can claim the same GPIO pins.
- This caused GPIO busy errors earlier.

---

### 5.9 Practice Mode created

Completed:

- Practice page added.
- Student sees a beginner letter.
- Student can play the expected Morse.
- Student taps the Morse using the telegraph key.
- Web app shows live tapped Morse.
- Student can check the answer.
- App gives friendly feedback.

Current beginner letters:

```text
E = .
T = -
A = .-
N = -.
I = ..
M = --
```

Current Practice Mode flow:

```text
Show target letter
Show expected Morse
Student taps key
Display tapped Morse
Check expected vs actual
Show feedback
Try another letter
```

---

## 6. Current Software Files

Current project folder is expected to look similar to this:

```text
morse-station/
├── README.md
├── app.py
├── morse.py
├── config.example.env
├── requirements.txt
├── templates/
│   ├── index.html
│   └── practice.html
├── static/
│   ├── style.css
│   └── app.js
├── hardware_tests/
│   ├── key_reader.py
│   ├── test_led.py
│   ├── test_buzzer.py
│   ├── key_reader_led_buzzer.py
│   └── morse_output.py
├── archive/
├── docs/
└── systemd/
```

Recommended future repo structure:

```text
morse-station/
├── app.py
├── morse.py
├── hardware.py
├── db.py
├── auth.py
├── lessons.py
├── requirements.txt
├── templates/
├── static/
├── docs/
│   ├── PROJECT_REQUIREMENTS_AND_STATUS.md
│   └── tutorials/
│       └── 01-morse-station-hardware-baby-steps.md
└── hardware_tests/
    ├── key_reader.py
    ├── test_led.py
    ├── test_buzzer.py
    └── key_reader_led_buzzer.py
```

---

## 7. Core Functional Requirements

### FR-001: Text-to-Morse conversion

The system shall convert typed text into Morse code.

Example:

```text
HI PAPPY → .... .. / .--. .- .--. .--. -.--
```

---

### FR-002: Morse-to-text decoding

The system shall decode valid Morse code into text.

Example:

```text
.... .. → HI
```

---

### FR-003: Physical telegraph key input

The system shall read a physical telegraph key connected to GPIO17.

The key shall be treated as a button input using an internal pull-up resistor.

---

### FR-004: Dot/dash classification

The system shall classify key press duration as dot or dash.

Initial beginner timing:

```text
press < 0.40 seconds = dot
press >= 0.40 seconds = dash
```

---

### FR-005: LED visual output

The system shall flash an LED during Morse playback and key presses.

---

### FR-006: Piezo buzzer output

The system shall play Morse tones using a passive piezo buzzer.

Recommended starting tone:

```text
700 Hz
```

---

### FR-007: USB speaker output

The system shall support a USB speaker for better audio playback.

This is planned as a next hardware improvement.

---

### FR-008: Browser audio playback

The web app shall support playing Morse audio in the browser using JavaScript.

This allows audio playback from a laptop, tablet, or browser connected to the Pi web app.

---

### FR-009: Pi station playback

The web app shall support playing Morse on the Raspberry Pi station hardware using LED and piezo buzzer.

---

### FR-010: Live key display

The web app shall show live telegraph key input.

Example:

```text
You tapped: .-
Decoded: A
```

---

### FR-011: Practice Mode

The system shall provide a Practice Mode where students tap the Morse code for a displayed letter or word.

---

### FR-012: Friendly feedback

The system shall provide encouraging feedback.

Examples:

```text
Great job! You tapped A correctly.
Good try. I heard .., but A is .-. Try holding the dash longer.
```

---

## 8. Student Learning Requirements

### LRN-001: Learn by doing

Students shall learn Morse code by physically tapping, hearing, seeing, and decoding Morse.

---

### LRN-002: Start with simple letters

Initial lessons shall start with simple letters:

```text
E = .
T = -
A = .-
N = -.
I = ..
M = --
```

---

### LRN-003: Use dit/dah language

The system should teach rhythm using:

```text
dit = dot
dah = dash
```

Example:

```text
A = dit dah
N = dah dit
```

---

### LRN-004: Support short practice activities

Practice should be short and encouraging.

Good first activities:

```text
Tap this letter
Listen and choose
Copy the rhythm
Decode the word
Send a short message
```

---

### LRN-005: Avoid frustration

The system should avoid harsh failure messages.

Instead of:

```text
Wrong
```

Use:

```text
Good try. Listen again and try holding the dash longer.
```

---

## 9. Adaptive Timing Requirements

The system should eventually adapt to each student.

Initial timing modes:

| Mode | Dot Length | Dash Length | Best For |
|---|---:|---:|---|
| Slow Learner | 250 ms | 750 ms | Starting out |
| Normal Practice | 180 ms | 540 ms | Getting comfortable |
| Challenge | 120 ms | 360 ms | More realistic |

### ADAPT-001: Separate playback and input timing

The system shall track playback speed separately from tapping/input timing.

A student may be able to hear Morse faster than they can tap it.

---

### ADAPT-002: Gradual speed adjustment

The system should gradually adjust speed based on student success.

Example:

```text
If accuracy >= 85% over recent attempts, make timing slightly faster.
If accuracy < 60%, slow down or repeat the lesson.
```

---

### ADAPT-003: Identify weak skills

The system should identify patterns such as:

```text
dash too short
letter gap too short
confuses A and I
confuses N and T
needs more listening practice
needs more tapping practice
```

---

## 10. Student Profile and Login Requirements

### LOGIN-001: Student profiles

The system shall support individual student profiles.

Each profile should eventually store:

```text
student display name
current level
known letters
weak letters
strong letters
playback speed
input timing settings
practice history
message history
```

---

### LOGIN-002: Morse password login

Students shall log in by selecting their profile and tapping a Morse code password using the telegraph key.

Example:

```text
Password word: STAR
Morse password: ... - .- .-.
```

---

### LOGIN-003: Beginner and challenge login modes

The system should support:

```text
Beginner mode: shows the Morse password pattern
Challenge mode: hides the Morse password pattern
```

---

### LOGIN-004: Password security

The system shall not store plain-text passwords.

The system should store a salted hash of the normalized Morse password.

---

### LOGIN-005: Admin reset

An adult/admin shall be able to reset a student's Morse password.

---

## 11. Logging and Data Requirements

Logging is a foundational requirement and should be added early.

### LOG-001: Log all usage and progress

The system shall log:

```text
logins
login attempts
practice sessions
practice attempts
lesson starts
lesson completions
Morse playback
replays
hints used
messages created
messages sent
messages received
messages decoded
speed changes
lesson recommendations
admin resets
system events
```

---

### LOG-002: SQLite local storage

The system shall use SQLite for local storage.

Initial database:

```text
morse_station.db
```

Recommended initial tables:

```text
students
sessions
practice_attempts
system_events
```

Later tables:

```text
login_attempts
lessons
lesson_attempts
messages
student_letter_stats
```

---

### LOG-003: Practice attempt logging

Each practice attempt shall save:

```text
student_id
session_id
activity_type
expected_text
expected_morse
actual_morse
correct/incorrect
dot durations
dash durations
gap durations
playback speed
input threshold
hints used
replays used
timestamp
```

---

### LOG-004: Admin progress dashboard

The system should eventually provide an adult/admin progress view showing:

```text
total practice attempts
lessons completed
letters mastered
letters needing practice
average accuracy
current speed level
recent activity
recommended next lesson
```

---

### LOG-005: Student progress dashboard

The system should show students a kid-friendly progress dashboard.

Example:

```text
Morse Missions Completed: 4
Best Letters: E, T, I
Practice Next: A, N
Current Speed: Turtle Mode
```

---

## 12. LLM-Assisted Learning Requirements

LLM support should be added later, after logging and student progress tracking exist.

### LLM-001: Evaluate progress

The system may use an LLM to evaluate student progress and identify learning patterns.

The LLM may review structured learning data such as:

```text
known letters
weak letters
accuracy
dot timing
dash timing
gap timing
lesson history
recent attempts
```

---

### LLM-002: Generate customized learning plans

The system may use an LLM to create a custom lesson plan for each student.

Example:

```text
Today's Morse Mission:
Warm up with E and T.
Practice A and N.
Focus on holding dashes longer.
Decode the word TEAM.
Send Pappy a short message.
```

---

### LLM-003: Structured input and output

The system should send structured progress data to the LLM and receive structured lesson plans back.

Example input:

```json
{
  "student": "Liara",
  "grade_band": "3-4",
  "known_letters": ["E", "T", "I"],
  "weak_letters": ["A", "N"],
  "accuracy_last_10": 0.7,
  "common_issue": "dash_too_short"
}
```

Example output:

```json
{
  "title": "Space Signal Mission",
  "focus_skill": "Hold dashes longer",
  "warmup": ["E", "T"],
  "practice_letters": ["A", "N"],
  "practice_words": ["AT", "TEN", "MAN"],
  "coach_message": "Your dots are strong. Today we will practice making dashes longer."
}
```

---

### LLM-004: Guardrails

The system shall not rely only on the LLM for progression.

Rule-based guardrails should prevent:

```text
speed increasing too quickly
too many new letters at once
too-long messages for beginners
age-inappropriate content
unnecessary personal data being sent to the LLM
```

---

## 13. Messaging Requirements

Messaging is planned after the local learning station works well.

### MSG-001: Local messages

The system shall allow students to create simple messages and hear them in Morse.

---

### MSG-002: Inbox/outbox

The system should support a local inbox and outbox.

---

### MSG-003: Listen before reveal

Received messages should encourage decoding.

Example flow:

```text
New message from Pappy
Listen first
Try to decode
Reveal text
Reply
```

---

### MSG-004: Multiple stations

The system should eventually support multiple stations.

Example station names:

```text
pappy
liara
team-a
team-b
```

---

## 14. Secure Internet Messaging Requirements

This is a later phase.

### MQTT-001: MQTT protocol

The system should use MQTT for station-to-station messages.

---

### MQTT-002: AWS IoT Core

The system should support AWS IoT Core for secure MQTT messaging.

---

### MQTT-003: Topic structure

Example topics:

```text
morse/family/messages/to/pappy
morse/family/messages/to/liara
morse/family/messages/to/team-a
morse/family/broadcast
```

---

### MQTT-004: Secure device identity

Each station should have its own AWS IoT certificate.

---

### MQTT-005: Least privilege

Each station should only publish and subscribe to approved topics.

---

## 15. Current MVP Status

### Completed MVP items

| Item | Status |
|---|---|
| Raspberry Pi configured | Complete |
| System Python and GPIO working | Complete |
| Telegraph key input | Complete |
| LED output | Complete |
| Passive piezo buzzer output | Complete |
| Key + LED + buzzer integration | Complete |
| Morse conversion | Complete |
| Text-to-Morse web page | Complete |
| Browser playback | Complete |
| Pi hardware playback | Complete |
| Live key display in web app | Complete |
| Basic Practice Mode | Complete |
| USB speaker integration | Complete |
| GitHub repo setup | Complete |
| Fresh Pi setup guide | Complete |
| Pi app autostart | Complete with user systemd service |
| Pi browser autostart | Complete for Labwc desktop session |
| Continuous Send practice loop | Complete |
| Learn practice mode | Complete |
| Read practice mode | Complete |
| Listen practice mode | Complete |
| JSON progress tracking | Complete |
| Overall Operator Level and rank | Complete |
| Unlocked-letter progress display | Started |
| Student score card | Complete |
| Detailed Progress page | Complete |
| Browser sound recovery control | Complete |
| Home playback stop controls | Complete |

---

### MVP items still remaining

| Item | Status |
|---|---|
| SQLite database | Deferred |
| Log practice attempts | Started with JSON progress |
| Student profile selection | Not started |
| Morse password login | Not started |
| Progress dashboard | Started |
| Listen progress tracking | Complete |
| Learn progress tracking | Complete |
| Enforced letter unlocking | Not started |
| Better timing feedback | Not started |
| Refactor hardware code | Not started |

---

## 16. Recommended Next Steps

### Step 1: Test the core practice loops

Next testing milestone:

```text
Start from reset practice progress.
Run Learn, Send, Read, and Listen in a real practice session.
Confirm the browser audio is comfortable for beginners.
Confirm the browser Test Sound button wakes audio when sound stops.
Confirm Stop Here cancels long browser playback from the Home page.
Confirm Stop Station cancels long Pi speaker/LED playback from the Home page.
Confirm Replay is easy to find and use.
Confirm Progress details make sense after a few attempts.
Confirm Operator Level and unlocked letters feel fun and encouraging.
Tune rank names and unlock thresholds after student testing.
Decide whether wrong Listen answers should reveal the letter immediately or invite one replay first.
Decide whether Learn should score progress the same way as Send or be more forgiving.
```

---

### Step 2: Refine Learn mode

Learn mode has a first working version for first exposure and reinforcement.

Next refinement should decide:

```text
Whether Learn should score progress like Send or use gentler scoring
Whether Learn should auto-play when a new prompt appears
Whether feedback should be shorter for younger students
Whether the Play Code button label is clear enough
```

---

### Step 3: Add Mixed mode

Use current progress data to rotate between weak mode+letter combinations.

First version should be rule-based.

---

### Step 4: Add student profiles

Add a simple profile selection page.

First version can include:

```text
Guest
Pappy
Student 1
Student 2
```

---

### Step 5: Add Morse password login

Add student login using a Morse-tapped password.

---

### Step 6: Improve Practice Mode

Add:

```text
dot/dash timing feedback
letter gap feedback
more beginner letters
word practice
copy-rhythm activity
```

---

### Step 7: Add adaptive lessons

Use logged data to recommend next practice.

First version should be rule-based.

Later version may use an LLM.

---

### Step 8: Add secure messaging

Add local messaging first.

Then add AWS IoT MQTT.

---

## 17. Important Design Decisions

### Use baby steps

The project should continue to be built in small, testable steps.

Recommended pattern:

```text
Build one thing
Test it
Combine it with the previous thing
Test again
Document it
Then move on
```

---

### Keep hardware tests separate

Hardware tests should stay available even after the web app exists.

Examples:

```text
key_reader.py
test_led.py
test_buzzer.py
key_reader_led_buzzer.py
```

These are useful for troubleshooting.

---

### Only one owner of GPIO pins

Avoid importing multiple modules that claim the same GPIO pins.

Problem seen:

```text
GPIO busy
```

Cause:

```text
app.py and morse_output.py both tried to create LED(GPIO27)
```

Current solution:

```text
app.py owns GPIO objects directly for now.
```

Future refactor:

```text
Create one hardware.py module that owns all GPIO devices safely.
```

---

### Do not use Flask debug reloader with GPIO

Use:

```python
app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
```

Reason:

```text
The debug reloader can start more than one process and claim GPIO pins twice.
```

---

### Logging starts early

Logging should be added before the project grows too far.

Reason:

```text
Progress tracking and adaptive learning depend on saved student data.
```

---

## 18. Definition of Done for Current Stage

The current stage is successful when:

```text
Student can open the web app.
Student can type a message and see Morse.
Student can play Morse in the browser.
Student can stop browser playback when a phrase is longer than expected.
Student can play Morse on the Pi LED + buzzer.
Student can stop Pi playback when a phrase is longer than expected.
Student can tap the telegraph key.
The tapped Morse appears in the web app.
Student can use Practice Mode.
Student can check whether a tapped letter matches the prompt.
```

Current status:

```text
This stage is working.
```

---

## 19. Definition of Done for Next Stage

The next stage is successful when:

```text
The student can complete a short Send practice session without mouse use.
The student can complete a short Learn practice session with letter, Morse, sound, and key-along support.
The student can complete a short Read practice session from visible Morse.
The student can complete a short Listen practice session from audio prompts.
Feedback feels encouraging and does not make practice too easy.
Progress details are understandable to a student or parent.
The next coding priority is selected from Mixed mode, more letters, or timing feedback.
```

---

## 20. Future Vision

The long-term vision is a family Morse learning network:

```text
Each student has a profile.
Each student logs in with a Morse password.
Each student gets a custom mission.
The station tracks progress.
The station adapts difficulty.
Pappy can send secret Morse messages.
Students listen, decode, and reply.
Stations communicate securely over the internet.
LLM support helps create personalized learning plans.
```

The project should remain focused on the learning experience:

```text
tap the key
hear the beep
see the light
decode the secret message
send a reply
learn a little more every time
```

# Morse Learning Best Practices

Research notes for Pappy's Internet Telegraph.

Last updated: 2026-06-16

## Purpose

This document captures learning-method research and design decisions for the Morse Station. The goal is to turn proven Morse teaching ideas into app behavior that helps 3rd-6th grade students practice without frustration.

## Summary

The learning station should teach Morse as sound and rhythm first, not as visual dot/dash counting. Students should practice in short loops, get immediate feedback, repeat weak letters, and gradually unlock more letters as confidence grows.

Recommended default approach:

- Use Farnsworth-style timing: recognizable character rhythm with extra spacing between letters and words.
- Use Koch-style progression: start with a small set of letters, then add more only after the student shows comfort.
- Keep practice sessions short and focused.
- Practice the same skill from multiple directions: see, hear, tap, read, and send.
- Track weak letters and repeat them more often.
- Add timing feedback after the basic modes feel stable.

## Core Methods

### Farnsworth Timing

Farnsworth timing sends each character at a useful target rhythm, but stretches the gaps between characters and words. This gives beginners thinking time without teaching distorted, extra-slow letter sounds.

For this project, the current beginner default is:

| Setting | Current default | Reason |
|---|---:|---|
| Character speed | 15 WPM | Keeps each letter's sound pattern recognizable |
| Effective spacing | 7 WPM | Gives beginners time to think between letters |
| Tone | 700 Hz | Clear browser/Pi speaker tone |

Design implication:

- Keep dot/dash timing crisp.
- Make inter-letter and inter-word gaps adjustable.
- Let students replay audio prompts.
- Test whether 15/7 WPM feels good on the real 7-inch station.

### Koch-Style Progression

Koch-style training starts with only a few characters at a real character speed. Once the student reaches a target accuracy, another character is introduced.

Design implication:

- Start with a small beginner set such as `E`, `T`, `A`, `N`, `I`, `M`.
- Track mastery per letter and per mode.
- Unlock new letters based on progress.
- Prefer weak or new letters when choosing the next prompt.
- Avoid showing the whole alphabet during beginner drills.

### Sound Before Symbols

Morse learning works best when students recognize each letter as a rhythm or sound shape. If students memorize a visual chart and count dots/dashes, they may struggle later when listening at normal speed.

Design implication:

- Continue supporting Listen mode.
- Keep audio replay easy to find.
- Avoid over-relying on a visible dot/dash answer during tests.
- Use visible Morse mainly for Learn and Read practice, not as a crutch in Send and Listen.

## Practice Modes

The current four practice modes map well to the learning goals.

| Mode | Student sees/hears | Student does | Skill reinforced |
|---|---|---|---|
| Learn | Letter, Morse, sound | Key along | Connect letter, sound, and movement |
| Send | Letter | Tap Morse | Recall and send |
| Read | Morse | Select/type letter | Decode visual Morse |
| Listen | Audio | Select/type letter | Decode sound |

Recommended future mode:

| Mode | Student does | Why |
|---|---|---|
| Mixed | Random mix of Send, Read, Listen | Builds flexible recall after basic confidence |

## Feedback Rules

Feedback should feel like coaching, not grading.

Good feedback:

- Short and immediate.
- Encouraging when correct.
- Specific when wrong.
- Allows another try without requiring mouse/touch navigation.
- Repeats weak letters over time.

Examples:

```text
Correct: E. Next letter coming up.
Try A again. I heard .., but A is .-.
Ready. Try it again.
```

Avoid:

- Long explanation text during practice.
- Harsh failure language.
- Requiring the student to move from keyer to mouse after every attempt.

## Timing Feedback Goals

Timing feedback should be the next major learning improvement after touch-screen testing.

Useful feedback targets:

- Dot too long or too short.
- Dash too short or too long.
- Intra-character gap too long, causing one letter to split.
- Letter gap too short, causing letters to merge.
- Rhythm consistency over a short session.

Suggested implementation path:

1. Capture raw key down/up timestamps.
2. Compare student timing to current dot/dash/gap settings.
3. Show simple coaching messages first.
4. Add detailed timing charts only after the basic feedback is useful.

Kid-friendly examples:

```text
Good rhythm.
Make the dash a little longer.
Pause a little more before the next letter.
That sounded like two letters. Try keeping the parts closer together.
```

## Progress And Unlocking

Progress should encourage practice without making the app feel like a test.

Recommended progress model:

- Track each mode separately: Learn, Send, Read, Listen.
- Track each letter separately.
- Use mastery, accuracy, attempts, and streak.
- Use an overall Operator Level for motivation.
- Unlock letters gradually, but allow an adult/testing override later.

Open decision:

- Should unlocked letters control the active practice set immediately, or should the current beginner set remain manually controlled until more testing?

## Touch Station Design Notes

The 7-inch Pi touchscreen should be a focused learning station.

Current direction:

- Touch menu focuses on Practice, Progress, Key, and Timing.
- Typed Message is hidden from the student-facing touch menu because typing phrases on the small screen is awkward.
- Spacebar Keyer is hidden on touch screens; physical key input is the main interaction.
- Desktop/laptop pages keep typed messages and Spacebar Keyer for testing.

## Sources

- Wikipedia, "Morse code" - timing, Farnsworth method, Koch method overview: https://en.wikipedia.org/wiki/Morse_code
- Wikipedia, "Words per minute" - Morse WPM measurement and `PARIS`/`CODEX` timing standards: https://en.wikipedia.org/wiki/Words_per_minute
- Wikipedia, "W1AW" - ARRL code practice speeds and training broadcast context: https://en.wikipedia.org/wiki/W1AW
- LCWO - online Morse practice using Koch-style lessons and speed settings: https://lcwo.net/

## Project Decisions From This Research

- Keep the current 15/7 WPM beginner timing until tested with students.
- Build for short practice loops with no mouse/touch required during Send mode.
- Continue separating Learn, Send, Read, and Listen.
- Prioritize timing feedback before adding too many new features.
- Keep progress feedback simple on the touch station and detailed on desktop.

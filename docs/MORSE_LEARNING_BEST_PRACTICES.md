# Morse Learning Best Practices

Research notes for Pappy's Internet Telegraph.

Last updated: 2026-06-17

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
| Character speed | 12 WPM | Keeps each letter's sound pattern recognizable while making dashes easier to hear |
| Effective spacing | 6 WPM | Gives beginners time to think between letters |
| Tone | 700 Hz | Clear browser/Pi speaker tone |

Design implication:

- Keep dot/dash timing crisp.
- Make inter-letter and inter-word gaps adjustable.
- Let students replay audio prompts.
- Test whether 12/6 WPM feels good on the real 7-inch station.

### Koch-Style Progression

Koch-style training starts with only a few characters at a real character speed. Once the student reaches a target accuracy, another character is introduced.

Design implication:

- Start with a small beginner set such as `E`, `T`, `A`, `N`, `I`, `M`.
- Track mastery per letter and per mode.
- Unlock new letters based on progress.
- Introduce newly unlocked letters in Learn before testing them in Send, Read, or Listen.
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

The current practice modes map well to the learning goals.

| Mode | Student sees/hears | Student does | Skill reinforced |
|---|---|---|---|
| Learn | Letter, Morse, sound | Key along | Connect letter, sound, and movement |
| Send | Letter | Tap Morse | Recall and send |
| Read | Morse | Select/type letter | Decode visual Morse |
| Listen | Audio | Select/type letter | Decode sound |
| Echo | Audio | Key Morse back | Hear-and-key-back reinforcement |

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

1. Capture raw key down/up timestamps. Started with `data/practice_attempts.jsonl`.
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

- Track each mode separately: Learn, Send, Read, Listen, Echo.
- Track each letter separately.
- Use mastery, accuracy, attempts, and streak.
- Use an overall Operator Level for motivation.
- Unlock letters gradually, but place each new group in Learn first.
- Keep only one group in `Learning Now` at a time so students cannot unlock far ahead before learning the new letters.
- Move the learning group into Send, Read, Listen, and Echo after each new letter has enough Learn success.
- Allow an adult/testing override later.

Current decision:

- `E T A N I M` are the starter active practice letters.
- New groups unlock by all-mode mastery, then appear in Learn as `Learning Now`.
- Send, Read, Listen, and Echo continue using active practice letters until the learning group is ready.
- The current readiness rule is 10 correct Learn attempts, 70% Learn strength, and practice across at least two calendar days for each new letter.
- Later groups cannot unlock until the current learning group joins active practice.

## Adaptive Listening

Listen practice can adapt before the rest of the station timing changes.

Current first rule:

- If Listen has fewer than 10 attempts, overall Listen accuracy is below 70%, or the current letter's Listen accuracy is below 70%, Listen prompts play one step slower than the saved station timing.
- Once Listen accuracy improves, prompts return to the saved station timing.

Design cautions:

- Do not change speed on every single attempt.
- Keep the change subtle so students still learn real Morse rhythm.
- Show adaptive timing as help, not failure, if it becomes visible in the UI.

## Words, Transfer, And Practical Copy

Letter drills build the foundation, but students should not wait until all A-Z letters are unlocked before seeing words. Words make Morse feel useful and help students transfer isolated letter knowledge into practical communication.

Recommended progression:

1. Start with micro-words made only from active letters.
2. Add unlocked-letter words as more letters graduate into active practice.
3. Use Daily Mission word challenges as optional short wins.
4. Later add secret message activities where the student decodes real words or short phrases.

Design rules:

- Do not introduce words containing unknown letters unless the activity is explicitly a preview.
- Keep early words short: 2-3 letters, then 4-5 letters.
- Favor touch choices and telegraph-key input before keyboard typing for younger students.
- Keep typed answers available on desktop/testing, but avoid making keyboard skill a blocker on the 7-inch station.
- Track word practice separately from letter mastery so a hard word does not make basic letter progress feel worse.

Student motivation notes:

- Some students, like Astrid, may be motivated by perfection and 100% mastery.
- Other students, like Liara, may be motivated by practical progress and using Morse to copy something meaningful.
- The app should support both: clean mastery loops for perfection-driven students, plus real-word missions for practical learners.

Good first word activities:

```text
Hear Morse -> choose the word from large touch buttons.
See a word -> key the Morse with the telegraph key.
Hear a short word -> echo it back with the key.
Match visible Morse to the word.
```

## Rewards And Daily Return

Rewards should celebrate real learning moments and point to the next mission. The goal is to make 100% feel like a doorway, not the end of the app.

Recommended reward moments:

- Active signal set reaches 100% across practice areas.
- New letters unlock into Learning Now.
- Learning Now letters graduate into active practice.
- Daily Mission is completed.
- First perfect Echo or Word Copy round.
- A student returns on another day to complete burn-in.

Recommended reward style:

- Full-screen touch celebration for important milestones.
- Short Morse-style sound flourish.
- LED celebration flash.
- Badge text connected to the skill, such as `First Signals Mastered` or `Clean Copy`.
- Immediate next mission text, such as `New mission: Learn S O`.

Avoid:

- Leaderboards between students.
- Long animations that slow practice.
- Rewards unrelated to actual learning.
- Making the app feel finished when a student reaches 100% on the current active set.

## Touch Station Design Notes

The 7-inch Pi touchscreen should be a focused learning station.

Current direction:

- Touch menu focuses on Practice, Progress, Key, and Timing.
- Typed Message is hidden from the student-facing touch menu because typing phrases on the small screen is awkward.
- Spacebar Keyer is hidden on touch screens; physical key input is the main interaction.
- Desktop/laptop pages keep typed messages and Spacebar Keyer for testing.
- Daily Mission should become the normal first stop if student testing shows it makes the learning flow clearer.
- Word Copy should favor large touch choices and keyer input before typed answers.

## Future Game Direction

A game mode can become useful after Daily Mission, word practice, and rewards are stable. It should wrap real practice rather than becoming a separate toy.

Possible game concept:

```text
Signal Quest
Student is a radio operator.
Daily practice powers the station.
Letters unlock places, badges, or message missions.
Words become supplies, secret notes, or rescued messages.
Accuracy keeps the signal clear.
Mistakes create static, not punishment.
```

Simpler first game:

```text
Message Rescue
A word arrives by Morse.
Student decodes it using big touch choices or keys it back.
Correct words repair the signal tower, light a beacon, or deliver a secret note.
Only already-learned letters appear.
```

Implementation guidance:

- Build game mode after the core practice engine and word practice are stable.
- Reuse existing Daily Mission, practice attempts, timing, and reward systems.
- Keep the game cooperative and personal rather than competitive.
- Use practical progress for students who want meaning and mastery badges for students who want perfection.

## Sources

- Wikipedia, "Morse code" - timing, Farnsworth method, Koch method overview: https://en.wikipedia.org/wiki/Morse_code
- Wikipedia, "Words per minute" - Morse WPM measurement and `PARIS`/`CODEX` timing standards: https://en.wikipedia.org/wiki/Words_per_minute
- Wikipedia, "W1AW" - ARRL code practice speeds and training broadcast context: https://en.wikipedia.org/wiki/W1AW
- LCWO - online Morse practice using Koch-style lessons and speed settings: https://lcwo.net/
- ARRL, "W1AW Operating Schedule" - slow/fast code practice speeds and real-text practice context: https://www.arrl.org/w1aw-operating-schedule

## Project Decisions From This Research

- Start with 12/6 WPM beginner timing after hands-on testing showed 15/7 was too fast for Listen practice.
- Keep the input dash threshold tied to playback timing so a correctly imitated dash decodes as a dash.
- Build for short practice loops with no mouse/touch required during Send mode.
- Continue separating Learn, Send, Read, Listen, and Echo.
- Use Learn-first gating for new letters so students are not surprised by unlearned prompts in Send, Read, Listen, or Echo.
- Prioritize timing feedback before adding too many new features.
- Keep progress feedback simple on the touch station and detailed on desktop.
- Introduce word practice before the full alphabet is unlocked, using only known letters.
- Use Daily Mission and future rewards to turn mastery into the next learning step.
- Make Daily Mission the first place to test motivational feedback because it already combines daily effort, accuracy, active letters, and next practice choices.
- Favor a next-action reward model: celebrate completion briefly, then guide the student to Learn new letters or strengthen the weakest mode.

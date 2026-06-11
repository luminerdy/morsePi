function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

let practiceCheckTimer = null;
let lastCheckedPracticeMorse = "";
let pendingPracticeMorse = "";
let practiceActive = true;
let practiceBusy = false;
let keyboardKeyerActive = false;
let keyboardPressStartedAt = null;
let keyboardMorse = "";

const KEYBOARD_DASH_THRESHOLD_MS = 400;
const MORSE_DECODE = {
    ".": "E",
    "-": "T",
    ".-": "A",
    "-.": "N",
    "..": "I",
    "--": "M"
};

async function browserBeep(audioCtx, durationMs) {
    const oscillator = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    oscillator.frequency.value = 700;
    oscillator.type = "sine";
    gain.gain.value = 0.2;

    oscillator.connect(gain);
    gain.connect(audioCtx.destination);

    oscillator.start();
    await sleep(durationMs);
    oscillator.stop();
}

async function playInBrowser() {
    const morseBox = document.getElementById("morseBox");

    if (!morseBox) {
        return;
    }

    const morseText = morseBox.innerText.trim();

    if (!morseText || morseText === "Type a message above.") {
        return;
    }

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    const dotMs = 250;
    const dashMs = dotMs * 3;
    const symbolGapMs = dotMs;
    const letterGapMs = dotMs * 3;
    const wordGapMs = dotMs * 7;

    for (const ch of morseText) {
        if (ch === ".") {
            await browserBeep(audioCtx, dotMs);
            await sleep(symbolGapMs);
        } else if (ch === "-") {
            await browserBeep(audioCtx, dashMs);
            await sleep(symbolGapMs);
        } else if (ch === " ") {
            await sleep(letterGapMs);
        } else if (ch === "/") {
            await sleep(wordGapMs);
        }
    }
}

async function updateLiveKey() {
    const liveMorse = document.getElementById("liveMorse");
    const liveDecoded = document.getElementById("liveDecoded");

    if (!liveMorse || !liveDecoded) {
        return;
    }

    if (keyboardKeyerActive) {
        return;
    }

    try {
        const response = await fetch("/live-key");
        const data = await response.json();

        if (data.morse) {
            liveMorse.innerText = data.morse;
            liveDecoded.innerText = data.decoded || "---";
        } else {
            liveMorse.innerText = "Waiting for key...";
            liveDecoded.innerText = "---";
        }

        schedulePracticeAutoCheck(data.morse || "");
    } catch (error) {
        console.log("Unable to update key display", error);
    }
}

async function clearKeyInput() {
    if (keyboardKeyerActive) {
        resetVirtualKeyer();
        return;
    }

    await fetch("/clear-key", {
        method: "POST"
    });

    resetPracticeAutoCheck();
    updateLiveKey();
}

function getPracticePanel() {
    return document.querySelector("[data-practice-target][data-expected-morse]");
}

function getPracticeMode() {
    const panel = getPracticePanel();
    return panel ? (panel.dataset.practiceMode || "send") : "send";
}

function normalizeMorse(value) {
    return value.trim().replace(/\s+/g, " ");
}

function countMorseSymbols(value) {
    return value.replace(/[\s/]/g, "").length;
}

function setPracticeFeedback(message) {
    const feedback = document.getElementById("practiceFeedback");

    if (!feedback) {
        return;
    }

    feedback.innerText = message;
    feedback.hidden = !message;

    feedback.classList.remove("success", "needs-practice");

    if (message.startsWith("Correct")) {
        feedback.classList.add("success");
    } else if (message.startsWith("Try")) {
        feedback.classList.add("needs-practice");
    }
}

function resetPracticeAutoCheck() {
    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
    }

    practiceCheckTimer = null;
    lastCheckedPracticeMorse = "";
    pendingPracticeMorse = "";
    setPracticeFeedback("");
}

function schedulePracticeAutoCheck(rawMorse) {
    const panel = getPracticePanel();

    if (!panel || getPracticeMode() !== "send" || !practiceActive || practiceBusy) {
        return;
    }

    const actualMorse = normalizeMorse(rawMorse);
    const expectedMorse = normalizeMorse(panel.dataset.expectedMorse || "");

    if (!actualMorse) {
        if (practiceCheckTimer) {
            clearTimeout(practiceCheckTimer);
            practiceCheckTimer = null;
        }
        lastCheckedPracticeMorse = "";
        pendingPracticeMorse = "";
        return;
    }

    if (actualMorse === lastCheckedPracticeMorse) {
        return;
    }

    if (countMorseSymbols(actualMorse) < countMorseSymbols(expectedMorse)) {
        if (practiceCheckTimer) {
            clearTimeout(practiceCheckTimer);
            practiceCheckTimer = null;
        }
        pendingPracticeMorse = "";
        return;
    }

    if (actualMorse === pendingPracticeMorse) {
        return;
    }

    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
    }

    pendingPracticeMorse = actualMorse;
    practiceCheckTimer = setTimeout(() => {
        checkPracticeAnswer(actualMorse, expectedMorse, panel.dataset.practiceTarget || "");
    }, 1100);
}

function checkPracticeAnswer(actualMorse, expectedMorse, target) {
    lastCheckedPracticeMorse = actualMorse;
    pendingPracticeMorse = "";
    practiceBusy = true;

    if (actualMorse === expectedMorse) {
        setPracticeFeedback(`Correct: ${target}. Next letter coming up.`);
        recordPracticeResult(target, true).finally(() => {
            setTimeout(loadNextPracticePrompt, 950);
        });
    } else {
        setPracticeFeedback(
            `Try ${target} again. I heard ${actualMorse}, but ${target} is ${expectedMorse}.`
        );
        recordPracticeResult(target, false).finally(() => {
            setTimeout(retryPracticePrompt, 1200);
        });
    }
}

async function recordPracticeResult(target, correct) {
    try {
        const response = await fetch("/practice/result", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ target, correct, mode: getPracticeMode() })
        });
        const data = await response.json();
        updateProgressPanel(data.progress || []);
        updateScoreCard(data.score || null);
    } catch (error) {
        console.log("Unable to record practice result", error);
    }
}

async function loadNextPracticePrompt() {
    try {
        const response = await fetch(`/practice/next?mode=${encodeURIComponent(getPracticeMode())}`, {
            method: "POST"
        });
        const data = await response.json();

        updatePracticePrompt(data.target, data.expected_morse, data.read_choices || []);
        updateProgressPanel(data.progress || []);
        updateScoreCard(data.score || null);
        resetInputDisplay();
        setPracticeFeedback(getPracticeMode() === "read" ? "Next one." : `Now try ${data.target}.`);
        focusReadInput();
    } catch (error) {
        console.log("Unable to load next practice prompt", error);
    } finally {
        practiceBusy = false;
        lastCheckedPracticeMorse = "";
        pendingPracticeMorse = "";
    }
}

async function retryPracticePrompt() {
    try {
        const response = await fetch(`/practice/retry?mode=${encodeURIComponent(getPracticeMode())}`, {
            method: "POST"
        });
        const data = await response.json();

        updatePracticePrompt(data.target, data.expected_morse, data.read_choices || []);
        updateProgressPanel(data.progress || []);
        updateScoreCard(data.score || null);
        resetInputDisplay();
        setPracticeFeedback("Ready. Try it again.");
        focusReadInput();
    } catch (error) {
        console.log("Unable to reset practice prompt", error);
    } finally {
        practiceBusy = false;
        lastCheckedPracticeMorse = "";
        pendingPracticeMorse = "";
    }
}

function updatePracticePrompt(target, expectedMorse, readChoices = []) {
    const panel = getPracticePanel();
    const targetLetter = document.getElementById("targetLetter");
    const expected = document.getElementById("expectedMorse");

    if (!panel || !targetLetter || !expected) {
        return;
    }

    panel.dataset.practiceTarget = target;
    panel.dataset.expectedMorse = expectedMorse;
    targetLetter.innerText = getPracticeMode() === "read" ? "?" : target;
    expected.innerText = expectedMorse;
    updateReadChoices(readChoices);
}

function updateReadChoices(choices) {
    const choiceGrid = document.getElementById("readChoices");

    if (!choiceGrid || !Array.isArray(choices) || choices.length === 0) {
        return;
    }

    choiceGrid.innerHTML = "";

    for (const choice of choices) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button secondary read-choice";
        button.dataset.readChoice = choice;
        button.innerText = choice;
        button.addEventListener("click", () => submitReadAnswer(choice));
        choiceGrid.appendChild(button);
    }
}

function updateProgressPanel(progress) {
    const progressPanel = document.getElementById("practiceProgress");

    if (!progressPanel || !Array.isArray(progress)) {
        return;
    }

    for (const item of progress) {
        const row = progressPanel.querySelector(`[data-progress-letter="${item.letter}"]`);

        if (!row) {
            continue;
        }

        const percent = Math.max(0, Math.min(Number(item.strength_percent) || 0, 100));
        const summary = row.querySelector(".progress-row span");
        const bar = row.querySelector(".progress-bar span");
        const meta = row.querySelector(".progress-meta");

        if (summary) {
            summary.innerText = `${percent}%`;
        }

        if (bar) {
            bar.style.width = `${percent}%`;
        }

        if (meta) {
            meta.innerHTML = `
                <span>${item.accuracy}% accuracy</span>
                <span>${item.streak} streak</span>
                <span>${item.attempts} tries</span>
            `;
        }
    }
}

function updateScoreCard(score) {
    if (!score) {
        return;
    }

    const scorePanel = document.getElementById("practiceScore");
    const mastery = document.getElementById("scoreMastery");
    const masteryBar = document.getElementById("scoreMasteryBar");
    const streak = document.getElementById("scoreStreak");
    const accuracy = document.getElementById("scoreAccuracy");
    const attempts = document.getElementById("scoreAttempts");
    const goal = document.getElementById("scoreGoal");

    if (!scorePanel) {
        return;
    }

    const masteryValue = Math.max(0, Math.min(Number(score.mastery) || 0, 100));

    if (mastery) {
        mastery.innerText = `${masteryValue}%`;
    }

    if (masteryBar) {
        masteryBar.style.width = `${masteryValue}%`;
    }

    if (streak) {
        streak.innerText = score.streak;
    }

    if (accuracy) {
        accuracy.innerText = `${score.accuracy}% accuracy`;
    }

    if (attempts) {
        attempts.innerText = `${score.attempts} tries`;
    }

    if (goal) {
        goal.innerText = score.next_goal;
    }
}

function normalizeLetterAnswer(value) {
    return (value || "").trim().toUpperCase().slice(0, 1);
}

function clearReadInput() {
    const input = document.getElementById("readAnswerInput");

    if (input) {
        input.value = "";
    }
}

function focusReadInput() {
    const input = document.getElementById("readAnswerInput");

    if (getPracticeMode() === "read" && input) {
        input.focus();
    }
}

function submitReadAnswer(answer) {
    const panel = getPracticePanel();

    if (!panel || getPracticeMode() !== "read" || practiceBusy || !practiceActive) {
        return;
    }

    const target = panel.dataset.practiceTarget || "";
    const expectedMorse = panel.dataset.expectedMorse || "";
    const normalizedAnswer = normalizeLetterAnswer(answer);

    if (!normalizedAnswer) {
        return;
    }

    practiceBusy = true;
    clearReadInput();

    if (normalizedAnswer === target) {
        setPracticeFeedback(`Correct: ${target}. Next letter coming up.`);
        recordPracticeResult(target, true).finally(() => {
            setTimeout(loadNextPracticePrompt, 850);
        });
    } else {
        setPracticeFeedback(`Try again. ${expectedMorse} is ${target}, not ${normalizedAnswer}.`);
        recordPracticeResult(target, false).finally(() => {
            setTimeout(retryPracticePrompt, 1200);
        });
    }
}

function resetLiveKeyDisplay() {
    const liveMorse = document.getElementById("liveMorse");
    const liveDecoded = document.getElementById("liveDecoded");

    if (liveMorse) {
        liveMorse.innerText = "Waiting for key...";
    }

    if (liveDecoded) {
        liveDecoded.innerText = "---";
    }
}

function resetInputDisplay() {
    if (keyboardKeyerActive) {
        resetVirtualKeyer();
        return;
    }

    resetLiveKeyDisplay();
}

function resetVirtualKeyer() {
    keyboardPressStartedAt = null;
    keyboardMorse = "";
    resetLiveKeyDisplay();
    lastCheckedPracticeMorse = "";
    pendingPracticeMorse = "";

    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
        practiceCheckTimer = null;
    }
}

function updateVirtualKeyerDisplay() {
    const liveMorse = document.getElementById("liveMorse");
    const liveDecoded = document.getElementById("liveDecoded");
    const morse = normalizeMorse(keyboardMorse);

    if (liveMorse) {
        liveMorse.innerText = morse || "Waiting for key...";
    }

    if (liveDecoded) {
        liveDecoded.innerText = morse ? (MORSE_DECODE[morse] || "?") : "---";
    }

    schedulePracticeAutoCheck(morse);
}

function updateKeyboardKeyerToggle() {
    const toggle = document.getElementById("keyboardKeyerToggle");
    const status = document.getElementById("keyerStatus");

    if (toggle) {
        toggle.innerText = keyboardKeyerActive ? "Spacebar Keyer: On" : "Spacebar Keyer: Off";
        toggle.classList.toggle("active", keyboardKeyerActive);
    }

    if (status) {
        status.innerText = keyboardKeyerActive ? "Spacebar keyer" : "Live";
        status.classList.toggle("keyboard", keyboardKeyerActive);
    }
}

function setKeyboardKeyerActive(active) {
    keyboardKeyerActive = active;
    resetVirtualKeyer();
    updateKeyboardKeyerToggle();

    if (!keyboardKeyerActive) {
        updateLiveKey();
    }
}

function ignoreKeyboardKeyerEvent(event) {
    const tagName = event.target && event.target.tagName;
    return ["INPUT", "TEXTAREA", "BUTTON", "A", "SELECT"].includes(tagName);
}

function handleKeyboardKeyDown(event) {
    if (!keyboardKeyerActive || event.code !== "Space" || event.repeat || ignoreKeyboardKeyerEvent(event)) {
        return;
    }

    event.preventDefault();

    if (keyboardPressStartedAt === null) {
        keyboardPressStartedAt = performance.now();
    }
}

function handleKeyboardKeyUp(event) {
    if (!keyboardKeyerActive || event.code !== "Space" || ignoreKeyboardKeyerEvent(event)) {
        return;
    }

    event.preventDefault();

    if (keyboardPressStartedAt === null) {
        return;
    }

    const durationMs = performance.now() - keyboardPressStartedAt;
    keyboardPressStartedAt = null;
    keyboardMorse += durationMs >= KEYBOARD_DASH_THRESHOLD_MS ? "-" : ".";
    updateVirtualKeyerDisplay();
}

function updatePracticeToggle() {
    const toggle = document.getElementById("practiceToggle");
    const status = document.getElementById("practiceStatus");

    if (!toggle || !status) {
        return;
    }

    toggle.innerText = practiceActive ? "Stop Practice" : "Resume Practice";
    status.innerText = practiceActive ? "Auto practice on" : "Practice paused";
    status.classList.toggle("paused", !practiceActive);
}

function initializePracticeMode() {
    const panel = getPracticePanel();
    const toggle = document.getElementById("practiceToggle");
    const keyboardToggle = document.getElementById("keyboardKeyerToggle");
    const readSubmit = document.getElementById("readSubmit");
    const readInput = document.getElementById("readAnswerInput");

    if (!panel || !toggle) {
        return;
    }

    toggle.addEventListener("click", () => {
        practiceActive = !practiceActive;

        if (!practiceActive && practiceCheckTimer) {
            clearTimeout(practiceCheckTimer);
            practiceCheckTimer = null;
        }

        updatePracticeToggle();
    });

    if (keyboardToggle) {
        keyboardToggle.addEventListener("click", () => {
            setKeyboardKeyerActive(!keyboardKeyerActive);
        });
    }

    document.querySelectorAll("[data-read-choice]").forEach(button => {
        button.addEventListener("click", () => submitReadAnswer(button.dataset.readChoice || ""));
    });

    if (readSubmit && readInput) {
        readSubmit.addEventListener("click", () => submitReadAnswer(readInput.value));
        readInput.addEventListener("keydown", event => {
            if (event.key === "Enter") {
                event.preventDefault();
                submitReadAnswer(readInput.value);
            }
        });
        readInput.addEventListener("input", () => {
            readInput.value = normalizeLetterAnswer(readInput.value);
        });
    }

    document.addEventListener("keydown", handleKeyboardKeyDown);
    document.addEventListener("keyup", handleKeyboardKeyUp);

    updatePracticeToggle();
    updateKeyboardKeyerToggle();
    clearKeyInput();
    focusReadInput();
}

document.addEventListener("DOMContentLoaded", () => {
    initializePracticeMode();
    updateLiveKey();
    setInterval(updateLiveKey, 300);
});

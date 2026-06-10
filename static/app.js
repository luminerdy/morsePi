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

    if (!panel || !practiceActive || practiceBusy) {
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
        setTimeout(loadNextPracticePrompt, 950);
    } else {
        setPracticeFeedback(
            `Try ${target} again. I heard ${actualMorse}, but ${target} is ${expectedMorse}.`
        );
        setTimeout(retryPracticePrompt, 1200);
    }
}

async function loadNextPracticePrompt() {
    try {
        const response = await fetch("/practice/next", {
            method: "POST"
        });
        const data = await response.json();

        updatePracticePrompt(data.target, data.expected_morse);
        resetInputDisplay();
        setPracticeFeedback(`Now try ${data.target}.`);
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
        await fetch("/practice/retry", {
            method: "POST"
        });

        resetInputDisplay();
        setPracticeFeedback("Ready. Try it again.");
    } catch (error) {
        console.log("Unable to reset practice prompt", error);
    } finally {
        practiceBusy = false;
        lastCheckedPracticeMorse = "";
        pendingPracticeMorse = "";
    }
}

function updatePracticePrompt(target, expectedMorse) {
    const panel = getPracticePanel();
    const targetLetter = document.getElementById("targetLetter");
    const expected = document.getElementById("expectedMorse");

    if (!panel || !targetLetter || !expected) {
        return;
    }

    panel.dataset.practiceTarget = target;
    panel.dataset.expectedMorse = expectedMorse;
    targetLetter.innerText = target;
    expected.innerText = expectedMorse;
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

    document.addEventListener("keydown", handleKeyboardKeyDown);
    document.addEventListener("keyup", handleKeyboardKeyUp);

    updatePracticeToggle();
    updateKeyboardKeyerToggle();
    clearKeyInput();
}

document.addEventListener("DOMContentLoaded", () => {
    initializePracticeMode();
    updateLiveKey();
    setInterval(updateLiveKey, 300);
});

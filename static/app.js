function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

let practiceCheckTimer = null;
let lastCheckedPracticeMorse = "";

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
}

function resetPracticeAutoCheck() {
    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
    }

    practiceCheckTimer = null;
    lastCheckedPracticeMorse = "";
    setPracticeFeedback("");
}

function schedulePracticeAutoCheck(rawMorse) {
    const panel = getPracticePanel();

    if (!panel) {
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
        return;
    }

    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
    }

    practiceCheckTimer = setTimeout(() => {
        checkPracticeAnswer(actualMorse, expectedMorse, panel.dataset.practiceTarget || "");
    }, 1100);
}

function checkPracticeAnswer(actualMorse, expectedMorse, target) {
    lastCheckedPracticeMorse = actualMorse;

    if (actualMorse === expectedMorse) {
        setPracticeFeedback(`Great job! You tapped ${target} correctly.`);
    } else {
        setPracticeFeedback(
            `Good try. I heard ${actualMorse}, but ${target} is ${expectedMorse}. Try again and listen to the rhythm.`
        );
    }
}

document.addEventListener("DOMContentLoaded", () => {
    updateLiveKey();
    setInterval(updateLiveKey, 300);
});

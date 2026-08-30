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
let keyboardLastReleasedAt = null;
let keyboardMorse = "";
let keyboardTimingEvents = [];
let keyboardAudioCtx = null;
let keyboardToneOscillator = null;
let keyboardToneGain = null;
let practiceAudioPlaying = false;
let browserAudioCtx = null;
let browserPlayback = null;
let wordCheckTimer = null;
let lastCheckedWordMorse = "";
let pendingWordMorse = "";
let wordStartedAt = null;
let wordAutoAdvanceTimer = null;
let touchIdleExperience = null;
let lastObservedPhysicalMorse = "";
let signalDropExperience = null;
let messageKeyCheckTimer = null;
let messageKeyLastMorse = "";
let messageKeyPendingMorse = "";
let messageKeyBusy = false;
let messageKeyStartedAt = null;

const KEYBOARD_DASH_THRESHOLD_UNITS = 2.5;
const WORD_AUTO_ADVANCE_DELAY_MS = 4000;
const WORD_AUTOPLAY_DELAY_MS = 1800;
const TOUCH_SCREENSAVER_IDLE_MS = 3 * 60 * 1000;
const TOUCH_SCREENSAVER_GUESS_MS = 5 * 1000;
const TOUCH_SCREENSAVER_REVEAL_MS = 3 * 1000;
const TOUCH_OPERATOR_RESET_MS = 10 * 60 * 1000;
const MORSE_DECODE = {
    ".": "E",
    "-": "T",
    ".-": "A",
    "-.": "N",
    "..": "I",
    "--": "M",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
    "-----": "0"
};

function ensureBrowserAudioContext() {
    if (!browserAudioCtx) {
        browserAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }

    if (browserAudioCtx.state === "suspended") {
        browserAudioCtx.resume();
    }

    return browserAudioCtx;
}

function getMorseTiming() {
    const source = document.body ? document.body.dataset : {};
    const numberFromData = (name, fallback) => {
        const parsed = Number(source[name]);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
    };

    return {
        toneHz: numberFromData("toneHz", 700),
        dotMs: numberFromData("dotMs", 80),
        dashMs: numberFromData("dashMs", 240),
        symbolGapMs: numberFromData("symbolGapMs", 80),
        letterGapMs: numberFromData("letterGapMs", 514),
        wordGapMs: numberFromData("wordGapMs", 1200),
        inputDashThresholdMs: numberFromData("inputDashThresholdMs", 200)
    };
}

function getKeyboardDashThresholdMs() {
    const timing = getMorseTiming();
    return timing.inputDashThresholdMs || Math.round(timing.dotMs * KEYBOARD_DASH_THRESHOLD_UNITS);
}

function updateMorseTimingData(timing) {
    if (!timing || !document.body) {
        return;
    }

    const fields = {
        toneHz: "tone_hz",
        dotMs: "dot_ms",
        dashMs: "dash_ms",
        symbolGapMs: "symbol_gap_ms",
        letterGapMs: "letter_gap_ms",
        wordGapMs: "word_gap_ms",
        inputDashThresholdMs: "input_dash_threshold_ms"
    };

    for (const [dataKey, timingKey] of Object.entries(fields)) {
        if (timing[timingKey] !== undefined) {
            document.body.dataset[dataKey] = timing[timingKey];
        }
    }
}

async function browserBeep(audioCtx, durationMs, playback = null) {
    if (audioCtx.state === "suspended") {
        await audioCtx.resume();
    }

    const oscillator = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    oscillator.frequency.value = getMorseTiming().toneHz;
    oscillator.type = "sine";
    gain.gain.value = 0.2;

    oscillator.connect(gain);
    gain.connect(audioCtx.destination);

    if (playback) {
        playback.oscillator = oscillator;
    }

    oscillator.start();
    await sleep(durationMs);

    try {
        oscillator.stop();
    } catch (error) {
        // The stop button may have already stopped this oscillator.
    }

    if (playback && playback.oscillator === oscillator) {
        playback.oscillator = null;
    }
}

async function triggerDailyCelebration() {
    try {
        await fetch("/touch/daily/celebrate", { method: "POST" });
    } catch (error) {
        console.log("Unable to trigger daily celebration", error);
    }
}

function initializeDailyMissionReward() {
    const daily = document.querySelector("[data-daily-complete]");

    if (!daily || daily.dataset.dailyComplete !== "true") {
        return;
    }

    const rewardKey = [
        "dailyMissionReward",
        daily.dataset.dailyDate || "",
        daily.dataset.dailyStudent || ""
    ].join(":");

    if (window.localStorage.getItem(rewardKey)) {
        return;
    }

    window.localStorage.setItem(rewardKey, "played");

    setTimeout(() => {
        triggerDailyCelebration();
    }, 500);
}

function ensureKeyboardAudioContext() {
    keyboardAudioCtx = ensureBrowserAudioContext();
    return keyboardAudioCtx;
}

async function testBrowserSound() {
    await resetSoundState();

    const audioCtx = ensureBrowserAudioContext();

    try {
        await browserBeep(audioCtx, 120);
    } finally {
        await releaseBrowserAudioContext();
    }
}

async function resetSoundState() {
    stopBrowserPlayback();
    stopKeyboardTone();
    practiceAudioPlaying = false;

    await releaseBrowserAudioContext();

    try {
        await fetch("/audio-reset", {
            method: "POST"
        });
    } catch (error) {
        console.log("Unable to reset Pi audio state", error);
    }
}

async function releaseBrowserAudioContext() {
    if (browserAudioCtx && browserAudioCtx.state !== "closed") {
        try {
            await browserAudioCtx.close();
        } catch (error) {
            console.log("Unable to close browser audio context", error);
        }
    }

    browserAudioCtx = null;
    keyboardAudioCtx = null;
}

function setHomePlaybackState(isPlaying) {
    const playButton = document.getElementById("playHereButton");
    const stopButton = document.getElementById("stopHereButton");

    if (playButton) {
        playButton.disabled = isPlaying;
    }

    if (stopButton) {
        stopButton.disabled = !isPlaying;
    }
}

function startKeyboardTone() {
    if (keyboardToneOscillator) {
        return;
    }

    const audioCtx = ensureKeyboardAudioContext();
    const oscillator = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    oscillator.frequency.value = getMorseTiming().toneHz;
    oscillator.type = "sine";
    gain.gain.value = 0.2;

    oscillator.connect(gain);
    gain.connect(audioCtx.destination);
    oscillator.start();

    keyboardToneOscillator = oscillator;
    keyboardToneGain = gain;
}

function stopKeyboardTone() {
    if (!keyboardToneOscillator) {
        return;
    }

    keyboardToneOscillator.stop();
    keyboardToneOscillator.disconnect();

    if (keyboardToneGain) {
        keyboardToneGain.disconnect();
    }

    keyboardToneOscillator = null;
    keyboardToneGain = null;
}

async function playMorseText(morseText, playback = null) {
    if (!morseText) {
        return;
    }

    const audioCtx = ensureBrowserAudioContext();
    const timing = getMorseTiming();

    for (const ch of morseText) {
        if (playback && playback.cancelled) {
            return;
        }

        if (ch === ".") {
            await browserBeep(audioCtx, timing.dotMs, playback);
            await sleep(timing.symbolGapMs);
        } else if (ch === "-") {
            await browserBeep(audioCtx, timing.dashMs, playback);
            await sleep(timing.symbolGapMs);
        } else if (ch === " ") {
            await sleep(timing.letterGapMs);
        } else if (ch === "/") {
            await sleep(timing.wordGapMs);
        }
    }
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

    stopBrowserPlayback();

    const playback = {
        cancelled: false,
        oscillator: null
    };

    browserPlayback = playback;
    setHomePlaybackState(true);

    try {
        await playMorseText(morseText, playback);
    } finally {
        if (browserPlayback === playback) {
            browserPlayback = null;
            setHomePlaybackState(false);
        }
    }
}

async function playWordCard() {
    const panel = document.querySelector("[data-word-morse]");

    if (!panel) {
        return;
    }

    const morseText = (panel.dataset.wordMorse || "").trim();

    if (!morseText) {
        return;
    }

    setWordFeedback("");
    await stopWordPlayback();

    const playback = {
        cancelled: false,
        oscillator: null
    };

    browserPlayback = playback;

    try {
        const response = await fetch("/words/prompt-station", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ morse: morseText })
        });

        if (!response.ok) {
            await playMorseText(morseText, playback);
        }
    } finally {
        if (browserPlayback === playback) {
            browserPlayback = null;
        }
    }
}

async function stopWordPlayback() {
    stopBrowserPlayback();
    cancelWordAutoAdvance();

    try {
        await fetch("/words/stop", { method: "POST" });
    } catch (error) {
        console.log("Unable to stop word playback", error);
    }
}

function cancelWordAutoAdvance() {
    if (wordAutoAdvanceTimer) {
        clearTimeout(wordAutoAdvanceTimer);
    }

    wordAutoAdvanceTimer = null;
}

async function initializeWordPractice() {
    const panel = getWordPanel();

    if (!panel) {
        return;
    }

    await clearKeyInput();

    const params = new URLSearchParams(window.location.search);

    if (params.get("autoplay") === "1") {
        setWordFeedback("Get ready...");
        setTimeout(playWordCard, WORD_AUTOPLAY_DELAY_MS);
    }
}

function stopBrowserPlayback() {
    if (!browserPlayback) {
        setHomePlaybackState(false);
        return;
    }

    browserPlayback.cancelled = true;

    if (browserPlayback.oscillator) {
        try {
            browserPlayback.oscillator.stop();
        } catch (error) {
            // Already stopped.
        }
    }

    browserPlayback = null;
    setHomePlaybackState(false);
}

async function playPracticePromptInBrowser() {
    const panel = getPracticePanel();

    if (!panel || practiceAudioPlaying) {
        return;
    }

    practiceAudioPlaying = true;

    try {
        if (["listen", "echo", "learn"].includes(getPracticeMode())) {
            await playPracticePromptOnStation();
        } else {
            await triggerPracticePromptLed();
            await playMorseText(panel.dataset.expectedMorse || "");
        }
    } finally {
        practiceAudioPlaying = false;
        await releaseBrowserAudioContext();
    }
}

async function playPracticePromptOnStation() {
    const mode = getPracticeMode();

    try {
        await fetch(`/practice/prompt-station?mode=${encodeURIComponent(mode)}`, {
            method: "POST"
        });
    } catch (error) {
        console.log("Unable to play prompt on station", error);
    }
}

function triggerPracticePromptLed() {
    const mode = getPracticeMode();

    if (!["listen", "echo", "learn"].includes(mode)) {
        return Promise.resolve();
    }

    return fetch(`/practice/prompt-led?mode=${encodeURIComponent(mode)}&delay_ms=100`, {
        method: "POST"
    }).catch(error => {
        console.log("Unable to flash prompt LED", error);
    });
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
        const observedMorse = normalizeMorse(data.morse || "");

        if (observedMorse && observedMorse !== lastObservedPhysicalMorse && touchIdleExperience) {
            const wakeOnly = await touchIdleExperience.notePhysicalKey();
            lastObservedPhysicalMorse = observedMorse;

            if (wakeOnly) {
                await fetch("/clear-key", { method: "POST" });
                lastObservedPhysicalMorse = "";
                resetLiveKeyDisplay();
                return;
            }
        } else if (!observedMorse) {
            lastObservedPhysicalMorse = "";
        }

        if (data.morse) {
            renderMorseVisual(liveMorse, data.morse);
            liveDecoded.innerText = data.decoded || "?";
        } else {
            renderMorseVisual(liveMorse, "", "Waiting for key...");
            liveDecoded.innerText = "";
        }

        const messageKeyedWordMorse = document.getElementById("messageKeyedWordMorse");
        if (messageKeyedWordMorse) {
            messageKeyedWordMorse.value = data.morse || "";
        }

        schedulePracticeAutoCheck(data.morse || "");
        scheduleWordAutoCheck(data.morse || "", data.decoded || "");
        scheduleMessageKeyAutoCheck(data.morse || "");
        if (signalDropExperience) {
            signalDropExperience.handleMorse(data.morse || "", data.decoded || "");
        }
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

function getWordPanel() {
    return document.querySelector("[data-word-target][data-word-morse]");
}

function getBonusConfig() {
    const panel = getPracticePanel();

    if (!panel || !panel.dataset.bonusKind) {
        return null;
    }

    return {
        kind: panel.dataset.bonusKind,
        sessionId: panel.dataset.bonusSession || "",
        goal: Number(panel.dataset.bonusGoal) || 20
    };
}

function getPracticeMode() {
    const panel = getPracticePanel();
    return panel ? (panel.dataset.practiceMode || "send") : "send";
}

function normalizeMorse(value) {
    return value.trim().replace(/\s+/g, " ");
}

function morseAccessibleLabel(value) {
    return normalizeMorse(value)
        .split("/")
        .map(word => word.trim().split(/\s+/).filter(Boolean).map(letter => (
            [...letter].filter(symbol => ".-".includes(symbol)).map(symbol => symbol === "." ? "dot" : "dash").join(" ")
        )).filter(Boolean).join(", "))
        .filter(Boolean)
        .join("; word gap; ");
}

function renderMorseVisual(element, value, fallback = "") {
    if (!element) {
        return;
    }

    const normalized = normalizeMorse(value || "");
    element.dataset.morse = normalized;
    element.replaceChildren();

    if (!normalized) {
        element.innerText = fallback;
        return;
    }

    const visual = document.createElement("span");
    visual.className = "morse-visual";
    visual.setAttribute("role", "img");
    visual.setAttribute("aria-label", morseAccessibleLabel(normalized));

    normalized.split("/").forEach(rawWord => {
        const word = document.createElement("span");
        word.className = "morse-word";

        rawWord.trim().split(/\s+/).filter(Boolean).forEach(rawLetter => {
            const letter = document.createElement("span");
            letter.className = "morse-letter";
            [...rawLetter].filter(symbol => ".-".includes(symbol)).forEach(symbol => {
                const mark = document.createElement("i");
                mark.className = `morse-mark ${symbol === "." ? "morse-dot" : "morse-dash"}`;
                mark.setAttribute("aria-hidden", "true");
                letter.appendChild(mark);
            });
            if (letter.childElementCount) {
                word.appendChild(letter);
            }
        });

        if (word.childElementCount) {
            visual.appendChild(word);
        }
    });

    element.appendChild(visual);
}

function countMorseSymbols(value) {
    return value.replace(/[\s/]/g, "").length;
}

function practiceInstructionForMode(mode) {
    if (mode === "listen") {
        return "Listen and choose the letter.";
    }

    if (mode === "echo") {
        return "Listen, then key it back.";
    }

    if (mode === "learn") {
        return "Study the pattern, then key it.";
    }

    if (mode === "warmup") {
        return "Review the pattern, then key it.";
    }

    if (mode === "read") {
        return "Choose the matching letter.";
    }

    return "Key the letter shown.";
}

function feedbackResult(message) {
    const text = (message || "").trim();

    if (text.startsWith("Correct")) {
        return { label: "Correct!", className: "success" };
    }

    if (text.startsWith("Try") || text.startsWith("Not yet") || text.startsWith("Listen again")) {
        return { label: "Try Again", className: "needs-practice" };
    }

    return null;
}

function setTouchResultBanner(result) {
    const banner = document.getElementById("touchResultBanner");

    if (!banner) {
        return;
    }

    banner.classList.remove("success", "needs-practice");
    banner.hidden = !result;
    banner.innerText = result ? result.label : "";

    if (result) {
        banner.classList.add(result.className);
    }
}

function setPracticeFeedback(message) {
    const feedback = document.getElementById("practiceFeedback");

    if (!feedback) {
        return;
    }

    feedback.innerText = message;
    feedback.hidden = !message;

    feedback.classList.remove("success", "needs-practice");
    const result = feedbackResult(message);

    if (result) {
        feedback.classList.add(result.className);
    }

    setTouchResultBanner(result);
}

function setWordFeedback(message) {
    const feedback = document.getElementById("wordFeedback");

    if (!feedback) {
        return;
    }

    feedback.innerText = message;
    feedback.hidden = !message;
    feedback.classList.remove("success", "needs-practice");
    const result = feedbackResult(message);

    if (result) {
        feedback.classList.add(result.className);
    }

    setTouchResultBanner(result);
}

function setWordRhythmCoach(rhythm) {
    const panel = document.getElementById("wordRhythmCoach");
    const message = document.getElementById("wordRhythmMessage");
    const target = document.getElementById("wordRhythmTarget");
    const actual = document.getElementById("wordRhythmActual");

    if (!panel || !message || !target || !actual) {
        return;
    }

    target.innerHTML = "";
    actual.innerHTML = "";

    if (!rhythm || !Array.isArray(rhythm.target) || !Array.isArray(rhythm.actual) || rhythm.actual.length === 0) {
        panel.hidden = true;
        panel.closest(".touch-words-layout")?.classList.remove("has-rhythm-coach");
        message.innerText = "";
        return;
    }

    message.innerText = rhythm.message || "";
    renderRhythmTrack(target, rhythm.target);
    renderRhythmTrack(actual, rhythm.actual);
    panel.hidden = false;
    panel.closest(".touch-words-layout")?.classList.add("has-rhythm-coach");
}

function renderRhythmTrack(element, segments) {
    segments.forEach(segment => {
        const item = document.createElement("span");
        const type = segment.type === "gap" ? "gap" : "symbol";
        const status = segment.status || "target";
        item.className = `touch-rhythm-segment ${type} ${status}`;

        if (segment.type === "gap") {
            item.classList.add(segment.gap_type || "symbol");
            item.innerText = segment.gap_type === "word" ? "word pause" : segment.gap_type === "letter" ? "letter pause" : "";
            item.setAttribute("aria-label", segment.label || "symbol pause");
        } else {
            item.innerText = segment.label || "";
        }

        if (segment.duration_ms !== undefined && segment.duration_ms !== null) {
            item.title = `${segment.duration_ms} ms`;
        }

        element.appendChild(item);
    });
}

function resetPracticeAutoCheck() {
    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
    }

    practiceCheckTimer = null;
    lastCheckedPracticeMorse = "";
    pendingPracticeMorse = "";
    setPracticeFeedback("");
    resetWordAutoCheck();
}

function resetWordAutoCheck() {
    if (wordCheckTimer) {
        clearTimeout(wordCheckTimer);
    }

    cancelWordAutoAdvance();
    wordCheckTimer = null;
    lastCheckedWordMorse = "";
    pendingWordMorse = "";
    wordStartedAt = null;
    setWordFeedback("");
    setWordRhythmCoach(null);
}

function scheduleWordAutoCheck(rawMorse, decoded = "") {
    const panel = getWordPanel();

    if (!panel) {
        return;
    }

    const actualMorse = normalizeMorse(rawMorse);
    const expectedMorse = normalizeMorse(panel.dataset.wordMorse || "");

    if (!actualMorse) {
        resetWordAutoCheck();
        return;
    }

    if (wordStartedAt === null) {
        wordStartedAt = performance.now();
    }

    if (actualMorse === lastCheckedWordMorse) {
        return;
    }

    if (countMorseSymbols(actualMorse) < countMorseSymbols(expectedMorse)) {
        if (wordCheckTimer) {
            clearTimeout(wordCheckTimer);
            wordCheckTimer = null;
        }
        pendingWordMorse = "";
        return;
    }

    if (actualMorse === pendingWordMorse) {
        return;
    }

    if (wordCheckTimer) {
        clearTimeout(wordCheckTimer);
    }

    pendingWordMorse = actualMorse;
    wordCheckTimer = setTimeout(() => {
        checkWordAnswer(actualMorse, expectedMorse, panel.dataset.wordTarget || "", decoded);
    }, 1300);
}

async function checkWordAnswer(actualMorse, expectedMorse, target, decoded = "") {
    lastCheckedWordMorse = actualMorse;
    pendingWordMorse = "";
    const correct = actualMorse === expectedMorse;
    const elapsedMs = wordStartedAt === null ? null : Math.round(performance.now() - wordStartedAt);

    const result = await recordWordResult(target, correct, actualMorse, expectedMorse, decoded, elapsedMs);
    setWordRhythmCoach(result ? result.rhythm : null);

    if (correct) {
        setWordFeedback(`Correct: ${target}.`);
        rewardWordResult(true);
        scheduleWordAutoAdvance();
        return;
    }

    const heard = decoded ? ` I read ${decoded}.` : "";
    setWordFeedback(`Not yet. Clear first, then try ${target} again.${heard}`);
    rewardWordResult(false);
}

async function recordWordResult(target, correct, actualMorse, expectedMorse, decoded, elapsedMs) {
    try {
        const response = await fetch("/words/result", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                word: target,
                correct,
                actual_morse: actualMorse,
                expected_morse: expectedMorse,
                decoded,
                elapsed_ms: elapsedMs,
                timing_events: keyboardKeyerActive ? keyboardTimingEvents : []
            })
        });
        if (!response.ok) {
            return null;
        }
        return await response.json();
    } catch (error) {
        console.log("Unable to record word result", error);
        return null;
    }
}

function rewardWordResult(correct) {
    const panel = getWordPanel();

    if (panel) {
        panel.classList.remove("word-correct-reward", "word-needs-practice");
        void panel.offsetWidth;
        panel.classList.add(correct ? "word-correct-reward" : "word-needs-practice");
        setTimeout(() => {
            panel.classList.remove("word-correct-reward", "word-needs-practice");
        }, 2200);
    }
}

function scheduleWordAutoAdvance() {
    const nextLink = document.querySelector("[data-word-next]");

    if (!nextLink) {
        return;
    }

    cancelWordAutoAdvance();
    wordAutoAdvanceTimer = setTimeout(() => {
        window.location.href = nextLink.href;
    }, WORD_AUTO_ADVANCE_DELAY_MS);
}

function schedulePracticeAutoCheck(rawMorse) {
    const panel = getPracticePanel();

    if (!panel || !["send", "echo", "learn", "warmup"].includes(getPracticeMode()) || !practiceActive || practiceBusy) {
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

    const bonus = getBonusConfig();
    if (bonus) {
        const correct = actualMorse === expectedMorse;
        setPracticeFeedback(correct
            ? `Correct: ${target}.`
            : `Try ${target} again. Follow the example and keep your rhythm steady.`
        );
        recordPracticeResult(target, correct).then(data => {
            const summary = data ? data.bonus : null;
            updateBonusScore(summary);
            if (summary && summary.complete) {
                setPracticeFeedback(`Sprint complete: ${summary.correct}/${summary.goal} correct · ${summary.best_streak} best streak.`);
                practiceActive = false;
                practiceBusy = false;
                return;
            }

            setTimeout(loadNextPracticePrompt, 850);
        });
        return;
    }

    if (actualMorse === expectedMorse) {
        setPracticeFeedback(getPracticeMode() === "warmup"
            ? `Correct: ${target}. Take your time, then tap Next.`
            : `Correct: ${target}. Next letter coming up.`
        );
        recordPracticeResult(target, true).then(data => {
            if (getPracticeMode() === "warmup") {
                if (data && data.score && Number(data.score.mastery) >= 100) {
                    setPracticeFeedback("Warm-up complete. Next review coming up.");
                }
                setTimeout(loadNextPracticePrompt, 1800);
                return;
            }

            setTimeout(loadNextPracticePrompt, 950);
        });
    } else {
        const feedback = getPracticeMode() === "learn"
            ? `Try ${target} again. Follow the example and keep your rhythm steady.`
            : getPracticeMode() === "echo"
            ? `Listen again, then echo ${target}.`
            : getPracticeMode() === "warmup"
            ? `Review ${target}. Clear, then key it again.`
            : `Try ${target} again. Clear, then follow the example.`;
        setPracticeFeedback(feedback);
        recordPracticeResult(target, false).finally(() => {
            setTimeout(retryPracticePrompt, 1200);
        });
    }
}

async function recordPracticeResult(target, correct, answer = "") {
    const panel = getPracticePanel();
    const liveMorse = document.getElementById("liveMorse");
    const mode = getPracticeMode();
    const bonus = getBonusConfig();
    const actualMorse = ["read", "listen"].includes(mode)
        ? ""
        : normalizeMorse(keyboardKeyerActive ? keyboardMorse : (liveMorse ? (liveMorse.dataset.morse || "") : ""));

    try {
        const response = await fetch(bonus ? "/bonus/result" : "/practice/result", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                target,
                correct,
                answer,
                mode,
                session_id: bonus ? bonus.sessionId : "",
                expected_morse: panel ? (panel.dataset.expectedMorse || "") : "",
                actual_morse: actualMorse,
                timing_events: keyboardKeyerActive ? keyboardTimingEvents : []
            })
        });
        const data = await response.json();
        updateMorseTimingData(data.timing || null);
        updateProgressPanel(data.progress || []);
        updateScoreCard(data.score || null);
        updateOverallScoreCard(data.overall || null);
        updateBonusScore(data.bonus || null);
        return data;
    } catch (error) {
        console.log("Unable to record practice result", error);
        return null;
    }
}

async function loadNextPracticePrompt() {
    try {
        const bonus = getBonusConfig();
        const response = await fetch(bonus ? "/bonus/next" : `/practice/next?mode=${encodeURIComponent(getPracticeMode())}`, {
            method: "POST"
        });
        const data = await response.json();

        updatePracticePrompt(data.target, data.expected_morse, data.read_choices || []);
        updateMorseTimingData(data.timing || null);
        updateProgressPanel(data.progress || []);
        updateScoreCard(data.score || null);
        updateOverallScoreCard(data.overall || null);
        updateBonusScore(data.bonus || null);
        resetInputDisplay();
        const mode = getPracticeMode();
        if (bonus) {
            setPracticeFeedback("Next signal. Key it once.");
        } else if (mode === "listen") {
            setPracticeFeedback(practiceInstructionForMode(mode));
            playPracticePromptInBrowser();
        } else if (mode === "echo") {
            setPracticeFeedback(practiceInstructionForMode(mode));
            playPracticePromptInBrowser();
        } else if (mode === "learn") {
            setPracticeFeedback(practiceInstructionForMode(mode));
            playPracticePromptInBrowser();
        } else {
            setPracticeFeedback(practiceInstructionForMode(mode));
        }
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
        updateMorseTimingData(data.timing || null);
        updateProgressPanel(data.progress || []);
        updateScoreCard(data.score || null);
        updateOverallScoreCard(data.overall || null);
        resetInputDisplay();
        setPracticeFeedback("Ready. Try it again.");
        if (["listen", "echo", "learn"].includes(getPracticeMode())) {
            playPracticePromptInBrowser();
        }
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
    if (["send", "learn", "warmup"].includes(getPracticeMode())) {
        targetLetter.innerText = target;
        if (["learn", "warmup"].includes(getPracticeMode())) {
            renderMorseVisual(expected, expectedMorse);
        } else {
            expected.innerText = "?";
        }
    } else if (["listen", "echo"].includes(getPracticeMode())) {
        targetLetter.innerText = "?";
        expected.innerText = "Play Code";
    } else {
        targetLetter.innerText = "?";
        renderMorseVisual(expected, expectedMorse);
    }

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
        streak.innerText = `current set · ${score.streak} streak`;
    }

    if (accuracy) {
        accuracy.innerText = `${score.accuracy}% accuracy`;
    }

    if (attempts) {
        attempts.innerText = `${score.attempts} tries`;
    }

    if (goal) {
        if (score.mode === "warmup") {
            goal.innerText = score.next_goal;
        } else {
            goal.innerText = masteryValue >= 100
                ? "Mode complete. Go to Daily for the next step."
                : score.next_goal;
        }
    }
}

function updateBonusScore(summary) {
    if (!summary) {
        return;
    }

    const accuracy = document.getElementById("bonusAccuracy");
    const attempts = document.getElementById("bonusAttempts");
    const streak = document.getElementById("bonusStreak");
    const bestStreak = document.getElementById("bonusBestStreak");
    const remaining = document.getElementById("bonusRemaining");

    if (accuracy) {
        accuracy.innerText = `${summary.accuracy}%`;
    }

    if (attempts) {
        attempts.innerText = summary.attempts;
    }

    if (streak) {
        streak.innerText = summary.streak;
    }

    if (bestStreak) {
        bestStreak.innerText = summary.best_streak;
    }

    if (remaining) {
        remaining.innerText = summary.complete ? "Sprint complete" : `${summary.remaining} left`;
    }
}

function updateOverallScoreCard(overall) {
    if (!overall) {
        return;
    }

    const mastery = document.getElementById("overallMastery");
    const masteryBar = document.getElementById("overallMasteryBar");
    const accuracy = document.getElementById("overallAccuracy");
    const attempts = document.getElementById("overallAttempts");
    const streak = document.getElementById("overallStreak");
    const unlockedLetters = document.getElementById("overallUnlockedLetters");
    const learningLetters = document.getElementById("overallLearningLetters");
    const learningProgress = document.getElementById("overallLearningProgress");
    const alphabetProgress = document.getElementById("overallAlphabetProgress");
    const nextUnlock = document.getElementById("overallNextUnlock");
    const masteryValue = Math.max(0, Math.min(Number(overall.current_mastery ?? overall.mastery) || 0, 100));

    if (mastery) {
        mastery.innerText = `${masteryValue}%`;
    }

    if (masteryBar) {
        masteryBar.style.width = `${masteryValue}%`;
    }

    if (accuracy) {
        accuracy.innerText = `${overall.accuracy}% accuracy`;
    }

    if (attempts) {
        attempts.innerText = overall.attempts;
    }

    if (streak) {
        streak.innerText = `${overall.attempts} tries`;
    }

    if (alphabetProgress) {
        alphabetProgress.innerText = overall.alphabet_progress || "";
    }

    if (unlockedLetters && Array.isArray(overall.active_letters)) {
        unlockedLetters.innerHTML = overall.active_letters.map(letter => `<span>${letter}</span>`).join("");
    } else if (unlockedLetters && Array.isArray(overall.unlocked_letters)) {
        unlockedLetters.innerHTML = overall.unlocked_letters.map(letter => `<span>${letter}</span>`).join("");
    }

    if (learningLetters && Array.isArray(overall.learning_letters)) {
        learningLetters.innerHTML = overall.learning_letters.length
            ? overall.learning_letters.map(letter => `<span>${letter}</span>`).join("")
            : "<span>None</span>";
    }

    if (learningProgress) {
        const focus = overall.learning_focus || {};
        if (focus.active) {
            learningProgress.hidden = false;
            learningProgress.innerText = `Learn progress: ${focus.correct}/${focus.goal} · ${focus.remaining} left`;
        } else {
            learningProgress.hidden = true;
            learningProgress.innerText = "";
        }
    }

    if (nextUnlock && overall.next_unlock) {
        const letters = overall.next_unlock.letters || [];
        const learning = overall.learning_letters || [];
        nextUnlock.innerText = learning.length || overall.locked_until_tomorrow
            ? overall.next_goal
            : letters.length
            ? `Next letters after 100% current set: ${letters.join(" ")}`
            : overall.next_unlock.label;
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

    if (["read", "listen"].includes(getPracticeMode()) && input) {
        input.focus();
    }
}

function submitReadAnswer(answer) {
    const panel = getPracticePanel();

    if (!panel || !["read", "listen"].includes(getPracticeMode()) || practiceBusy || !practiceActive) {
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
        recordPracticeResult(target, true, normalizedAnswer).finally(() => {
            setTimeout(loadNextPracticePrompt, 850);
        });
    } else {
        const feedback = getPracticeMode() === "listen"
            ? `Try again. That was ${target}, not ${normalizedAnswer}.`
            : `Try again. That pattern is ${target}, not ${normalizedAnswer}.`;
        setPracticeFeedback(feedback);
        recordPracticeResult(target, false, normalizedAnswer).finally(() => {
            setTimeout(retryPracticePrompt, 1200);
        });
    }
}

function resetLiveKeyDisplay() {
    const liveMorse = document.getElementById("liveMorse");
    const liveDecoded = document.getElementById("liveDecoded");

    if (liveMorse) {
        renderMorseVisual(liveMorse, "", "Waiting for key...");
    }

    if (liveDecoded) {
        liveDecoded.innerText = "";
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
    stopKeyboardTone();
    keyboardPressStartedAt = null;
    keyboardLastReleasedAt = null;
    keyboardMorse = "";
    keyboardTimingEvents = [];
    resetLiveKeyDisplay();
    lastCheckedPracticeMorse = "";
    pendingPracticeMorse = "";

    if (practiceCheckTimer) {
        clearTimeout(practiceCheckTimer);
        practiceCheckTimer = null;
    }

    resetWordAutoCheck();
}

function updateVirtualKeyerDisplay() {
    const liveMorse = document.getElementById("liveMorse");
    const liveDecoded = document.getElementById("liveDecoded");
    const morse = normalizeMorse(keyboardMorse);

    if (liveMorse) {
        renderMorseVisual(liveMorse, morse, "Waiting for key...");
    }

    if (liveDecoded) {
        liveDecoded.innerText = morse ? (MORSE_DECODE[morse] || "?") : "";
    }

    schedulePracticeAutoCheck(morse);
    scheduleWordAutoCheck(morse, MORSE_DECODE[morse] || "");
    scheduleMessageKeyAutoCheck(morse);
    if (signalDropExperience) {
        signalDropExperience.handleMorse(morse, MORSE_DECODE[morse] || "");
    }
}

function initializeSignalDrop() {
    const panel = document.querySelector("[data-signal-drop]");
    if (!panel) {
        return;
    }

    const field = document.getElementById("signalDropField");
    const startOverlay = document.getElementById("signalDropStart");
    const toggle = document.getElementById("signalDropToggle");
    const choices = document.getElementById("signalDropChoices");
    const feedback = document.getElementById("signalDropFeedback");
    const feedbackTitle = document.getElementById("signalDropFeedbackTitle");
    const feedbackText = document.getElementById("signalDropFeedbackText");
    const reviewMorse = document.getElementById("signalDropReviewMorse");
    const scoreElement = document.getElementById("signalDropScore");
    const clearedElement = document.getElementById("signalDropCleared");
    const accuracyElement = document.getElementById("signalDropAccuracy");
    const streakElement = document.getElementById("signalDropStreak");
    const levelElement = document.getElementById("signalDropLevel");
    const mode = panel.dataset.gameMode === "read" ? "read" : "send";
    const sessionId = panel.dataset.sessionId || "";
    const activeLetters = JSON.parse(panel.dataset.activeLetters || "[]");
    const letterMorse = JSON.parse(panel.dataset.letterMorse || "{}");
    const targets = new Map();
    const reviewQueue = [];
    let running = false;
    let started = false;
    let busy = false;
    let nextTargetId = 1;
    let lastFrameAt = 0;
    let spawnElapsed = 0;
    let animationFrame = null;
    let morseTimer = null;
    let pendingMorse = "";
    let lastSubmittedMorse = "";
    let score = 0;
    let attempts = 0;
    let correct = 0;
    let cleared = 0;
    let streak = 0;
    let level = 1;

    const maxTargets = mode === "read" ? 4 : 5;
    const fallSpeed = () => Math.min(42, 15 + ((level - 1) * 4));
    const spawnDelay = () => Math.max(1500, 3300 - ((level - 1) * 260));

    function updateScore() {
        scoreElement.innerText = score;
        clearedElement.innerText = cleared;
        accuracyElement.innerText = attempts ? `${Math.round((correct / attempts) * 100)}%` : "0%";
        streakElement.innerText = streak;
        levelElement.innerText = level;
    }

    function showFeedback(title, text, target = "", needsWork = false) {
        feedbackTitle.innerText = title;
        feedbackText.innerText = text;
        feedback.classList.toggle("needs-work", needsWork);

        if (target && letterMorse[target]) {
            reviewMorse.hidden = false;
            renderMorseVisual(reviewMorse, letterMorse[target]);
        } else {
            reviewMorse.hidden = true;
            reviewMorse.innerText = "";
        }
    }

    function frontTarget() {
        return Array.from(targets.values()).sort((left, right) => right.y - left.y)[0] || null;
    }

    function removeTarget(target, className = "") {
        targets.delete(target.id);
        if (className) {
            target.node.classList.add(className);
            window.setTimeout(() => target.node.remove(), 220);
        } else {
            target.node.remove();
        }
    }

    function markTargetMiss(target) {
        target.node.classList.add("missed");
        window.setTimeout(() => {
            if (targets.has(target.id)) {
                target.node.classList.remove("missed");
            }
        }, 1000);
    }

    function matchingTargets(letter) {
        return Array.from(targets.values()).filter(target => target.letter === letter);
    }

    function shuffle(items) {
        const copy = [...items];
        for (let index = copy.length - 1; index > 0; index -= 1) {
            const swapIndex = Math.floor(Math.random() * (index + 1));
            [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
        }
        return copy;
    }

    function updateReadChoices() {
        if (!choices) {
            return;
        }

        const visible = [...new Set(Array.from(targets.values()).map(target => target.letter))];
        const fill = shuffle(activeLetters.filter(letter => !visible.includes(letter)));
        const options = shuffle([...visible, ...fill].slice(0, Math.min(8, activeLetters.length)));
        choices.innerHTML = "";

        options.forEach(letter => {
            const button = document.createElement("button");
            button.type = "button";
            button.innerText = letter;
            button.addEventListener("click", () => handleReadChoice(letter));
            choices.appendChild(button);
        });
    }

    async function requestTarget() {
        const reviewLetter = reviewQueue.length ? reviewQueue.shift() : "";
        const response = await fetch("/signal-drop/next", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ review_letter: reviewLetter })
        });
        return await response.json();
    }

    async function spawnTarget() {
        if (!running || targets.size >= maxTargets) {
            return;
        }

        try {
            const item = await requestTarget();
            if (!running || !item.target) {
                return;
            }

            const id = nextTargetId;
            nextTargetId += 1;
            const node = document.createElement("div");
            node.className = `signal-drop-target ${mode === "read" ? "read-target" : "send-target"}`;
            node.dataset.letter = item.target;
            if (mode === "read") {
                renderMorseVisual(node, item.expected_morse);
            } else {
                node.innerText = item.target;
            }

            const width = mode === "read" ? 112 : 94;
            const laneCount = mode === "read" ? 4 : 5;
            const lane = Math.floor(Math.random() * laneCount);
            const laneWidth = Math.max(width, field.clientWidth / laneCount);
            const x = Math.min(
                Math.max(0, (lane * laneWidth) + ((laneWidth - width) / 2)),
                Math.max(0, field.clientWidth - width)
            );
            const target = { id, letter: item.target, morse: item.expected_morse, x, y: -62, node };
            targets.set(id, target);
            field.appendChild(node);
            node.style.transform = `translate(${x}px, ${target.y}px)`;
            updateReadChoices();
        } catch (error) {
            showFeedback("Connection paused", "Trying the station again.", "", true);
        }
    }

    async function recordResult(target, values) {
        const response = await fetch("/signal-drop/result", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                game_mode: mode,
                target: target.letter,
                actual_morse: values.actualMorse || "",
                answer: values.answer || "",
                clear_count: values.clearCount || 0,
                reason: values.reason || "answer",
                timing_events: keyboardKeyerActive ? keyboardTimingEvents : []
            })
        });
        return await response.json();
    }

    async function finishAttempt(target, values) {
        if (busy || !target) {
            return;
        }

        busy = true;
        const matches = values.expectedCorrect ? matchingTargets(target.letter) : [target];
        if (values.expectedCorrect) {
            matches.forEach(item => removeTarget(item, "correct"));
        } else if (mode === "send" && values.reason !== "bottom") {
            markTargetMiss(target);
        } else {
            removeTarget(target, "missed");
        }
        updateReadChoices();

        try {
            const result = await recordResult(target, {
                ...values,
                clearCount: values.expectedCorrect ? matches.length : 0
            });
            attempts += 1;

            if (result.correct) {
                correct += 1;
                cleared += Math.max(1, result.clear_count || matches.length);
                streak += 1;
                score += Math.max(1, result.clear_count || matches.length) * 10 * level;
                level = Math.min(8, Math.max(level, 1 + Math.floor(streak / 4)));
                showFeedback(
                    matches.length > 1 ? `Great! ${matches.length} cleared` : "Correct!",
                    "Keep the streak going."
                );
            } else {
                streak = 0;
                level = Math.max(1, level - 1);
                reviewQueue.push(target.letter);
                showFeedback(
                    values.reason === "bottom" ? `Review ${target.letter}` : (mode === "send" ? "MISS" : "Not yet"),
                    values.reason === "bottom" ? "This signal will return soon." : `Review ${target.letter}; it will return soon.`,
                    target.letter,
                    true
                );
            }
            updateScore();
        } catch (error) {
            reviewQueue.push(target.letter);
            showFeedback("Try that again", "The result was not saved.", target.letter, true);
        } finally {
            busy = false;
            pendingMorse = "";
            lastSubmittedMorse = "";
            await clearKeyInput();
            if (running && targets.size === 0) {
                spawnElapsed = spawnDelay();
            }
        }
    }

    function handleReadChoice(letter) {
        if (!running || busy) {
            return;
        }
        const matches = matchingTargets(letter);
        const target = matches[0] || frontTarget();
        if (!target) {
            return;
        }
        finishAttempt(target, {
            answer: letter,
            expectedCorrect: matches.length > 0,
            reason: "answer"
        });
    }

    function handleMorse(rawMorse, decoded) {
        if (mode !== "send" || !running || busy) {
            return;
        }

        const morse = normalizeMorse(rawMorse);
        if (!morse || morse === lastSubmittedMorse) {
            return;
        }

        // Physical-key polling repeats the same value every 300 ms. Only a
        // changed pattern should restart the letter-completion timer.
        if (morse === pendingMorse) {
            return;
        }
        pendingMorse = morse;

        if (morseTimer) {
            window.clearTimeout(morseTimer);
        }
        morseTimer = window.setTimeout(() => {
            const letter = decoded || MORSE_DECODE[morse] || "";
            const matches = matchingTargets(letter);
            const target = matches[0] || frontTarget();
            if (!target) {
                clearKeyInput();
                return;
            }
            lastSubmittedMorse = morse;
            finishAttempt(target, {
                actualMorse: morse,
                expectedCorrect: matches.length > 0,
                reason: "answer"
            });
        }, 1050);
    }

    function animate(now) {
        if (!running) {
            return;
        }

        if (!lastFrameAt) {
            lastFrameAt = now;
        }
        const delta = Math.min(0.08, (now - lastFrameAt) / 1000);
        lastFrameAt = now;
        spawnElapsed += delta * 1000;

        let bottomMiss = null;
        targets.forEach(target => {
            target.y += fallSpeed() * delta;
            target.node.style.transform = `translate(${target.x}px, ${target.y}px)`;
            if (!bottomMiss && target.y >= field.clientHeight - 58) {
                bottomMiss = target;
            }
        });

        if (bottomMiss && !busy) {
            finishAttempt(bottomMiss, {
                expectedCorrect: false,
                reason: "bottom"
            });
        }

        if (spawnElapsed >= spawnDelay() && targets.size < maxTargets) {
            spawnElapsed = 0;
            spawnTarget();
        }

        animationFrame = window.requestAnimationFrame(animate);
    }

    function setRunning(nextRunning) {
        running = nextRunning;
        toggle.innerText = running ? "Pause" : (started ? "Resume" : "Start");

        if (running) {
            started = true;
            startOverlay.hidden = true;
            lastFrameAt = 0;
            if (targets.size === 0) {
                spawnTarget();
            }
            animationFrame = window.requestAnimationFrame(animate);
            showFeedback("Go!", mode === "send" ? "Key any falling letter." : "Touch a matching letter.");
        } else {
            if (animationFrame) {
                window.cancelAnimationFrame(animationFrame);
                animationFrame = null;
            }
            startOverlay.hidden = false;
            startOverlay.querySelector("strong").innerText = started ? "Paused" : "Ready?";
            startOverlay.querySelector("span").innerText = started
                ? "Tap Resume when you are ready."
                : "Accuracy first. The signals speed up as your streak grows.";
        }
    }

    toggle.addEventListener("click", () => setRunning(!running));
    updateReadChoices();
    updateScore();
    signalDropExperience = { handleMorse };
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

    if (keyboardKeyerActive && document.activeElement) {
        document.activeElement.blur();
    }

    if (!keyboardKeyerActive) {
        updateLiveKey();
    }
}

function ignoreKeyboardKeyerEvent(event) {
    const tagName = event.target && event.target.tagName;
    return !keyboardKeyerActive && ["INPUT", "TEXTAREA", "BUTTON", "A", "SELECT"].includes(tagName);
}

function handleKeyboardKeyDown(event) {
    if (!keyboardKeyerActive || event.code !== "Space" || event.repeat || ignoreKeyboardKeyerEvent(event)) {
        return;
    }

    event.preventDefault();

    if (keyboardPressStartedAt === null) {
        if (keyboardLastReleasedAt !== null) {
            keyboardTimingEvents.push({
                type: "gap",
                gap_type: "symbol",
                duration_ms: Math.round(performance.now() - keyboardLastReleasedAt)
            });
        }
        keyboardPressStartedAt = performance.now();
        startKeyboardTone();
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
    stopKeyboardTone();
    const symbol = durationMs >= getKeyboardDashThresholdMs() ? "-" : ".";
    keyboardMorse += symbol;
    keyboardTimingEvents.push({
        type: "symbol",
        symbol,
        duration_ms: Math.round(durationMs)
    });
    keyboardLastReleasedAt = performance.now();
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
    const listenReplay = document.getElementById("listenReplay");

    if (panel && toggle) {
        toggle.addEventListener("click", () => {
            practiceActive = !practiceActive;

            if (!practiceActive && practiceCheckTimer) {
                clearTimeout(practiceCheckTimer);
                practiceCheckTimer = null;
            }

            updatePracticeToggle();
        });
    }

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

    if (listenReplay) {
        listenReplay.addEventListener("click", playPracticePromptInBrowser);
    }

    document.querySelectorAll("[data-test-sound]").forEach(button => {
        button.addEventListener("click", testBrowserSound);
    });

    document.querySelectorAll("[data-word-play]").forEach(button => {
        button.addEventListener("click", playWordCard);
    });

    document.querySelectorAll("[data-word-stop]").forEach(button => {
        button.addEventListener("click", stopWordPlayback);
    });

    document.querySelectorAll("[data-word-clear]").forEach(button => {
        button.addEventListener("click", clearKeyInput);
    });

    const stopHereButton = document.getElementById("stopHereButton");
    if (stopHereButton) {
        stopHereButton.addEventListener("click", stopBrowserPlayback);
    }

    document.addEventListener("keydown", handleKeyboardKeyDown);
    document.addEventListener("keyup", handleKeyboardKeyUp);
    window.addEventListener("blur", stopKeyboardTone);

    updatePracticeToggle();
    updateKeyboardKeyerToggle();
    if (keyboardToggle || panel) {
        clearKeyInput();
    }
    if (panel && ["listen", "echo", "learn"].includes(getPracticeMode())) {
        setPracticeFeedback(practiceInstructionForMode(getPracticeMode()));
        setTimeout(playPracticePromptInBrowser, 350);
    }
    initializeWordPractice();
    initializeSignalDrop();
    focusReadInput();
}

function initializeTouchRedirect() {
    if (!document.body || document.body.classList.contains("touch-ui")) {
        return;
    }

    const params = new URLSearchParams(window.location.search);

    if (params.get("view") === "desktop") {
        return;
    }

    const touchCapable = navigator.maxTouchPoints > 0
        || window.matchMedia("(pointer: coarse)").matches;
    const touchSized = window.matchMedia("(max-width: 900px), (max-height: 540px)").matches;

    if (touchCapable || touchSized) {
        window.location.replace("/touch");
    }
}

function touchIdleDuration(name, fallback) {
    const localTestHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);

    if (!localTestHost) {
        return fallback;
    }

    const value = Number(new URLSearchParams(window.location.search).get(name));
    return Number.isFinite(value) && value >= 50 ? value : fallback;
}

function initializeTouchIdleExperience() {
    if (!document.body || !document.body.classList.contains("touch-ui")) {
        return;
    }

    if (window.location.pathname.startsWith("/touch/shutdown")) {
        return;
    }

    const screensaverIdleMs = touchIdleDuration("screensaver_ms", TOUCH_SCREENSAVER_IDLE_MS);
    const screensaverGuessMs = touchIdleDuration("screensaver_guess_ms", TOUCH_SCREENSAVER_GUESS_MS);
    const screensaverRevealMs = touchIdleDuration("screensaver_reveal_ms", TOUCH_SCREENSAVER_REVEAL_MS);
    const redirectMs = touchIdleDuration("operator_reset_ms", TOUCH_OPERATOR_RESET_MS);
    const redirectEnabled = window.location.pathname !== "/touch/students";
    const choices = Object.entries(MORSE_DECODE)
        .filter(([, character]) => /^[A-Z0-9]$/.test(character))
        .map(([morse, character]) => ({ morse, character }));
    const overlay = document.createElement("div");
    const item = document.createElement("div");
    const character = document.createElement("strong");
    const morse = document.createElement("div");
    let screensaverTimer = null;
    let redirectTimer = null;
    let rotationTimer = null;
    let keyerPollTimer = null;
    let active = false;
    let lastCharacter = "";
    let pendingCharacter = "";
    let suppressCoveredInputUntil = 0;

    overlay.className = "touch-screensaver";
    overlay.hidden = true;
    overlay.setAttribute("aria-hidden", "true");
    item.className = "touch-screensaver-item";
    character.className = "touch-screensaver-character";
    character.setAttribute("aria-hidden", "true");
    morse.className = "touch-screensaver-morse";
    item.append(character, morse);
    overlay.appendChild(item);
    document.body.appendChild(overlay);

    const clearTimer = timer => {
        if (timer) {
            window.clearTimeout(timer);
            window.clearInterval(timer);
        }
    };

    const revealCharacter = () => {
        character.innerText = pendingCharacter;
        item.classList.add("answer-visible");
        character.setAttribute("aria-hidden", "false");
        rotationTimer = window.setTimeout(beginRecallCycle, screensaverRevealMs);
    };

    const beginRecallCycle = () => {
        const available = choices.filter(choice => choice.character !== lastCharacter);
        const choice = available[Math.floor(Math.random() * available.length)] || choices[0];

        item.classList.remove("answer-visible");
        character.setAttribute("aria-hidden", "true");
        character.innerText = "";
        lastCharacter = choice.character;
        pendingCharacter = choice.character;
        renderMorseVisual(morse, choice.morse);
        item.style.left = `${25 + Math.random() * 50}%`;
        item.style.top = `${25 + Math.random() * 50}%`;
        rotationTimer = window.setTimeout(revealCharacter, screensaverGuessMs);
    };

    const stopKeyerWatch = () => {
        clearTimer(keyerPollTimer);
        keyerPollTimer = null;
    };

    const hideScreensaver = () => {
        active = false;
        clearTimer(rotationTimer);
        rotationTimer = null;
        stopKeyerWatch();
        item.classList.remove("answer-visible");
        character.setAttribute("aria-hidden", "true");
        overlay.hidden = true;
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("touch-screensaver-active");
    };

    const resetTimers = () => {
        clearTimer(screensaverTimer);
        clearTimer(redirectTimer);
        screensaverTimer = window.setTimeout(showScreensaver, screensaverIdleMs);

        if (redirectEnabled) {
            redirectTimer = window.setTimeout(() => {
                window.location.replace("/touch");
            }, redirectMs);
        }
    };

    const wakeFromPhysicalKey = async () => {
        if (!active) {
            resetTimers();
            return false;
        }

        hideScreensaver();
        resetTimers();

        try {
            await fetch("/clear-key", { method: "POST" });
        } catch (error) {
            console.log("Unable to clear screensaver wake key", error);
        }

        lastObservedPhysicalMorse = "";
        resetLiveKeyDisplay();
        return true;
    };

    const pollForWakeKey = async () => {
        if (!active) {
            return;
        }

        try {
            const response = await fetch("/live-key");
            const data = await response.json();
            if (normalizeMorse(data.morse || "")) {
                await wakeFromPhysicalKey();
            }
        } catch (error) {
            console.log("Unable to check screensaver wake key", error);
        }
    };

    const startKeyerWatch = async () => {
        try {
            await fetch("/clear-key", { method: "POST" });
        } catch (error) {
            console.log("Unable to prepare screensaver wake key", error);
        }

        if (active && !document.getElementById("liveMorse")) {
            keyerPollTimer = window.setInterval(pollForWakeKey, 300);
        }
    };

    function showScreensaver() {
        if (active) {
            return;
        }

        active = true;
        beginRecallCycle();
        overlay.hidden = false;
        overlay.setAttribute("aria-hidden", "false");
        document.body.classList.add("touch-screensaver-active");
        startKeyerWatch();
    }

    const handleUserActivity = event => {
        if (Date.now() < suppressCoveredInputUntil) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }

        if (active) {
            event.preventDefault();
            event.stopImmediatePropagation();
            suppressCoveredInputUntil = Date.now() + 700;
            hideScreensaver();
        }

        resetTimers();
    };

    ["pointerdown", "touchstart", "keydown", "click"].forEach(eventName => {
        document.addEventListener(eventName, handleUserActivity, {
            capture: true,
            passive: false
        });
    });

    touchIdleExperience = {
        isActive: () => active,
        notePhysicalKey: wakeFromPhysicalKey
    };

    resetTimers();
}

function getMessageKeyPanel() {
    return document.querySelector("[data-message-key][data-message-key-morse]");
}

function setMessageKeyFeedback(message, needsWork = false) {
    const element = document.getElementById("messageKeyFeedback");
    if (!element) {
        return;
    }
    element.innerText = message;
    element.classList.toggle("needs-work", needsWork);
}

function resetMessageKeyCheck() {
    if (messageKeyCheckTimer) {
        clearTimeout(messageKeyCheckTimer);
    }
    messageKeyCheckTimer = null;
    messageKeyLastMorse = "";
    messageKeyPendingMorse = "";
    messageKeyStartedAt = null;
}

function messageKeyCurrentMorse() {
    if (keyboardKeyerActive) {
        return normalizeMorse(keyboardMorse);
    }
    const liveMorse = document.getElementById("liveMorse");
    return normalizeMorse(liveMorse ? (liveMorse.dataset.morse || "") : "");
}

function renderMessageKeyLetterResults(result) {
    const letters = Array.from(document.querySelectorAll("#messageKeyLetters > strong"));
    const current = Array.isArray(result.letter_results) ? result.letter_results : [];
    const best = new Set(Array.isArray(result.best_letters) ? result.best_letters : []);
    letters.forEach((letter, index) => {
        letter.classList.toggle("best", best.has(index));
        letter.classList.toggle("miss", current.length > index && !current[index] && !best.has(index));
    });
}

async function submitMessageKeyAttempt(actualMorse) {
    const panel = getMessageKeyPanel();
    const normalized = normalizeMorse(actualMorse || "");
    if (!panel || !normalized || messageKeyBusy || normalized === messageKeyLastMorse) {
        if (!normalized) {
            setMessageKeyFeedback("Key the whole word first.", true);
        }
        return;
    }

    messageKeyBusy = true;
    messageKeyLastMorse = normalized;
    const elapsedMs = messageKeyStartedAt === null ? null : Math.round(performance.now() - messageKeyStartedAt);
    try {
        const response = await fetch("/touch/messages/key/result", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                recipient_id: panel.dataset.recipientId || "",
                word_index: Number(panel.dataset.wordIndex),
                actual_morse: normalized,
                elapsed_ms: elapsedMs,
                timing_events: keyboardKeyerActive ? keyboardTimingEvents : []
            })
        });
        const result = await response.json();
        if (!response.ok) {
            if (result.next_url) {
                window.location.href = result.next_url;
                return;
            }
            setMessageKeyFeedback(result.message || "Unable to check that word.", true);
            return;
        }

        renderMessageKeyLetterResults(result);
        const hint = document.querySelector("[data-message-key-hint]");
        const continueButton = document.querySelector("[data-message-key-continue]");
        if (hint) {
            hint.disabled = false;
        }
        if (continueButton) {
            continueButton.disabled = !result.can_continue;
        }

        if (result.correct) {
            setMessageKeyFeedback(`Correct: ${result.word}. Moving to the next step.`);
            window.setTimeout(() => {
                window.location.href = result.next_url;
            }, 2000);
        } else {
            setMessageKeyFeedback(`Not yet. Clear, then try ${result.word} again.`, true);
        }
    } catch (error) {
        console.log("Unable to record message keying attempt", error);
        setMessageKeyFeedback("Could not check the word. Please try again.", true);
    } finally {
        messageKeyBusy = false;
        messageKeyPendingMorse = "";
    }
}

function scheduleMessageKeyAutoCheck(rawMorse) {
    const panel = getMessageKeyPanel();
    if (!panel || messageKeyBusy) {
        return;
    }
    const actual = normalizeMorse(rawMorse);
    const expected = normalizeMorse(panel.dataset.messageKeyMorse || "");
    if (!actual) {
        if (messageKeyCheckTimer) {
            clearTimeout(messageKeyCheckTimer);
        }
        messageKeyCheckTimer = null;
        messageKeyPendingMorse = "";
        messageKeyLastMorse = "";
        messageKeyStartedAt = null;
        return;
    }
    if (messageKeyStartedAt === null) {
        messageKeyStartedAt = performance.now();
    }
    if (actual === messageKeyLastMorse || actual === messageKeyPendingMorse) {
        return;
    }
    if (countMorseSymbols(actual) < countMorseSymbols(expected)) {
        if (messageKeyCheckTimer) {
            clearTimeout(messageKeyCheckTimer);
        }
        messageKeyCheckTimer = null;
        messageKeyPendingMorse = "";
        return;
    }
    if (messageKeyCheckTimer) {
        clearTimeout(messageKeyCheckTimer);
    }
    messageKeyPendingMorse = actual;
    messageKeyCheckTimer = setTimeout(() => submitMessageKeyAttempt(actual), 1400);
}

async function messageKeyAction(panel, action) {
    const response = await fetch("/touch/messages/key/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            recipient_id: panel.dataset.recipientId || "",
            word_index: Number(panel.dataset.wordIndex),
            action
        })
    });
    const result = await response.json();
    if (!response.ok) {
        setMessageKeyFeedback(result.message || "That action is not ready yet.", true);
        return null;
    }
    return result;
}

function initializeMessageKeying(panel) {
    resetMessageKeyCheck();
    const check = document.querySelector("[data-message-key-check]");
    const retry = document.querySelector("[data-message-key-retry]");
    const hint = document.querySelector("[data-message-key-hint]");
    const continueButton = document.querySelector("[data-message-key-continue]");

    if (check) {
        check.addEventListener("click", () => submitMessageKeyAttempt(messageKeyCurrentMorse()));
    }
    if (retry) {
        retry.addEventListener("click", async () => {
            await clearKeyInput();
            resetMessageKeyCheck();
            setMessageKeyFeedback(`Ready. Try ${panel.dataset.messageKeyWord || "the word"} again.`);
        });
    }
    if (hint) {
        hint.addEventListener("click", async () => {
            hint.disabled = true;
            try {
                const result = await messageKeyAction(panel, "show-code");
                if (result) {
                    document.getElementById("messageKeyCode")?.classList.remove("hidden");
                    setMessageKeyFeedback("Code shown. Clear, then key the whole word again.");
                }
            } finally {
                hint.disabled = false;
            }
        });
    }
    if (continueButton) {
        continueButton.addEventListener("click", async () => {
            continueButton.disabled = true;
            const result = await messageKeyAction(panel, "continue-with-help");
            if (result) {
                setMessageKeyFeedback("Good effort. Moving to the next step.");
                window.setTimeout(() => {
                    window.location.href = result.next_url;
                }, 1200);
            } else {
                continueButton.disabled = false;
            }
        });
    }
}

function initializeMessageControls() {
    const composer = document.querySelector("[data-message-compose]");
    const messageKeyPanel = document.querySelector("[data-message-key]");
    if ((composer && document.getElementById("messageKeyedWordMorse")) || messageKeyPanel) {
        fetch("/clear-key", { method: "POST" }).catch(error => {
            console.log("Unable to clear message key", error);
        });
    }

    document.querySelectorAll("[data-message-retry-word]").forEach(button => {
        button.addEventListener("click", async () => {
            button.disabled = true;
            await clearKeyInput();
            button.disabled = false;
        });
    });

    document.querySelectorAll("[data-message-play-draft]").forEach(button => {
        button.addEventListener("click", async () => {
            button.disabled = true;
            try {
                await fetch("/touch/messages/play-draft", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ recipient_id: button.dataset.recipientId || "" })
                });
            } finally {
                button.disabled = false;
            }
        });
    });

    document.querySelectorAll("[data-message-play]").forEach(button => {
        button.addEventListener("click", async () => {
            const messageId = button.dataset.messageId || "";
            const scope = button.dataset.scope || "message";
            button.disabled = true;
            try {
                await fetch(`/touch/messages/inbox/${encodeURIComponent(messageId)}/play`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ scope })
                });
            } finally {
                button.disabled = false;
            }
        });
    });

    if (messageKeyPanel) {
        initializeMessageKeying(messageKeyPanel);
    }
}

function updateTouchPinDisplay(input, display) {
    if (!display) {
        return;
    }

    const length = (input.value || "").length;
    display.innerText = length ? "•".repeat(length) : "PIN";
}

function syncTouchPinCopies(input) {
    document.querySelectorAll("[data-touch-pin-copy]").forEach(copy => {
        copy.value = input.value || "";
    });
}

function initializeTouchPinPads() {
    document.querySelectorAll("[data-touch-pin-pad]").forEach(pad => {
        const form = pad.closest("form");
        const input = form ? form.querySelector("[data-touch-pin-input]") : null;
        const display = form ? form.querySelector("[data-touch-pin-display]") : null;

        if (!input) {
            return;
        }

        input.tabIndex = -1;
        updateTouchPinDisplay(input, display);
        syncTouchPinCopies(input);

        pad.querySelectorAll("[data-touch-pin-digit]").forEach(button => {
            button.addEventListener("click", () => {
                input.value = `${input.value || ""}${button.dataset.touchPinDigit || ""}`.slice(0, 32);
                updateTouchPinDisplay(input, display);
                syncTouchPinCopies(input);
            });
        });

        const clearButton = pad.querySelector("[data-touch-pin-clear]");
        if (clearButton) {
            clearButton.addEventListener("click", () => {
                input.value = "";
                updateTouchPinDisplay(input, display);
                syncTouchPinCopies(input);
            });
        }

        const backButton = pad.querySelector("[data-touch-pin-back]");
        if (backButton) {
            backButton.addEventListener("click", () => {
                input.value = (input.value || "").slice(0, -1);
                updateTouchPinDisplay(input, display);
                syncTouchPinCopies(input);
            });
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initializeTouchRedirect();
    initializeTouchIdleExperience();
    initializePracticeMode();
    initializeDailyMissionReward();
    initializeMessageControls();
    initializeTouchPinPads();
    initializeWordPractice();

    if (document.getElementById("liveMorse") && document.getElementById("liveDecoded")) {
        updateLiveKey();
        setInterval(updateLiveKey, 300);
    }
});

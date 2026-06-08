function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

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
    } catch (error) {
        console.log("Unable to update key display", error);
    }
}

async function clearKeyInput() {
    await fetch("/clear-key", {
        method: "POST"
    });

    updateLiveKey();
}

document.addEventListener("DOMContentLoaded", () => {
    updateLiveKey();
    setInterval(updateLiveKey, 300);
});

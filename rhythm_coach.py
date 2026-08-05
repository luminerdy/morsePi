GAP_RANK = {
    "symbol": 1,
    "letter": 2,
    "word": 3,
}

GAP_LABELS = {
    "symbol": "symbol pause",
    "letter": "letter pause",
    "word": "word pause",
}


def normalize_morse(value):
    return " ".join(str(value or "").strip().split())


def expected_segments(morse):
    segments = []
    words = [word for word in normalize_morse(morse).split(" / ") if word]

    for word_index, word in enumerate(words):
        letters = [letter for letter in word.split(" ") if letter]
        for letter_index, letter in enumerate(letters):
            for symbol_index, symbol in enumerate(letter):
                if symbol in ".-":
                    segments.append({"type": "symbol", "label": symbol, "status": "target"})
                if symbol_index < len(letter) - 1:
                    segments.append({"type": "gap", "gap_type": "symbol", "label": GAP_LABELS["symbol"], "status": "target"})
            if letter_index < len(letters) - 1:
                segments.append({"type": "gap", "gap_type": "letter", "label": GAP_LABELS["letter"], "status": "target"})
        if word_index < len(words) - 1:
            segments.append({"type": "gap", "gap_type": "word", "label": GAP_LABELS["word"], "status": "target"})

    return segments


def actual_segments(events):
    segments = []
    for event in events or []:
        event_type = event.get("type")
        if event_type == "symbol" and event.get("symbol") in ".-":
            segments.append({
                "type": "symbol",
                "label": event["symbol"],
                "duration_ms": event.get("duration_ms"),
                "status": "unknown",
            })
        elif event_type == "gap":
            gap_type = event.get("gap_type", "symbol")
            if gap_type not in GAP_RANK:
                gap_type = "symbol"
            segments.append({
                "type": "gap",
                "gap_type": gap_type,
                "label": GAP_LABELS[gap_type],
                "duration_ms": event.get("duration_ms"),
                "status": "unknown",
            })
    return segments


def compare_segments(target, actual):
    target_symbols = [segment for segment in target if segment["type"] == "symbol"]
    target_gaps = [segment for segment in target if segment["type"] == "gap"]
    actual_symbols = [segment for segment in actual if segment["type"] == "symbol"]
    actual_gaps = [segment for segment in actual if segment["type"] == "gap"]
    first_issue = ""

    for index, segment in enumerate(actual_symbols):
        expected = target_symbols[index] if index < len(target_symbols) else None
        if expected and segment["label"] == expected["label"]:
            segment["status"] = "good"
        else:
            segment["status"] = "check"
            first_issue = first_issue or "Check the dot and dash pattern."

    for index, segment in enumerate(actual_gaps):
        expected = target_gaps[index] if index < len(target_gaps) else None
        if expected is None:
            segment["status"] = "extra"
            first_issue = first_issue or "There is an extra pause."
            continue

        actual_rank = GAP_RANK[segment["gap_type"]]
        expected_rank = GAP_RANK[expected["gap_type"]]
        if actual_rank == expected_rank:
            segment["status"] = "good"
        elif actual_rank > expected_rank:
            segment["status"] = "too-long"
            if segment["gap_type"] == "word" and expected["gap_type"] == "letter":
                first_issue = first_issue or "That pause was too long between letters. I heard a word break."
            elif expected["gap_type"] == "symbol":
                first_issue = first_issue or "That pause split one letter apart. Keep symbols in a letter closer together."
            else:
                first_issue = first_issue or "That pause was a little too long."
        else:
            segment["status"] = "too-short"
            if expected["gap_type"] == "letter":
                first_issue = first_issue or "Add a little more pause between letters."
            elif expected["gap_type"] == "word":
                first_issue = first_issue or "Add a bigger word pause."
            else:
                first_issue = first_issue or "Add a tiny pause between symbols."

    return first_issue


def rhythm_coach(expected_morse, actual_morse, events, correct=False):
    target = expected_segments(expected_morse)
    actual = actual_segments(events)

    if not actual and actual_morse:
        actual = expected_segments(actual_morse)

    message = compare_segments(target, actual)
    if not message:
        message = "Great rhythm." if correct else "Good try. Compare your rhythm to the target."

    return {
        "message": message,
        "target": target,
        "actual": actual,
    }

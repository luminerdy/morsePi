from html import escape


class SafeMorseMarkup(str):
    def __html__(self):
        return self


def morse_accessible_label(value):
    words = []
    for raw_word in str(value or "").strip().split("/"):
        letters = []
        for raw_letter in raw_word.strip().split():
            symbols = ["dot" if symbol == "." else "dash" for symbol in raw_letter if symbol in ".-"]
            if symbols:
                letters.append(" ".join(symbols))
        if letters:
            words.append(", ".join(letters))
    return "; word gap; ".join(words)


def morse_visual(value):
    raw = str(value or "").strip()
    label = morse_accessible_label(raw)
    if not label:
        return SafeMorseMarkup(escape(raw))

    rendered_words = []
    for raw_word in raw.split("/"):
        rendered_letters = []
        for raw_letter in raw_word.strip().split():
            marks = []
            for symbol in raw_letter:
                if symbol == ".":
                    marks.append('<i class="morse-mark morse-dot" aria-hidden="true"></i>')
                elif symbol == "-":
                    marks.append('<i class="morse-mark morse-dash" aria-hidden="true"></i>')
            if marks:
                rendered_letters.append(f'<span class="morse-letter">{"".join(marks)}</span>')
        if rendered_letters:
            rendered_words.append(f'<span class="morse-word">{"".join(rendered_letters)}</span>')

    return SafeMorseMarkup(
        f'<span class="morse-visual" role="img" aria-label="{escape(label)}">'
        f'{"".join(rendered_words)}</span>'
    )

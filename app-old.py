from flask import Flask, render_template, request, redirect, url_for
from morse import text_to_morse
from morse_output import play_morse
import threading

app = Flask(__name__)

last_message = ""
last_morse = ""


def play_in_background(morse):
    thread = threading.Thread(target=play_morse, args=(morse,))
    thread.daemon = True
    thread.start()


@app.route("/", methods=["GET", "POST"])
def index():
    global last_message, last_morse

    if request.method == "POST":
        last_message = request.form.get("message", "")
        last_morse = text_to_morse(last_message)

    return render_template(
        "index.html",
        message=last_message,
        morse=last_morse
    )


@app.route("/play", methods=["POST"])
def play():
    if last_morse:
        play_in_background(last_morse)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

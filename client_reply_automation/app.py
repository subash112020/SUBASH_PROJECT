import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for

from asterisk_service import send_voice_to_asterisk
from monitor_service import check_once, get_monitor_status, start_monitor, stop_monitor
from summary_service import summarize_enquiry
from tts_service import synthesize_speech

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.post("/enquiries")
def submit_enquiry():
    """Summarize an enquiry, create its voice file, and send it to Asterisk."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    message = str(data.get("message", "")).strip()

    missing_fields = [
        field for field, value in (("name", name), ("phone", phone), ("message", message))
        if not value
    ]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Missing required field(s): {', '.join(missing_fields)}.",
        }), 400

    enquiry_id = uuid4().hex
    summary = summarize_enquiry(name, message)
    audio_path = Path("generated_audio") / f"client-enquiry-{enquiry_id}.wav"

    try:
        synthesize_speech(summary, audio_path)
        result = send_voice_to_asterisk(audio_path, enquiry_id, phone)
    except (OSError, RuntimeError, ValueError, ConnectionError) as error:
        return jsonify({
            "status": "error",
            "message": str(error),
            "summary": summary,
        }), 503

    return jsonify({
        "status": "called" if result.get("call_started") else "ready",
        "message": "Enquiry voice sent to Asterisk.",
        "enquiry_id": enquiry_id,
        "name": name,
        "phone": phone,
        "summary": summary,
        "audio_path": str(audio_path),
        "audio_url": url_for("audio_file", filename=audio_path.name),
        **result,
    }), 201


@app.get("/check-reply")
def check_reply():
    """Manually trigger one Gmail check for testing."""
    try:
        result = check_once()
    except (OSError, RuntimeError, ValueError, ConnectionError) as error:
        return jsonify({"status": "error", "message": f"Gmail check failed: {error}"}), 503
    monitor_result = get_monitor_status().get("last_result", {})
    if (
        result.get("status") == "waiting"
        and result.get("reply_id")
        and monitor_result.get("reply_id") == result["reply_id"]
        and monitor_result.get("status") not in {"waiting", "stopped", "starting"}
    ):
        result = monitor_result
    audio_path = result.get("audio_path")
    if audio_path:
        result["audio_url"] = url_for(
            "audio_file",
            filename=Path(audio_path).name,
        )
    return jsonify(result)


@app.get("/audio/<path:filename>")
def audio_file(filename):
    """Serve generated WAV files for browser playback."""
    return send_from_directory("generated_audio", filename)


@app.get("/monitor-status")
def monitor_status():
    return jsonify(get_monitor_status())


@app.post("/monitor/start")
def monitor_start():
    return jsonify(start_monitor())


@app.post("/monitor/stop")
def monitor_stop():
    return jsonify(stop_monitor())


if __name__ == "__main__":
    # Start the Gmail monitor once. Disable Flask's reloader so it is not started twice.
    if os.getenv("ENABLE_REPLY_MONITOR", "1") == "1":
        start_monitor()

    app.run(debug=False, host="127.0.0.1", port=5000)

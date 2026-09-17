import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import pytz

from asterisk_service import send_voice_to_asterisk
from gmail_service import get_gmail_service, get_latest_client_reply
from summary_service import summarize_reply
from tts_service import synthesize_speech

TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Asia/Kolkata"))
WORK_START = int(os.getenv("WORK_START", "9"))
WORK_END = int(os.getenv("WORK_END", "18"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))
CLIENT_EMAIL = os.getenv("CLIENT_EMAIL", "")
STATE_FILE = Path(os.getenv("STATE_FILE", "reply_state.json"))

_started = False
_lock = threading.Lock()
_stop_event = threading.Event()
_thread = None
_last_result = {"status": "stopped", "message": "Monitor is stopped."}
_last_event = None
_last_check_at = None


def is_working_hours():
    now = datetime.now(TIMEZONE)
    return WORK_START <= now.hour < WORK_END


def _load_last_message_id():
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_message_id")
    except (OSError, json.JSONDecodeError):
        return None


def _save_last_message_id(message_id):
    STATE_FILE.write_text(
        json.dumps({"last_message_id": message_id}, indent=2),
        encoding="utf-8"
    )


def process_reply(reply):
    reply_id = reply["id"]
    summary = summarize_reply(reply.get("from", CLIENT_EMAIL), reply.get("body", ""))
    audio_path = Path("generated_audio") / f"client-reply-{reply_id}.wav"
    synthesize_speech(summary, audio_path)
    return send_voice_to_asterisk(
        audio_path,
        f"reply-{reply_id}",
        os.getenv("MY_PHONE", "")
    )


def check_once(service=None):
    """Check once for a new client reply. Returns a status dictionary."""
    service = service or get_gmail_service()
    reply = get_latest_client_reply(service, CLIENT_EMAIL)
    if not reply:
        return {"status": "waiting", "message": "No received client email found."}

    last_id = _load_last_message_id()
    if last_id is None:
        # Baseline the mailbox so an old email does not trigger a call on startup.
        _save_last_message_id(reply["id"])
        return {
            "status": "baseline",
            "message": "Latest existing email recorded. Waiting for a new client reply.",
            "reply_id": reply["id"],
            "sender": reply.get("from", ""),
            "subject": reply.get("subject", ""),
        }

    if reply["id"] == last_id:
        return {
            "status": "waiting",
            "message": "No new client reply. The latest received email is already processed.",
            "reply_id": reply["id"],
            "sender": reply.get("from", ""),
            "subject": reply.get("subject", ""),
        }

    # Mark it as seen before calling so the same reply cannot trigger repeatedly.
    _save_last_message_id(reply["id"])

    if not is_working_hours():
        return {
            "status": "outside_hours",
            "message": "New reply detected, but it is outside working hours.",
            "new_reply": True,
            "reply_id": reply["id"],
            "sender": reply.get("from", ""),
            "subject": reply.get("subject", ""),
            "summary": summarize_reply(reply.get("from", CLIENT_EMAIL), reply.get("body", "")),
        }

    try:
        result = process_reply(reply)
        summary = summarize_reply(reply.get("from", CLIENT_EMAIL), reply.get("body", ""))
        return {
            "status": "called" if result.get("call_started") else "ready",
            "message": "New client reply detected and sent to Asterisk.",
            "new_reply": True,
            "reply_id": reply["id"],
            "sender": reply.get("from", ""),
            "subject": reply.get("subject", ""),
            "summary": summary,
            **result,
            "audio_path": str(Path("generated_audio") / f"client-reply-{reply['id']}.wav"),
        }
    except (OSError, RuntimeError, ValueError, ConnectionError) as error:
        return {
            "status": "error",
            "message": str(error),
            "new_reply": True,
            "reply_id": reply["id"],
            "sender": reply.get("from", ""),
            "subject": reply.get("subject", ""),
            "summary": summarize_reply(reply.get("from", CLIENT_EMAIL), reply.get("body", "")),
        }


def monitor_loop(stop_event):
    print("Client Reply Monitor started")
    print(f"Watching: {CLIENT_EMAIL or 'all received inbox email'}")
    print(f"Working hours: {WORK_START}:00-{WORK_END}:00 ({TIMEZONE.zone})")
    print(f"Checking every {POLL_SECONDS} seconds")

    global _last_check_at, _last_result, _last_event, _started, _thread
    try:
        service = get_gmail_service()
        while not stop_event.is_set():
            try:
                result = check_once(service)
                with _lock:
                    _last_result = result
                    if result.get("new_reply"):
                        _last_event = result
                    _last_check_at = datetime.now(TIMEZONE).isoformat()
                print(f"[{datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}] {result['message']}")
            except Exception as error:
                result = {"status": "error", "message": str(error)}
                with _lock:
                    _last_result = result
                    _last_check_at = datetime.now(TIMEZONE).isoformat()
                print(f"Monitor error: {error}")
            stop_event.wait(POLL_SECONDS)
    finally:
        with _lock:
            _started = False
            _thread = None
            _last_result = {"status": "stopped", "message": "Monitor is stopped."}


def start_monitor():
    global _started, _stop_event, _thread, _last_result, _last_event
    with _lock:
        if _started:
            return {"running": True, "message": "Monitor is already running."}
        _started = True
        _stop_event = threading.Event()
        _last_result = {"status": "starting", "message": "Monitor is starting."}
        _thread = threading.Thread(
            target=monitor_loop,
            args=(_stop_event,),
            name="gmail-reply-monitor",
            daemon=True,
        )
        _thread.start()
        return {"running": True, "message": "Monitor started."}


def stop_monitor():
    global _stop_event
    with _lock:
        if not _started:
            return {"running": False, "message": "Monitor is already stopped."}
        _stop_event.set()
        return {"running": False, "message": "Monitor stopped."}


def get_monitor_status():
    with _lock:
        return {
            "running": _started,
            "current_time": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": TIMEZONE.zone,
            "last_check_at": _last_check_at,
            "last_result": dict(_last_result),
            "last_event": dict(_last_event) if _last_event else None,
        }

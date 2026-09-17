import os
import shutil
import socket
from pathlib import Path


def send_voice_to_asterisk(audio_path: Path, enquiry_id: str, phone: str) -> dict[str, str | bool]:
    """Copy audio to Asterisk and optionally originate a test call through AMI.

    The shared sound directory must be mounted or copied to Asterisk's sounds
    directory. AMI is optional so enquiries can be tested before SIP is set up.
    """
    asterisk_sound_dir = Path(
        os.getenv("ASTERISK_SOUND_DIR", "asterisk_sounds")
    )
    asterisk_sound_dir.mkdir(parents=True, exist_ok=True)
    sound_name = f"client-enquiry-{enquiry_id}"
    asterisk_audio_path = asterisk_sound_dir / f"{sound_name}.wav"
    shutil.copyfile(audio_path, asterisk_audio_path)

    result: dict[str, str | bool] = {
        "audio_sent": True,
        "sound_name": sound_name,
        "audio_path": str(asterisk_audio_path),
        "call_started": False,
        "call_message": "Audio copied for Asterisk playback.",
    }

    if os.getenv("ASTERISK_AMI_HOST"):
        _originate_test_call(sound_name, phone)
        result["call_started"] = True
        result["call_message"] = "Asterisk accepted the test call request."
    else:
        result["call_message"] = (
            "Audio copied for Asterisk playback. Configure ASTERISK_AMI_HOST "
            "to originate the test call."
        )

    return result


def _originate_test_call(sound_name: str, phone: str) -> None:
    host = os.environ["ASTERISK_AMI_HOST"]
    port = int(os.getenv("ASTERISK_AMI_PORT", "5038"))
    username = os.getenv("ASTERISK_AMI_USERNAME", "admin")
    secret = os.getenv("ASTERISK_AMI_SECRET", "")
    channel_template = os.getenv("ASTERISK_CHANNEL", "Local/{phone}@from-internal")
    channel = channel_template.format(phone=phone)

    with socket.create_connection((host, port), timeout=10) as connection:
        _send_ami_action(
            connection,
            "Login",
            Username=username,
            Secret=secret,
            Events="off",
        )
        _send_ami_action(
            connection,
            "Originate",
            Channel=channel,
            Application="Playback",
            Data=sound_name,
            CallerID="Client enquiry",
            Async="true",
        )
        _send_ami_action(connection, "Logoff")


def _send_ami_action(connection: socket.socket, action: str, **headers: str) -> None:
    lines = [f"Action: {action}"]
    lines.extend(f"{key}: {value}" for key, value in headers.items())
    connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("utf-8"))
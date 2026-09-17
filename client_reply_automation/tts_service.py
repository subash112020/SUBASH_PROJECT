import audioop
import tempfile
import wave
from pathlib import Path


def synthesize_speech(text: str, output_path: Path) -> None:
    """Render speech locally through the installed operating-system TTS engine."""
    try:
        import pyttsx3
    except ImportError as error:
        raise RuntimeError(
            "Local TTS is not installed. Run: pip install -r requirements.txt"
        ) from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary_dir:
        temporary_path = Path(temporary_dir) / "speech.wav"
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.save_to_file(text, str(temporary_path))
        engine.runAndWait()
        engine.stop()

        if not temporary_path.exists() or temporary_path.stat().st_size == 0:
            raise RuntimeError("The local TTS engine did not create an audio file.")

        with wave.open(str(temporary_path), "rb") as source:
            audio = source.readframes(source.getnframes())
            if source.getnchannels() != 1:
                audio = audioop.tomono(audio, source.getsampwidth(), 0.5, 0.5)
            if source.getframerate() != 8000:
                audio, _ = audioop.ratecv(
                    audio,
                    source.getsampwidth(),
                    1,
                    source.getframerate(),
                    8000,
                    None,
                )

        with wave.open(str(output_path), "wb") as destination:
            destination.setnchannels(1)
            destination.setsampwidth(2)
            destination.setframerate(8000)
            destination.writeframes(audio)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("The local TTS engine did not create an audio file.")
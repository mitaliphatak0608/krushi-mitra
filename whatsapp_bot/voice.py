"""whatsapp_bot/voice.py - Voice pipeline, Python 3.13 safe, no pydub."""
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

_BOT_DIR = Path(__file__).resolve().parent


def _find_ffmpeg():
    for c in _BOT_DIR.rglob("ffmpeg.exe"):
        return str(c)
    return None


_FFMPEG_PATH = _find_ffmpeg()
if _FFMPEG_PATH:
    print(f"[voice] ffmpeg: {_FFMPEG_PATH}", flush=True)
else:
    print("[voice] ffmpeg not found!", flush=True)


def _ffmpeg(*args: str) -> None:
    cmd = [_FFMPEG_PATH or "ffmpeg", "-y", *args]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[-400:])


_whisper_model: Any = None
_whisper_model_size: str = os.environ.get("WHISPER_MODEL", "base")


def _get_whisper() -> Any:
    global _whisper_model
    if _whisper_model is None:
        import whisper  # type: ignore
        print(f"[voice] Loading Whisper {_whisper_model_size}...", flush=True)
        _whisper_model = whisper.load_model(_whisper_model_size)
        print("[voice] Whisper ready.", flush=True)
    return _whisper_model


_AUDIO_TMP = Path(tempfile.gettempdir()) / "krushi_mitra_audio"
_AUDIO_TMP.mkdir(parents=True, exist_ok=True)


def _ogg_to_wav(ogg_path: Path) -> Path:
    wav = ogg_path.with_suffix(".wav")
    _ffmpeg("-i", str(ogg_path), "-ar", "16000", "-ac", "1", str(wav))
    return wav


def _mp3_to_ogg(mp3_path: Path) -> Path:
    ogg = mp3_path.with_suffix(".ogg")
    _ffmpeg("-i", str(mp3_path), "-c:a", "libopus", str(ogg))
    return ogg


_GTTS_LANG = {"en": "en", "hi": "hi", "mr": "mr"}
_WSPR_LANG = {"en": "en", "hi": "hi", "mr": "mr"}


def transcribe(ogg_path: Path, lang: str = "hi") -> str:
    wav = _ogg_to_wav(ogg_path)
    try:
        result = _get_whisper().transcribe(
            str(wav),
            language=_WSPR_LANG.get(lang, "hi"),
            fp16=False,
            task="transcribe",
        )
        return result.get("text", "").strip()
    finally:
        wav.unlink(missing_ok=True)


def synthesize(text: str, lang: str = "hi") -> Path:
    from gtts import gTTS  # type: ignore
    uid = uuid.uuid4().hex[:8]
    mp3 = _AUDIO_TMP / f"reply_{uid}.mp3"
    gTTS(text=text, lang=_GTTS_LANG.get(lang, "hi"), slow=False).save(str(mp3))
    ogg = _mp3_to_ogg(mp3)
    mp3.unlink(missing_ok=True)
    return ogg


def cleanup(path: Path) -> None:
    path.unlink(missing_ok=True)

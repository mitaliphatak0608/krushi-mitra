"""
backend/stt_tts.py
==================
Server-side Speech-to-Text and Text-to-Speech using OpenAI models.

STT model: configurable via ``OPENAI_STT_MODEL`` (default gpt-4o-mini-transcribe)
TTS model: configurable via ``OPENAI_TTS_MODEL`` (default gpt-4o-mini-tts)

These are backend primitives only — frontend voice UI wiring happens in Phase 3.
"""

import io
import os
import logging
from typing import Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

class ConfigurationError(RuntimeError):
    pass

class ExternalAPIError(Exception):
    pass

# ── Constants ─────────────────────────────────────────────────────────────

ALLOWED_AUDIO_CONTENT_TYPES = frozenset({
    "audio/webm", "audio/ogg", "audio/wav", "audio/wave",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a",
    "audio/flac", "audio/x-wav", "audio/x-m4a",
})

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB — OpenAI hard limit

# Per-language TTS voice defaults.  These are OpenAI voice names.
# The user can override via the ``voice`` API parameter.
DEFAULT_VOICES = {
    "en": "nova",
    "hi": "shimmer",
    "mr": "shimmer",
}


# ── Client helper ─────────────────────────────────────────────────────────

def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your-"):
        raise ConfigurationError(
            "OPENAI_API_KEY is not configured. "
            "Set it in backend/.env (see .env.example)."
        )
    return OpenAI(api_key=api_key)


# ── Speech-to-Text ────────────────────────────────────────────────────────

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Transcribe audio bytes to text.

    Parameters
    ----------
    audio_bytes : raw audio file bytes
    filename    : original filename (extension helps the API pick a codec)
    language    : optional ISO-639-1 hint (``"en"``, ``"hi"``, ``"mr"``)

    Returns
    -------
    (transcribed_text, detected_language_code)

    Raises
    ------
    ValueError  if audio is empty or too large
    RuntimeError if the API key is missing
    """
    if not audio_bytes:
        raise ValueError("Empty audio data received.")
    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise ValueError(
            f"Audio file exceeds {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} MB limit."
        )

    client = _get_client()
    model = os.environ.get("OPENAI_STT_MODEL", "whisper-1")

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename or "audio.webm"

    # Build kwargs — only pass language if provided
    create_kwargs: dict = {"model": model, "file": audio_file}
    if language:
        create_kwargs["language"] = language

    try:
        transcription = client.audio.transcriptions.create(**create_kwargs)
    except Exception as exc:
        logger.exception("STT transcription failed: %s", exc)
        raise ExternalAPIError(f"Transcription failed: {exc}") from exc

    text = (transcription.text or "").strip()
    detected_lang = _detect_script_language(text)

    return text, detected_lang


# ── Text-to-Speech ────────────────────────────────────────────────────────

def synthesize_speech(
    text: str,
    language: str = "en",
    voice: Optional[str] = None,
    response_format: str = "mp3",
) -> bytes:
    """
    Convert text to speech audio bytes.

    Parameters
    ----------
    text            : the text to speak
    language        : ``"en"`` / ``"hi"`` / ``"mr"`` — selects default voice
    voice           : explicit OpenAI voice name (overrides language default)
    response_format : ``"mp3"`` | ``"opus"`` | ``"aac"`` | ``"flac"`` | ``"wav"``

    Returns
    -------
    Raw audio bytes in the requested format.
    """
    if not text or not text.strip():
        raise ValueError("Empty text provided for speech synthesis.")

    if language == "mr":
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="mr", slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            return fp.getvalue()
        except Exception as exc:
            logger.exception("gTTS synthesis failed for Marathi: %s", exc)
            raise ExternalAPIError(f"Marathi Speech synthesis failed: {exc}") from exc

    client = _get_client()
    model = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
    selected_voice = voice or DEFAULT_VOICES.get(language, "nova")

    try:
        response = client.audio.speech.create(
            model=model,
            voice=selected_voice,
            input=text,
            response_format=response_format,
        )
    except Exception as exc:
        logger.exception("TTS synthesis failed: %s", exc)
        raise ExternalAPIError(f"Speech synthesis failed: {exc}") from exc

    # The SDK returns an HttpxBinaryResponseContent — .content gives bytes
    audio_data: bytes = response.content  # type: ignore[assignment]
    return audio_data


# ── Helpers ────────────────────────────────────────────────────────────────

def _detect_script_language(text: str) -> str:
    """
    Heuristic language detection based on Unicode script.

    Returns ``"en"``, ``"hi"``, or ``"mr"``.
    """
    if not text:
        return "en"

    devanagari_count = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    total_alpha = sum(1 for c in text if c.isalpha())

    if total_alpha == 0:
        return "en"

    if devanagari_count / total_alpha > 0.3:
        # Devanagari — try to distinguish Marathi from Hindi
        marathi_markers = [
            "आहे", "आहेत", "नाही", "करा", "साठी", "मध्ये",
            "काय", "कसे", "पात्र", "योजना", "शेत",
        ]
        if any(m in text for m in marathi_markers):
            return "mr"
        return "hi"

    return "en"

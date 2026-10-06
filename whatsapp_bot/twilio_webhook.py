"""
whatsapp_bot/twilio_webhook.py
================================
FastAPI router for Twilio WhatsApp Sandbox webhook.

Twilio sends POST requests with form-encoded data (NOT JSON like Meta).

Fields received:
  From        — sender's WhatsApp number e.g. whatsapp:+919876543210
  Body        — text message body
  MediaUrl0   — URL of first media file (voice note OGG/MP4)
  MediaContentType0 — MIME type of media
  NumMedia    — number of media files attached

Response must be TwiML XML (or empty 200 OK to suppress auto-reply).
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Response
from fastapi.responses import PlainTextResponse

from . import bot_logic, sessions
from . import twilio_client as wa
from . import voice as voice_pipeline

router = APIRouter()

_INCOMING_TMP = Path(tempfile.gettempdir()) / "krushi_mitra_incoming"
_INCOMING_TMP.mkdir(parents=True, exist_ok=True)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")


def _twiml(msg: str) -> Response:
    """Return a TwiML Message response."""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{msg}</Message>
</Response>"""
    return Response(content=xml, media_type="application/xml")


def _empty() -> Response:
    """Return empty 200 — we send replies via API, not TwiML."""
    return Response(content="", status_code=200)


@router.post("/twilio/webhook")
async def twilio_receive(
    From: Annotated[str, Form()] = "",
    Body: Annotated[str, Form()] = "",
    NumMedia: Annotated[str, Form()] = "0",
    MediaUrl0: Annotated[str, Form()] = "",
    MediaContentType0: Annotated[str, Form()] = "",
) -> Response:
    """
    Handle incoming WhatsApp messages from Twilio sandbox.
    Supports text messages and voice notes.
    """
    # wa_number: strip 'whatsapp:' prefix for internal use
    wa_number = From.replace("whatsapp:", "").strip()
    if not wa_number:
        return _empty()

    num_media = int(NumMedia or "0")

    # ── Voice / Audio message ────────────────────────────────────────────
    if num_media > 0 and MediaUrl0 and "audio" in MediaContentType0:
        uid = uuid.uuid4().hex[:8]
        ogg_path = _INCOMING_TMP / f"voice_{uid}.ogg"
        try:
            wa.download_media(MediaUrl0, ogg_path)
            reply_text, should_voice = bot_logic.handle_voice_message(wa_number, ogg_path)

            session = sessions.get(wa_number)
            lang = session["lang"]

            # Send text reply
            wa.send_text(From, reply_text)

            # Send voice reply if enabled (Twilio sandbox: text only for now)
            if should_voice:
                audio_out = None
                try:
                    audio_out = voice_pipeline.synthesize(reply_text, lang=lang)
                    wa.send_audio_file(From, audio_out)
                except Exception as ve:
                    print(f"[twilio_webhook] Voice reply error: {ve}", flush=True)
                finally:
                    if audio_out:
                        voice_pipeline.cleanup(audio_out)

        except Exception as exc:
            print(f"[twilio_webhook] Voice error: {exc}", flush=True)
            wa.send_text(From, "Voice message error. Please type your question.")
        finally:
            ogg_path.unlink(missing_ok=True)

        return _empty()

    # ── Text message ────────────────────────────────────────────────────
    if Body.strip():
        reply_text, _ = bot_logic.handle_message(wa_number, Body.strip())
        wa.send_text(From, reply_text)

    return _empty()

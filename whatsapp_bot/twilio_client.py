"""
whatsapp_bot/twilio_client.py
==============================
Twilio WhatsApp Sandbox client.

Replaces wa_client.py when using Twilio instead of Meta API.

Env vars needed:
  TWILIO_ACCOUNT_SID  — from Twilio Console
  TWILIO_AUTH_TOKEN   — from Twilio Console
  TWILIO_WA_NUMBER    — sandbox number e.g. whatsapp:+14155238886
"""

import os
from pathlib import Path
from typing import Any

ACCOUNT_SID   = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN    = os.environ.get("TWILIO_AUTH_TOKEN", "")
FROM_NUMBER   = os.environ.get("TWILIO_WA_NUMBER", "whatsapp:+14155238886")


def _client():
    from twilio.rest import Client  # type: ignore
    return Client(ACCOUNT_SID, AUTH_TOKEN)


def send_text(to: str, body: str) -> Any:
    """Send a plain text WhatsApp message via Twilio sandbox."""
    # Ensure E.164 format with whatsapp: prefix
    to_wa = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    msg = _client().messages.create(
        from_=FROM_NUMBER,
        to=to_wa,
        body=body,
    )
    return {"sid": msg.sid, "status": msg.status}


def send_audio_file(to: str, file_path: Path) -> Any:
    """
    Send a voice note via Twilio.
    Twilio requires a publicly accessible URL for media — for sandbox testing,
    we skip audio send and just send text (voice reply shown as text).
    In production, upload to a CDN or use ngrok URL.
    """
    # For sandbox: just skip audio (text reply already sent)
    print(f"[twilio] Audio send skipped in sandbox mode (file: {file_path.name})", flush=True)
    return {"status": "skipped_sandbox"}


def download_media(media_url: str, dest: Path) -> Path:
    """Download an incoming media file (voice note) from Twilio."""
    import httpx
    from requests.auth import HTTPBasicAuth
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(
            media_url,
            auth=(ACCOUNT_SID, AUTH_TOKEN),
        )
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest

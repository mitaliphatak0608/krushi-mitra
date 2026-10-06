"""
whatsapp_bot/wa_client.py
=========================
Meta WhatsApp Cloud API client.

Provides helpers to:
  - Send plain text messages
  - Send interactive button messages (up to 3 buttons)
  - Send audio messages (voice replies)
  - Upload media and get a media_id for audio sending
"""

import os
from pathlib import Path
from typing import Any

import httpx

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _token() -> str:
    return os.environ.get("WHATSAPP_TOKEN", "")


def _phone_id() -> str:
    return os.environ.get("PHONE_NUMBER_ID", "")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Send text message
# ---------------------------------------------------------------------------
def send_text(to: str, body: str) -> dict[str, Any]:
    """Send a plain text message to a WhatsApp number."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_BASE}/{_phone_id()}/messages",
            headers=_headers(),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Send interactive button message
# ---------------------------------------------------------------------------
def send_buttons(
    to: str,
    body: str,
    buttons: list[dict[str, str]],  # [{"id": "...", "title": "..."}]
    header: str | None = None,
    footer: str | None = None,
) -> dict[str, Any]:
    """
    Send an interactive reply-button message (max 3 buttons).
    Each button: {"id": "unique_id", "title": "Button Label"}
    """
    btn_objects = [
        {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
        for b in buttons[:3]
    ]
    interactive: dict[str, Any] = {
        "type": "button",
        "body": {"text": body},
        "action": {"buttons": btn_objects},
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_BASE}/{_phone_id()}/messages",
            headers=_headers(),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Upload media and send audio
# ---------------------------------------------------------------------------
def upload_audio(file_path: Path) -> str:
    """
    Upload an OGG/Opus audio file to the Meta media endpoint.
    Returns the media_id string.
    """
    url = f"{GRAPH_BASE}/{_phone_id()}/media"
    headers = {"Authorization": f"Bearer {_token()}"}
    with file_path.open("rb") as f:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                url,
                headers=headers,
                data={"messaging_product": "whatsapp"},
                files={"file": (file_path.name, f, "audio/ogg; codecs=opus")},
            )
    resp.raise_for_status()
    return resp.json()["id"]


def send_audio_by_id(to: str, media_id: str) -> dict[str, Any]:
    """Send an already-uploaded audio file by its media_id."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "audio",
        "audio": {"id": media_id},
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_BASE}/{_phone_id()}/messages",
            headers=_headers(),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()


def send_audio_file(to: str, file_path: Path) -> dict[str, Any]:
    """Upload audio file and send it as a voice message in one step."""
    media_id = upload_audio(file_path)
    return send_audio_by_id(to, media_id)


# ---------------------------------------------------------------------------
# Download media (for incoming voice notes)
# ---------------------------------------------------------------------------
def get_media_url(media_id: str) -> str:
    """Resolve a media_id to its temporary download URL."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            f"{GRAPH_BASE}/{media_id}",
            headers={"Authorization": f"Bearer {_token()}"},
        )
    resp.raise_for_status()
    return resp.json()["url"]


def download_media(media_id: str, dest: Path) -> Path:
    """
    Download a WhatsApp media file (voice note / audio) to *dest*.
    Returns the path to the downloaded file.
    """
    url = get_media_url(media_id)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(url, headers={"Authorization": f"Bearer {_token()}"})
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest

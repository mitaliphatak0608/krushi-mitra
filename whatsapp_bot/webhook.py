"""whatsapp_bot/webhook.py — Meta WhatsApp Cloud API webhook."""
import os, tempfile, uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from . import bot_logic, sessions, wa_client
from . import voice as voice_pipeline

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN","krushi-mitra-verify")
router = APIRouter()
_TMP = Path(tempfile.gettempdir()) / "krushi_mitra_incoming"
_TMP.mkdir(parents=True, exist_ok=True)

@router.get("/webhook", response_class=PlainTextResponse)
def verify(hub_mode=Query(None,alias="hub.mode"), hub_challenge=Query(None,alias="hub.challenge"), hub_verify_token=Query(None,alias="hub.verify_token")):
    if hub_mode=="subscribe" and hub_verify_token==VERIFY_TOKEN: return hub_challenge or ""
    raise HTTPException(403,"Verification failed")

@router.post("/webhook")
async def receive(request: Request):
    body: dict[str,Any] = await request.json()
    try: msgs = body["entry"][0]["changes"][0]["value"].get("messages",[])
    except (KeyError,IndexError): return {"status":"no_message"}
    for msg in msgs:
        num = msg["from"]; typ = msg.get("type","")
        if typ=="text":
            reply,_ = bot_logic.handle_message(num,msg["text"]["body"])
            wa_client.send_text(num,reply)
        elif typ=="audio":
            ogg = _TMP / f"v_{uuid.uuid4().hex[:8]}.ogg"
            try:
                wa_client.download_media(msg["audio"]["id"],ogg)
                reply,sv = bot_logic.handle_voice_message(num,ogg)
                wa_client.send_text(num,reply)
                if sv:
                    s = sessions.get(num)
                    a = voice_pipeline.synthesize(reply,lang=s["lang"])
                    try: wa_client.send_audio_file(num,a)
                    finally: voice_pipeline.cleanup(a)
            except Exception as e: wa_client.send_text(num,"Voice error. Please type.")
            finally: ogg.unlink(missing_ok=True)
        elif typ=="interactive":
            rid = msg.get("interactive",{}).get("button_reply",{}).get("id","")
            reply,_ = bot_logic.handle_message(num,rid)
            wa_client.send_text(num,reply)
    return {"status":"ok"}

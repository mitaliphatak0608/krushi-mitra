"""whatsapp_bot/broadcast.py — Admin broadcast endpoint."""
import os
from typing import Any
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from . import wa_client

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BROADCAST_SECRET = os.environ.get("BROADCAST_SECRET", "")
router = APIRouter()

class BroadcastRequest(BaseModel):
    numbers: list[str]; lang: str = "mr"; secret: str; profile: dict[str, Any] = {}

@router.post("/admin/broadcast")
def broadcast_notifications(body: BroadcastRequest) -> dict[str, Any]:
    if not BROADCAST_SECRET: raise HTTPException(503, "BROADCAST_SECRET not set.")
    if body.secret != BROADCAST_SECRET: raise HTTPException(403, "Wrong secret.")
    if not body.numbers: raise HTTPException(422, "No numbers.")
    lang = body.lang if body.lang in ("en","hi","mr") else "mr"
    try:
        with httpx.Client(timeout=15) as c:
            notifs = c.post(f"{BACKEND_URL}/notifications", json={"lang":lang,"profile":body.profile}).json()
    except Exception as e: raise HTTPException(502, str(e))
    if not notifs: return {"status":"no_notifications","sent":0,"failed":0}
    sent=failed=0; errors=[]
    for num in body.numbers:
        try:
            for n in notifs:
                t = n.get("title",{}).get(lang) or n.get("title",{}).get("en","")
                b = n.get("body",{}).get(lang) or n.get("body",{}).get("en","")
                wa_client.send_text(num, f"{t}\n{b}")
            sent += 1
        except Exception as e: failed += 1; errors.append(str(e))
    return {"status":"done","sent":sent,"failed":failed,"errors":errors[:5]}

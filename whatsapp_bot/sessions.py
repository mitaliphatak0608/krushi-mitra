"""whatsapp_bot/sessions.py — In-memory session store."""
import time
from typing import Any

STATE_IDLE    = "idle"
STATE_PROFILE = "profile_qa"
IDLE_MINUTES  = 30
_sessions: dict[str, dict[str, Any]] = {}

def _now() -> float: return time.time()

def get(wa_number: str) -> dict[str, Any]:
    s = _sessions.get(wa_number)
    if s and (_now() - s["last_seen"]) < IDLE_MINUTES * 60:
        s["last_seen"] = _now(); return s
    s = {"lang": "hi", "profile": {}, "state": STATE_IDLE, "step": 0, "voice_mode": False, "last_seen": _now()}
    _sessions[wa_number] = s; return s

def save(wa_number: str, session: dict[str, Any]) -> None:
    session["last_seen"] = _now(); _sessions[wa_number] = session

def reset(wa_number: str) -> None: _sessions.pop(wa_number, None)

def purge_expired() -> int:
    cutoff = _now() - IDLE_MINUTES * 60
    expired = [k for k, v in _sessions.items() if v["last_seen"] < cutoff]
    for k in expired: del _sessions[k]
    return len(expired)

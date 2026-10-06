"""
krushi_bot_server.py
====================
Standalone WhatsApp bot server — all logic in one file.
Replies to Twilio WhatsApp sandbox messages via TwiML.

Run:  python krushi_bot_server.py
"""

import os
import sys
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load .env from whatsapp_bot folder
load_dotenv(Path(__file__).parent / "whatsapp_bot" / ".env")

from fastapi import FastAPI, Form, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from typing import Annotated, Any
import uvicorn

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# ── Session store ─────────────────────────────────────────────────────────
_sessions: dict[str, dict] = {}

def _get_session(number: str) -> dict:
    s = _sessions.get(number)
    now = time.time()
    if s and (now - s["ts"]) < 1800:
        s["ts"] = now
        return s
    s = {"lang": "hi", "profile": {}, "state": "idle", "step": 0, "ts": now}
    _sessions[number] = s
    return s

def _save(number: str, s: dict):
    s["ts"] = time.time()
    _sessions[number] = s

# ── Profile Q&A steps ─────────────────────────────────────────────────────
STEPS = [
    ("name",              {"en":"1. Your name?", "hi":"1. आपका नाम?", "mr":"1. तुमचे नाव?"}),
    ("landholding",       {"en":"2. Land in hectares? (e.g. 1.5)", "hi":"2. जमीन हेक्टेयर में? (जैसे 1.5)", "mr":"2. जमीन हेक्टर मध्ये? (उदा. 1.5)"}),
    ("category",          {"en":"3. Category? General/OBC/SC/ST", "hi":"3. श्रेणी? General/OBC/SC/ST", "mr":"3. प्रवर्ग? General/OBC/SC/ST"}),
    ("region",            {"en":"4. Region? (Marathwada/Vidarbha/Western Maharashtra)", "hi":"4. क्षेत्र?", "mr":"4. विभाग?"}),
    ("cropSeason",        {"en":"5. Season? Kharif/Rabi/Annual Commercial", "hi":"5. मौसम? Kharif/Rabi/Annual Commercial", "mr":"5. हंगाम? Kharif/Rabi/Annual Commercial"}),
    ("primaryCrop",       {"en":"6. Primary crop? (Cotton/Soybean/Wheat)", "hi":"6. मुख्य फसल?", "mr":"6. मुख्य पीक?"}),
    ("annualIncome",      {"en":"7. Annual income in Rs?", "hi":"7. वार्षिक आय रु में?", "mr":"7. वार्षिक उत्पन्न रु मध्ये?"}),
    ("isTaxPayer",        {"en":"8. Income tax payer? Yes/No", "hi":"8. आयकर दाता? Yes/No", "mr":"8. आयकर भरता? Yes/No"}),
    ("hasOutstandingLoan",{"en":"9. Outstanding crop loan? Yes/No", "hi":"9. फसल ऋण बकाया? Yes/No", "mr":"9. पीक कर्ज थकबाकी? Yes/No"}),
    ("isOrganic",         {"en":"10. Organic farming? Yes/No", "hi":"10. जैविक खेती? Yes/No", "mr":"10. सेंद्रिय शेती? Yes/No"}),
]

MENU = {
    "en": "Krushi Mitra Menu:\n- Ask any scheme question\n- Type *profile* - setup farm profile\n- Type *schemes* - eligible schemes\n- Type *reset* - start over\n- Language: type Hindi / Marathi / English",
    "hi": "कृषी मित्र मेनू:\n- कोई भी योजना सवाल पूछें\n- *profile* टाइप करें\n- *schemes* टाइप करें\n- *reset* टाइप करें\n- भाषा: Hindi / Marathi / English",
    "mr": "कृषी मित्र मेनू:\n- कोणताही योजना प्रश्न विचारा\n- *profile* टाइप करा\n- *schemes* टाइप करा\n- *reset* टाइप करा\n- भाषा: Hindi / Marathi / English",
}

def _lang(t: str):
    l = t.strip().lower()
    if l in ("english","en","in english"): return "en"
    if l in ("hindi","हिंदी","in hindi"): return "hi"
    if l in ("marathi","मराठी","in marathi"): return "mr"
    return None

def _bool(t: str) -> str:
    return "Yes" if t.strip().lower() in ("yes","y","हो","हाँ","होय","1") else "No"

def _p(idx, lang): return STEPS[idx][1].get(lang, STEPS[idx][1]["en"])

def _chat_api(q, lang, profile):
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{BACKEND_URL}/chat", json={"query": q, "lang": lang, "profile": profile})
    r.raise_for_status()
    return r.json()

def _fmt(resp, lang):
    if not resp.get("found"):
        return {"en":"No info found. Type menu.","hi":"जानकारी नहीं मिली।","mr":"माहिती मिळाली नाही."}[lang]
    return resp.get("message","") or ""

def handle(number: str, text: str) -> str:
    s = _get_session(number)
    lang = s["lang"]
    t = text.strip()
    lo = t.lower()

    # Language switch
    nl = _lang(t)
    if nl:
        s["lang"] = nl
        _save(number, s)
        return {"en":"Language set to English.","hi":"भाषा हिंदी में बदली।","mr":"भाषा मराठी मध्ये बदलली."}[nl]

    # Reset
    if lo in ("reset","रीसेट","start over"):
        _sessions.pop(number, None)
        return {"en":"Session reset!","hi":"सत्र रीसेट!","mr":"सत्र रीसेट!"}[lang]

    # Menu
    if lo in ("menu","help","मेनू","मदद"):
        _save(number, s)
        return MENU[lang]

    # Start profile
    if lo in ("profile","my profile","प्रोफ़ाइल","प्रोफाइल"):
        s["state"] = "profile"; s["step"] = 0
        _save(number, s)
        intro = {"en":"Setting up profile:\n\n","hi":"प्रोफ़ाइल बना रहे हैं:\n\n","mr":"प्रोफाइल तयार करत आहोत:\n\n"}[lang]
        return intro + _p(0, lang)

    # Profile Q&A
    if s["state"] == "profile":
        idx = s["step"]
        key, _ = STEPS[idx]
        float_keys = {"landholding","annualIncome"}
        bool_keys  = {"isTaxPayer","hasOutstandingLoan","isOrganic"}
        if key in float_keys:
            try: s["profile"][key] = float(t.replace(",",""))
            except:
                _save(number, s)
                return "Please enter a number.\n" + _p(idx, lang)
        elif key in bool_keys:
            s["profile"][key] = _bool(t)
        else:
            s["profile"][key] = t
        nxt = idx + 1
        if nxt < len(STEPS):
            s["step"] = nxt; _save(number, s)
            return _p(nxt, lang)
        else:
            s["state"] = "idle"; s["step"] = 0
            try:
                with httpx.Client(timeout=20) as c:
                    res = c.post(f"{BACKEND_URL}/eligibility", json={"profile": s["profile"],"lang": lang}).json()
                ec = sum(1 for r in res if r.get("eligible")); tot = len(res)
            except: ec = tot = 0
            _save(number, s)
            name = s["profile"].get("name","Farmer")
            return {"en":f"Profile saved! {ec}/{tot} schemes eligible. Type *schemes*.","hi":f"प्रोफ़ाइल सेव! {ec}/{tot} योजनाएं पात्र। *schemes* टाइप करें।","mr":f"प्रोफाइल सेव! {ec}/{tot} योजना पात्र. *schemes* टाइप करा."}[lang]

    # Schemes shortcut
    if lo in ("schemes","all schemes"):
        try:
            q = {"en":"all schemes","hi":"सभी योजनाएं","mr":"सर्व योजना"}[lang]
            reply = _fmt(_chat_api(q, lang, s["profile"]), lang)
        except Exception as e: reply = f"Service error. Try again."
        _save(number, s); return reply

    # General chat
    try:
        reply = _fmt(_chat_api(t, lang, s["profile"]), lang)
    except Exception:
        reply = {"en":"Service unavailable.","hi":"सेवा उपलब्ध नहीं।","mr":"सेवा उपलब्ध नाही."}[lang]
    _save(number, s)
    return reply


# ── FastAPI app ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[bot] Krushi Mitra standalone server ready on port 8001", flush=True)
    print("[bot] Twilio webhook -> POST /twilio/webhook", flush=True)
    yield

app = FastAPI(title="Krushi Mitra Bot", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def twiml(msg: str) -> Response:
    safe = msg.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe}</Message></Response>'
    return Response(content=xml, media_type="application/xml")


@app.post("/twilio/webhook")
async def webhook(
    From: Annotated[str, Form()] = "",
    Body: Annotated[str, Form()] = "",
    NumMedia: Annotated[str, Form()] = "0",
) -> Response:
    number = From.replace("whatsapp:", "").strip()
    print(f"[bot] From={From!r} Body={Body[:60]!r}", flush=True)
    if not number or not Body.strip():
        return Response(content='<?xml version="1.0"?><Response></Response>', media_type="application/xml")
    try:
        reply = handle(number, Body.strip())
    except Exception as e:
        print(f"[bot] Error: {e}", flush=True)
        reply = "Sorry, something went wrong. Please try again."
    print(f"[bot] Reply: {reply[:80]!r}", flush=True)
    return twiml(reply)


@app.get("/health")
def health():
    return {"status": "ok", "service": "krushi-mitra-bot-standalone"}


@app.get("/")
def root():
    return {"message": "Krushi Mitra WhatsApp Bot running. POST /twilio/webhook for messages."}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

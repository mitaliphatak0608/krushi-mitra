"""
krushi_voice_bot.py
===================
Standalone WhatsApp Voice & Multilingual Bot for Krushi Mitra.
Supports:
  1. High-accuracy multilingual recognition for Marathi (default), Hindi, and English.
  2. Sub-second to fast voice note processing (Whisper tiny with domain prompt & normalization).
  3. Full spoken audio replies (explains scheme name, financial benefit, and criteria in natural Marathi/Hindi/English).
  4. Instant scheme matching for PM-KISAN, Namo Shetkari, PMFBY, KCC, Solar Pump, etc.
"""

import os
import sys
import time
import uuid
import re
import unicodedata
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Ensure ffmpeg bin is in system PATH for Whisper & audio conversion
ROOT_DIR = Path(__file__).parent.resolve()
FFMPEG_BIN = ROOT_DIR / "whatsapp_bot" / "ffmpeg-9.0.2-essentials_build" / "bin"
if FFMPEG_BIN.exists():
    os.environ["PATH"] = str(FFMPEG_BIN) + os.pathsep + os.environ.get("PATH", "")

load_dotenv(ROOT_DIR / "whatsapp_bot" / ".env")

import httpx
from fastapi import FastAPI, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from typing import Annotated
import uvicorn

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")

AUDIO_CACHE = ROOT_DIR / "whatsapp_audio_cache"
AUDIO_CACHE.mkdir(parents=True, exist_ok=True)

WHISPER_PROMPT = (
    "शेतकरी, कृषी मित्र, पीएम किसान योजना, नमो शेतकरी महासन्मान निधी, "
    "पीक विमा, कुसुम सौर पंप, ठिबक सिंचन, विहीर अनुदान, कर्जमाफी, "
    "सर्व योजना, पात्रता, माहिती, सांगा, काय आहे, मला माहिती हवी आहे"
)

# ── Whisper Loader ────────────────────────────────────────────────────────
_whisper_model = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print("[voice] Loading Whisper model (tiny)...", flush=True)
        _whisper_model = whisper.load_model("tiny")
        print("[voice] Whisper ready.", flush=True)
    return _whisper_model

# ── Session Store ─────────────────────────────────────────────────────────
_sessions: dict[str, dict] = {}

def get_session(number: str) -> dict:
    now = time.time()
    s = _sessions.get(number)
    if s and (now - s["ts"]) < 1800:
        s["ts"] = now
        return s
    s = {"lang": "mr", "profile": {}, "state": "idle", "step": 0, "ts": now}
    _sessions[number] = s
    return s

def save_session(number: str, s: dict):
    s["ts"] = time.time()
    _sessions[number] = s

# ── Profile Questions (en, hi, mr) ────────────────────────────────────────
STEPS = [
    ("name", {
        "en": "1. What is your name?",
        "hi": "1. आपका नाम क्या है?",
        "mr": "1. तुमचे नाव काय आहे?"
    }),
    ("landholding", {
        "en": "2. How many hectares of land do you own? (e.g. 1.5)",
        "hi": "2. आपके पास कितने हेक्टेयर जमीन है? (जैसे 1.5)",
        "mr": "2. तुमच्याकडे किती हेक्टर जमीन आहे? (उदा. 1.5)"
    }),
    ("category", {
        "en": "3. Social category? General / OBC / SC / ST",
        "hi": "3. सामाजिक श्रेणी? General / OBC / SC / ST",
        "mr": "3. सामाजिक प्रवर्ग? General / OBC / SC / ST"
    }),
    ("region", {
        "en": "4. Farming region? (Marathwada/Vidarbha/Western Maharashtra)",
        "hi": "4. कृषि क्षेत्र? (Marathwada/Vidarbha/Western Maharashtra)",
        "mr": "4. कृषी विभाग? (Marathwada/Vidarbha/Western Maharashtra)"
    }),
    ("cropSeason", {
        "en": "5. Crop season? Kharif / Rabi / Annual Commercial",
        "hi": "5. फसल मौसम? Kharif / Rabi / Annual Commercial",
        "mr": "5. हंगाम? Kharif / Rabi / Annual Commercial"
    }),
    ("primaryCrop", {
        "en": "6. Primary crop? (Cotton, Soybean, Wheat)",
        "hi": "6. मुख्य फसल? (कपास, सोयाबीन, गेहूं)",
        "mr": "6. मुख्य पीक? (कापूस, सोयाबीन, गहू)"
    }),
    ("annualIncome", {
        "en": "7. Annual household income in Rs? (e.g. 120000)",
        "hi": "7. वार्षिक आय रु में? (जैसे 120000)",
        "mr": "7. वार्षिक कौटुंबिक उत्पन्न रु मध्ये? (उदा. 120000)"
    }),
    ("isTaxPayer", {
        "en": "8. Are you an income tax payer? Yes / No",
        "hi": "8. क्या आप आयकर दाता हैं? Yes / No",
        "mr": "8. तुम्ही आयकर भरता का? Yes / No"
    }),
    ("hasOutstandingLoan", {
        "en": "9. Do you have an outstanding crop loan? Yes / No",
        "hi": "9. क्या फसल ऋण बकाया है? Yes / No",
        "mr": "9. तुमचे पीक कर्ज थकबाकी आहे का? Yes / No"
    }),
    ("isOrganic", {
        "en": "10. Certified organic farming? Yes / No",
        "hi": "10. प्रमाणित जैविक खेती? Yes / No",
        "mr": "10. प्रमाणित सेंद्रिय शेती? Yes / No"
    }),
]

MENU = {
    "en": (
        "🌾 *Krushi Mitra — Menu*\n\n"
        "• Ask any scheme question (Type or send 🎤 Voice Note)\n"
        "• Type *profile* — set up your farm profile\n"
        "• Type *schemes* — see eligible schemes\n"
        "• Type *reset* — start fresh\n"
        "• Change language: type *Hindi* | *Marathi* | *English*\n\n"
        "📞 Kisan Call Centre: 1800-120-8040 (toll-free)"
    ),
    "hi": (
        "🌾 *कृषी मित्र — मेनू*\n\n"
        "• कोई भी योजना सवाल पूछें (टेक्स्ट या 🎤 वॉइस नोट भेजें)\n"
        "• *profile* टाइप करें — खेत की जानकारी भरें\n"
        "• *schemes* टाइप करें — पात्र योजनाएं देखें\n"
        "• *reset* टाइप करें — नए सिरे से शुरू करें\n"
        "• भाषा बदलें: *Hindi* | *Marathi* | *English*\n\n"
        "📞 किसान कॉल सेंटर: 1800-120-8040 (टोल-फ्री)"
    ),
    "mr": (
        "🌾 *कृषी मित्र — मेनू*\n\n"
        "• कोणताही योजना प्रश्न विचारा (मजकूर किंवा 🎤 व्हॉइस मेसेज पाठवा)\n"
        "• *profile* टाइप करा — शेत माहिती नोंदवा\n"
        "• *schemes* टाइप करा — पात्र योजना पहा\n"
        "• *reset* टाइप करा — पुन्हा सुरू करा\n"
        "• भाषा बदला: *Hindi* | *Marathi* | *English*\n\n"
        "📞 किसान कॉल सेंटर: 1800-120-8040 (टोल-फ्री)"
    ),
}

# ── Language Detection Indicators (Devanagari + Romanized) ────────────────
MARATHI_INDICATORS = {
    "आहे", "नाही", "काय", "कशी", "कसे", "सांगा", "सांग", "माहिती", "मिळेल", "मिळतील",
    "करावे", "करावी", "शेतकरी", "अनुदान", "अर्ज", "हंगाम", "पाहिजे", "होय", "मला", "बद्दल",
    "कोणती", "कोणत्या", "कोणते", "योजनेबद्दल", "लागू"
}
MARATHI_LATIN = {
    "mala", "mahala", "sanga", "sangha", "badal", "bhadal", "ahe", "nahi", "kay",
    "kashi", "kase", "sheti", "shetkari", "anudan", "yojnebadal", "milel", "pahije",
    "konti", "kontya", "konte"
}
HINDI_INDICATORS = {
    "है", "नहीं", "क्या", "कैसे", "बताओ", "बताइए", "जानकारी", "मिलेगा", "करना",
    "सब्सिडी", "आवेदन", "फसल", "चाहिए", "हाँ", "हां", "दीजिए", "मुझे", "सकते", "बारे में"
}
HINDI_LATIN = {
    "mujhe", "batao", "bataiye", "hai", "kya", "kaise", "chahiye", "milega", "kheti",
    "fasal", "karein", "bare me"
}
ENGLISH_WORDS = {
    "what", "how", "tell", "which", "scheme", "schemes", "eligibility", "eligible",
    "apply", "subsidy", "farmer", "details", "information", "about", "is", "the", "me"
}

def detect_language(t: str) -> str | None:
    """Accurately detect if the user's input is Marathi, Hindi, or English."""
    l = t.strip().lower()
    if l in ("english", "en", "in english"): return "en"
    if l in ("hindi", "हिंदी", "in hindi"): return "hi"
    if l in ("marathi", "मराठी", "in marathi"): return "mr"

    tokens = set(re.findall(r"\b\w+\b", l))
    mr_cnt = sum(1 for w in MARATHI_INDICATORS if w in t) + sum(1 for w in MARATHI_LATIN if w in tokens)
    hi_cnt = sum(1 for w in HINDI_INDICATORS if w in t) + sum(1 for w in HINDI_LATIN if w in tokens)
    en_cnt = sum(1 for w in ENGLISH_WORDS if w in tokens)

    if mr_cnt > hi_cnt and mr_cnt >= en_cnt and mr_cnt > 0: return "mr"
    if hi_cnt > mr_cnt and hi_cnt >= en_cnt and hi_cnt > 0: return "hi"
    if en_cnt > mr_cnt and en_cnt > hi_cnt: return "en"
    return None

def normalize_query(text: str) -> str:
    """Normalize speech recognition artifacts and phonetic variations for high accuracy matching."""
    # 1. Unicode NFKC normalization and nukta stripping
    t = unicodedata.normalize("NFKC", text.strip().replace("\u093c", ""))
    # 2. Collapse repetitive phrase loops from Whisper
    t = re.sub(r"([^\n,]+?)(?:,\s*\1){2,}", r"\1", t)
    # 3. Phonetic and dialectal mappings
    replacements = [
        # PM-KISAN phonetic speech patterns
        (r"\b(tm|pm)\s*ki\s*sahani\b", "pm kisan"),
        (r"\b(tm|pm)\s*kisani\b", "pm kisan"),
        (r"\b(tm|pm)\s*kisaan\b", "pm kisan"),
        (r"\b(tm|pm)\s*kissan\b", "pm kisan"),
        (r"\b(tm|pm)\s*kishan\b", "pm kisan"),
        (r"\b(tm|pm)\s*kisano\b", "pm kisan"),
        (r"\b(tm|pm)\s*kisan\b", "pm kisan"),
        (r"\bkisani\s+(ojna|yojna|yojana|ojira)\b", "pm kisan yojana"),
        (r"\bkisan\s+(ojna|ojira)\b", "kisan yojana"),
        (r"\b(ojna|ojira)\b", "yojana"),
        (r"\bmahala\b", "mala"),
        (r"\bbhadal\b", "badal"),
        (r"\bsangha\b", "sanga"),
        # Devanagari variations
        (r"पीम\s*किसान", "पीएम किसान"),
        (r"पीएम\s*किसानी", "पीएम किसान"),
        (r"पीम\s*किसानी", "पीएम किसान"),
        (r"पी\.?एम\.?\s*किसान", "पीएम किसान"),
        (r"योजरा", "योजना"),
        (r"पत्रता", "पात्रता"),
        (r"प़रा", ""),
    ]
    for pattern, rep in replacements:
        t = re.sub(pattern, rep, t, flags=re.IGNORECASE)
    return t.strip()

def parse_bool(t: str) -> str:
    return "Yes" if t.strip().lower() in ("yes", "y", "हो", "हाँ", "हां", "होय", "1", "true") else "No"

def get_prompt(idx: int, lang: str) -> str:
    return STEPS[idx][1].get(lang, STEPS[idx][1]["en"])

def call_chat(query: str, lang: str, profile: dict) -> dict:
    with httpx.Client(timeout=15) as client:
        r = client.post(f"{BACKEND_URL}/chat", json={"query": query, "lang": lang, "profile": profile})
    r.raise_for_status()
    return r.json()

def call_eligibility(lang: str, profile: dict) -> list:
    with httpx.Client(timeout=15) as client:
        r = client.post(f"{BACKEND_URL}/eligibility", json={"profile": profile, "lang": lang})
    r.raise_for_status()
    return r.json()

def format_chat_reply(resp: dict, lang: str) -> str:
    if not resp.get("found"):
        not_found = {
            "en": "Sorry, I could not find relevant scheme details. Try rephrasing or type *menu*.",
            "hi": "माफ़ करें, इस बारे में योजना जानकारी नहीं मिली। दोबारा पूछें या *menu* लिखें।",
            "mr": "माफ करा, याबद्दल योजना माहिती सापडली नाही. पुन्हा विचारा किंवा *menu* टाइप करा."
        }
        return not_found.get(lang, not_found["en"])

    msg = resp.get("message", "")
    schemes = resp.get("schemes") or []
    if schemes and resp.get("type") in ("all_schemes", "ineligible_reasons"):
        lines = [msg, ""]
        for s in schemes[:8]:
            icon = "✅" if s.get("eligible") else "❌"
            lines.append(f"{icon} *{s.get('name')}*")
            if s.get("note"):
                lines.append(f"   {s.get('note')}")
        return "\n".join(lines)
    return msg or ""

# ── Main Conversation Logic ───────────────────────────────────────────────
def handle_message(number: str, text: str) -> tuple[str, str]:
    """
    Handles a message from a user.
    Returns: (reply_text, reply_lang)
    """
    session = get_session(number)
    stripped = text.strip()
    norm = normalize_query(stripped)
    low = norm.lower()

    det = detect_language(norm)
    if det:
        session["lang"] = det

    lang = session.get("lang", "mr")

    if low in ("english", "en", "hindi", "हिंदी", "marathi", "मराठी"):
        ack = {
            "en": "✅ Language changed to *English*. How can I help you?",
            "hi": "✅ भाषा *हिंदी* में बदल दी गई है। पूछिए, मैं क्या मदद करूँ?",
            "mr": "✅ भाषा *मराठी* मध्ये बदलली आहे. विचारा, मी काय मदत करू?"
        }
        save_session(number, session)
        return ack[lang], lang

    if low in ("reset", "restart", "रीसेट", "पुन्हा सुरू"):
        _sessions.pop(number, None)
        msg = {
            "en": "🌱 Session reset! Type *menu* to see all options.",
            "hi": "🌱 सत्र रीसेट हो गया है! *menu* टाइप करें।",
            "mr": "🌱 सत्र रीसेट झाले आहे! *menu* टाइप करा."
        }
        return msg.get(lang, msg["en"]), lang

    if low in ("menu", "help", "मेनू", "मदत", "मदद"):
        save_session(number, session)
        return MENU.get(lang, MENU["en"]), lang

    if low in ("profile", "my profile", "प्रोफ़ाइल", "प्रोफाइल", "शेत माहिती"):
        session["state"] = "profile"
        session["step"] = 0
        save_session(number, session)
        intro = {
            "en": "📋 Let us set up your farm profile.\n\n",
            "hi": "📋 आइए आपकी किसान प्रोफ़ाइल बनाते हैं।\n\n",
            "mr": "📋 चला तुमची शेतकरी प्रोफाइल तयार करूया.\n\n"
        }
        return intro.get(lang, intro["en"]) + get_prompt(0, lang), lang

    if session.get("state") == "profile":
        idx = session["step"]
        key, _ = STEPS[idx]
        if key in ("landholding", "annualIncome"):
            try:
                session["profile"][key] = float(stripped.replace(",", ""))
            except ValueError:
                save_session(number, session)
                err = {
                    "en": f"❌ Please enter a valid number.\n{get_prompt(idx, lang)}",
                    "hi": f"❌ कृपया एक सही संख्या दर्ज करें।\n{get_prompt(idx, lang)}",
                    "mr": f"❌ कृपया वैध संख्या प्रविष्ट करा.\n{get_prompt(idx, lang)}"
                }
                return err.get(lang, err["en"]), lang
        elif key in ("isTaxPayer", "hasOutstandingLoan", "isOrganic"):
            session["profile"][key] = parse_bool(stripped)
        else:
            session["profile"][key] = stripped

        next_idx = idx + 1
        if next_idx < len(STEPS):
            session["step"] = next_idx
            save_session(number, session)
            return get_prompt(next_idx, lang), lang
        else:
            session["state"] = "idle"
            session["step"] = 0
            try:
                el = call_eligibility(lang, session["profile"])
                ec = sum(1 for item in el if item.get("eligible"))
                tot = len(el)
            except Exception:
                ec, tot = 0, 0
            save_session(number, session)
            name = session["profile"].get("name", "Farmer")
            saved = {
                "en": f"✅ *{name}*, your profile is saved!\nYou qualify for *{ec}/{tot}* schemes.\n\nType *schemes* to see the list.",
                "hi": f"✅ *{name}*, प्रोफ़ाइल सेव हो गई!\nआप *{ec}/{tot}* योजनाओं के पात्र हैं।\n\nसूची के लिए *schemes* लिखें।",
                "mr": f"✅ *{name}*, तुमची प्रोफाइल सेव्ह झाली!\nतुम्ही *{ec}/{tot}* योजनांसाठी पात्र आहात.\n\nयादीसाठी *schemes* टाइप करा."
            }
            return saved.get(lang, saved["en"]), lang

    if low in ("schemes", "all schemes", "योजना", "सर्व योजना", "सभी योजनाएं"):
        try:
            q = {"en": "all schemes", "hi": "सभी योजनाएं", "mr": "सर्व योजना"}.get(lang, "all schemes")
            reply = format_chat_reply(call_chat(q, lang, session.get("profile", {})), lang)
        except Exception:
            reply = "⚠️ Service temporarily unavailable."
        save_session(number, session)
        return reply, lang

    try:
        reply = format_chat_reply(call_chat(norm, lang, session.get("profile", {})), lang)
    except Exception:
        err = {
            "en": "⚠️ Could not connect to scheme engine.",
            "hi": "⚠️ योजना सहायक से संपर्क नहीं हो सका।",
            "mr": "⚠️ योजना सहाय्यकाशी संपर्क होऊ शकला नाही."
        }
        reply = err.get(lang, err["en"])

    save_session(number, session)
    return reply, lang

# ── Voice Processing ──────────────────────────────────────────────────────
def process_voice_note(audio_bytes: bytes, session_lang: str) -> tuple[str, str]:
    """
    Converts voice audio bytes (ogg/opus) to WAV and transcribes using Whisper tiny.
    Uses Marathi domain vocabulary initial_prompt to ensure Devanagari output and fast ~5s latency.
    Returns: (normalized_transcription, detected_language)
    """
    uid = uuid.uuid4().hex[:8]
    in_file = AUDIO_CACHE / f"in_{uid}.ogg"
    wav_file = AUDIO_CACHE / f"in_{uid}.wav"
    in_file.write_bytes(audio_bytes)

    try:
        ffmpeg_exec = str(FFMPEG_BIN / "ffmpeg.exe") if (FFMPEG_BIN / "ffmpeg.exe").exists() else "ffmpeg"
        cmd = [ffmpeg_exec, "-y", "-i", str(in_file), "-ar", "16000", "-ac", "1", str(wav_file)]
        subprocess.run(cmd, capture_output=True, check=True)

        whisper_model = get_whisper()
        import torch
        torch.set_num_threads(4)

        whisper_kwargs = {
            "fp16": False,
            "task": "transcribe",
            "initial_prompt": WHISPER_PROMPT,
            "condition_on_previous_text": False,
            "without_timestamps": True,
            "beam_size": 1,
            "best_of": 1,
            "temperature": 0.0,
        }
        if session_lang in ("mr", "hi", "en"):
            whisper_kwargs["language"] = session_lang

        res = whisper_model.transcribe(str(wav_file), **whisper_kwargs)
        raw_text = res.get("text", "").strip()
        print(f"[voice] Raw whisper transcript: {raw_text.encode('ascii','replace').decode()}", flush=True)

        norm_text = normalize_query(raw_text)

        # Detect language from transcribed text
        det = detect_language(norm_text)
        final_lang = det if det else session_lang

        return norm_text, final_lang
    finally:
        in_file.unlink(missing_ok=True)
        wav_file.unlink(missing_ok=True)

def generate_voice_reply(text: str, lang: str) -> str:
    """
    Generates natural spoken audio via gTTS and encodes as faststart AAC .m4a.
    Explains the scheme name AND core benefit clearly (up to 250 characters).
    Returns: filename of generated audio in AUDIO_CACHE.
    """
    from gtts import gTTS
    clean = re.sub(r"\*([^*]+)\*", r"\1", text)
    clean = re.sub(r"https?://\S+", "", clean)
    clean = re.sub(r"\b\w+\.(gov|in|org|com)\S*", "", clean)
    clean = re.sub(r"[🌾✅❌📋📞🎤🌱⚠️•💰📄🌐]", "", clean)
    # Convert Rs to full word for smooth pronunciation
    clean = re.sub(r"\bRs\.?\s*", "रु. ", clean)
    clean = re.sub(r"\n+", ". ", clean)
    clean = re.sub(r"(अर्जासाठी|Apply at|आवेदन करें)\s*:?\s*$", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Build clean spoken message with scheme name AND benefit
    sentences = [s.strip() for s in re.split(r"[।\.]", clean) if s.strip()]
    spoken = ""
    for s in sentences:
        if len(spoken) + len(s) + 2 <= 140:
            spoken += s + ("। " if lang in ("mr", "hi") else ". ")
        else:
            break

    spoken = spoken.strip() or clean[:130]
    if not spoken:
        fallbacks = {
            "mr": "माहिती उपलब्ध आहे.",
            "hi": "जानकारी उपलब्ध है।",
            "en": "Information is available."
        }
        spoken = fallbacks.get(lang, fallbacks["mr"])

    g_lang = {"en": "en", "hi": "hi", "mr": "mr"}.get(lang, "mr")
    uid = uuid.uuid4().hex[:8]
    temp_mp3 = AUDIO_CACHE / f"tmp_{uid}.mp3"
    m4a_name = f"out_{uid}.m4a"
    m4a_path = AUDIO_CACHE / m4a_name

    tts = gTTS(text=spoken, lang=g_lang, slow=False)
    tts.save(str(temp_mp3))

    ffmpeg_exec = str(FFMPEG_BIN / "ffmpeg.exe") if (FFMPEG_BIN / "ffmpeg.exe").exists() else "ffmpeg"
    cmd = [
        ffmpeg_exec, "-y", "-i", str(temp_mp3),
        "-c:a", "aac", "-b:a", "64k", "-ar", "24000", "-ac", "1",
        "-movflags", "+faststart",
        str(m4a_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    temp_mp3.unlink(missing_ok=True)
    return m4a_name

# ── FastAPI App ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[bot] Pre-loading Whisper tiny model...", flush=True)
    get_whisper()
    print("[bot] Krushi Mitra Voice & Multilingual Server ready on port 8001.", flush=True)
    yield

app = FastAPI(title="Krushi Mitra WhatsApp Voice Bot", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def build_twiml(text: str, media_url: str | None = None) -> Response:
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if media_url:
        xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'  <Message>\n'
            f'    <Body>{safe}</Body>\n'
            f'    <Media>{media_url}</Media>\n'
            f'  </Message>\n'
            f'</Response>'
        )
    else:
        xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Response>\n'
            f'  <Message>\n'
            f'    <Body>{safe}</Body>\n'
            f'  </Message>\n'
            f'</Response>'
        )
    return Response(content=xml, media_type="application/xml")

@app.get("/audio/{filename}")
def get_audio(filename: str):
    p = AUDIO_CACHE / filename
    if p.exists():
        media_type = "audio/mp4" if filename.endswith(".m4a") else "audio/mpeg"
        return FileResponse(p, media_type=media_type)
    return Response(status_code=404, content="Audio not found")

@app.post("/twilio/webhook")
async def webhook(
    request: Request,
    From: Annotated[str, Form()] = "",
    Body: Annotated[str, Form()] = "",
    NumMedia: Annotated[str, Form()] = "0",
    MediaUrl0: Annotated[str, Form()] = "",
    MediaContentType0: Annotated[str, Form()] = "",
) -> Response:
    number = From.replace("whatsapp:", "").strip()
    if not number:
        return build_twiml("Invalid request.")

    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8001")
    base_url = f"{proto}://{host}"

    session = get_session(number)
    num_media = int(NumMedia or "0")
    is_voice = False
    user_query = Body.strip()

    # 1. Voice Note Handling
    if num_media > 0 and MediaUrl0 and ("audio" in MediaContentType0 or "ogg" in MediaContentType0):
        is_voice = True
        try:
            print(f"[bot] Downloading incoming voice note from {MediaUrl0}", flush=True)
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                r = client.get(MediaUrl0, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
                r.raise_for_status()
                audio_bytes = r.content

            transcribed, v_lang = process_voice_note(audio_bytes, session.get("lang", "mr"))
            print(f"[bot] Transcribed voice ({v_lang}): {transcribed.encode('ascii','replace').decode()}", flush=True)

            if transcribed:
                session["lang"] = v_lang
                user_query = transcribed
        except Exception as e:
            print(f"[bot] Voice processing error: {e}", flush=True)

    if not user_query:
        if is_voice:
            no_sp = {
                "en": "🎤 Could not hear clearly. Please speak again or type your question.",
                "hi": "🎤 आवाज़ साफ़ सुनाई नहीं दी। कृपया फिर से बोलें।",
                "mr": "🎤 आवाज स्पष्ट आली नाही. कृपया पुन्हा बोला किंवा टाइप करा."
            }
            return build_twiml(no_sp.get(session.get("lang", "mr"), no_sp["mr"]))
        return Response(content='<?xml version="1.0"?><Response></Response>', media_type="application/xml")

    # 2. Process query
    reply_text, reply_lang = handle_message(number, user_query)
    print(f"[bot] Reply ({reply_lang}): {reply_text[:60].encode('ascii','replace').decode()}", flush=True)

    # 3. Generate voice note audio response
    media_url = None
    if is_voice:
        try:
            m4a = generate_voice_reply(reply_text, reply_lang)
            media_url = f"{base_url}/audio/{m4a}"
            print(f"[bot] Generated audio reply: {media_url}", flush=True)
        except Exception as e:
            print(f"[bot] TTS error: {e}", flush=True)

    return build_twiml(reply_text, media_url=media_url)

@app.get("/health")
def health():
    return {"status": "ok", "service": "krushi-voice-bot"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

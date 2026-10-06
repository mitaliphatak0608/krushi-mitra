"""whatsapp_bot/bot_logic.py — Core conversation state machine."""
import os
from pathlib import Path
from typing import Any
import httpx
from . import sessions
from . import voice as voice_pipeline

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

PROFILE_STEPS: list[dict[str, Any]] = [
    {"key":"name","prompts":{"en":"1. What is your name?","hi":"1. आपका नाम क्या है?","mr":"1. तुमचे नाव काय आहे?"},"type":"text"},
    {"key":"landholding","prompts":{"en":"2. Land in hectares? (e.g. 1.5)","hi":"2. जमीन कितने हेक्टेयर? (जैसे 1.5)","mr":"2. जमीन किती हेक्टर? (उदा. 1.5)"},"type":"float"},
    {"key":"category","prompts":{"en":"3. Social category? General / OBC / SC / ST","hi":"3. सामाजिक श्रेणी? General / OBC / SC / ST","mr":"3. सामाजिक प्रवर्ग? General / OBC / SC / ST"},"type":"text"},
    {"key":"region","prompts":{"en":"4. Region? (Marathwada/Vidarbha/Western Maharashtra)","hi":"4. क्षेत्र? (Marathwada/Vidarbha/Western Maharashtra)","mr":"4. विभाग? (Marathwada/Vidarbha/Western Maharashtra)"},"type":"text"},
    {"key":"cropSeason","prompts":{"en":"5. Crop season? Kharif / Rabi / Annual Commercial","hi":"5. फसल मौसम? Kharif / Rabi / Annual Commercial","mr":"5. हंगाम? Kharif / Rabi / Annual Commercial"},"type":"text"},
    {"key":"primaryCrop","prompts":{"en":"6. Primary crop? (Cotton/Soybean/Wheat)","hi":"6. मुख्य फसल? (कपास/सोयाबीन/गेहूं)","mr":"6. मुख्य पीक? (कापूस/सोयाबीन/गहू)"},"type":"text"},
    {"key":"annualIncome","prompts":{"en":"7. Annual household income in Rs? (e.g. 120000)","hi":"7. वार्षिक आय रु में? (जैसे 120000)","mr":"7. वार्षिक उत्पन्न रु मध्ये? (उदा. 120000)"},"type":"float"},
    {"key":"isTaxPayer","prompts":{"en":"8. Income tax payer? Yes / No","hi":"8. आयकर दाता हैं? Yes / No","mr":"8. आयकर भरता? Yes / No"},"type":"bool"},
    {"key":"hasOutstandingLoan","prompts":{"en":"9. Outstanding crop loan? Yes / No","hi":"9. फसल ऋण बकाया? Yes / No","mr":"9. पीक कर्ज थकबाकी? Yes / No"},"type":"bool"},
    {"key":"isOrganic","prompts":{"en":"10. Certified organic farming? Yes / No","hi":"10. प्रमाणित जैविक खेती? Yes / No","mr":"10. प्रमाणित सेंद्रिय शेती? Yes / No"},"type":"bool"},
]

MENU_TEXT = {
    "en":"Menu:\n- Ask any scheme question\n- Type profile\n- Type schemes\n- Type reset\n- Say: Hindi/Marathi/English",
    "hi":"मेनू:\n- कोई भी योजना सवाल पूछें\n- profile टाइप करें\n- schemes टाइप करें\n- reset टाइप करें\n- भाषा: Hindi/Marathi/English",
    "mr":"मेनू:\n- कोणताही योजना प्रश्न विचारा\n- profile टाइप करा\n- schemes टाइप करा\n- reset टाइप करा\n- भाषा: Hindi/Marathi/English",
}
LANG_ACK = {"en":"Language set to English.","hi":"भाषा हिंदी में बदल दी।","mr":"भाषा मराठी मध्ये बदलली."}
_LANG_KW = {"en":{"english","in english"},"hi":{"hindi","हिंदी"},"mr":{"marathi","मराठी"}}
_RESET_W = {"reset","रीसेट","रीसेट करा","start over"}
_MENU_W  = {"menu","help","मेनू","मदद","सहाय्य"}
_PROF_W  = {"profile","my profile","प्रोफ़ाइल","प्रोफाइल"}

def detect_language(text: str):
    low = text.strip().lower()
    for lang,kws in _LANG_KW.items():
        if low in kws or any(k in low for k in kws): return lang
    return None

def _parse_bool(t: str) -> str:
    return "Yes" if t.strip().lower() in ("yes","y","हो","हाँ","हां","होय","1","true") else "No"

def _prompt(idx: int, lang: str) -> str:
    s = PROFILE_STEPS[idx]; return s["prompts"].get(lang, s["prompts"]["en"])

def _chat(q, lang, profile):
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{BACKEND_URL}/chat", json={"query":q,"lang":lang,"profile":profile})
    r.raise_for_status(); return r.json()

def _eligibility(lang, profile):
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{BACKEND_URL}/eligibility", json={"profile":profile,"lang":lang})
    r.raise_for_status(); return r.json()

def _fmt(resp, lang):
    if not resp.get("found"):
        return {"en":"No info found. Type menu.","hi":"जानकारी नहीं मिली। menu टाइप करें।","mr":"माहिती मिळाली नाही. menu टाइप करा."}.get(lang,"No info.")
    t = resp.get("type","")
    if t in ("greeting","scheme"): return resp.get("message","") or ""
    hdr = resp.get("message",""); schemes = resp.get("schemes") or []
    if not schemes: return hdr
    lines = [hdr,""]
    for s in schemes[:10]:
        lines.append(("OK" if s.get("eligible") else "X") + " " + s.get("name",""))
        lines.append("  " + s.get("note",""))
    return "\n".join(lines)

def handle_message(wa_number: str, text: str, *, is_voice=False):
    session = sessions.get(wa_number)
    lang = session["lang"]; stripped = text.strip(); lower = stripped.lower()
    session["voice_mode"] = is_voice
    sv = is_voice

    nl = detect_language(stripped)
    if nl:
        session["lang"] = nl; sessions.save(wa_number, session); return LANG_ACK[nl], False

    if lower in _RESET_W or any(w in lower for w in _RESET_W):
        sessions.reset(wa_number)
        return {"en":"Session reset!","hi":"सत्र रीसेट!","mr":"सत्र रीसेट!"}.get(lang,"Reset!"), False

    if lower in _MENU_W or any(w in lower for w in _MENU_W):
        sessions.save(wa_number, session); return MENU_TEXT.get(lang, MENU_TEXT["en"]), sv

    if lower in _PROF_W or any(w in lower for w in _PROF_W):
        session["state"] = sessions.STATE_PROFILE; session["step"] = 0
        sessions.save(wa_number, session)
        intro = {"en":"Setting up farm profile.\n\n","hi":"खेत प्रोफ़ाइल बना रहे हैं।\n\n","mr":"शेत प्रोफाइल तयार करत आहोत.\n\n"}
        return intro.get(lang,"") + _prompt(0,lang), sv

    if session["state"] == sessions.STATE_PROFILE:
        idx = session["step"]; step = PROFILE_STEPS[idx]; key = step["key"]
        if step["type"] == "float":
            try: session["profile"][key] = float(stripped.replace(",",""))
            except ValueError:
                sessions.save(wa_number, session)
                return "Please enter a valid number.\n" + _prompt(idx,lang), sv
        elif step["type"] == "bool":
            session["profile"][key] = _parse_bool(stripped)
        else:
            session["profile"][key] = stripped
        nxt = idx + 1
        if nxt < len(PROFILE_STEPS):
            session["step"] = nxt; sessions.save(wa_number, session); return _prompt(nxt,lang), sv
        else:
            session["state"] = sessions.STATE_IDLE; session["step"] = 0
            try:
                res = _eligibility(lang, session["profile"])
                ec = sum(1 for r in res if r.get("eligible")); tot = len(res)
            except: ec = tot = 0
            sessions.save(wa_number, session)
            name = session["profile"].get("name","Farmer")
            return {"en":f"Profile saved! {ec}/{tot} schemes eligible. Type schemes.","hi":f"प्रोफ़ाइल सेव! {ec}/{tot} योजनाएं पात्र। schemes टाइप करें।","mr":f"प्रोफाइल सेव! {ec}/{tot} योजना पात्र. schemes टाइप करा."}.get(lang,"Done!"), sv

    if lower in {"schemes","all schemes","सभी योजनाएं","सर्व योजना"}:
        try:
            q = {"en":"all schemes","hi":"सभी योजनाएं","mr":"सर्व योजना"}.get(lang,"all schemes")
            reply = _fmt(_chat(q,lang,session["profile"]),lang)
        except Exception as e: reply = f"Service error: {e}"
        sessions.save(wa_number, session); return reply, sv

    try:
        reply = _fmt(_chat(stripped,lang,session["profile"]),lang)
    except Exception:
        reply = {"en":"Service unavailable. Try again.","hi":"सेवा उपलब्ध नहीं। पुनः प्रयास करें।","mr":"सेवा उपलब्ध नाही. पुन्हा प्रयत्न करा."}.get(lang,"Error.")
    sessions.save(wa_number, session); return reply, sv

def handle_voice_message(wa_number: str, audio_ogg_path: Path):
    session = sessions.get(wa_number); lang = session["lang"]
    try: text = voice_pipeline.transcribe(audio_ogg_path, lang=lang)
    except Exception:
        return {"en":"Could not process voice. Type your question.","hi":"आवाज़ नहीं समझी। टाइप करें।","mr":"आवाज समजली नाही. टाइप करा."}.get(lang,"Error."), False
    if not text:
        return {"en":"Could not hear clearly. Try again.","hi":"स्पष्ट नहीं सुनाई दिया। फिर बोलें।","mr":"स्पष्ट ऐकू नाही. पुन्हा बोला."}.get(lang,"Error."), False
    return handle_message(wa_number, text, is_voice=True)

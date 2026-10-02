"""
backend/voice_utils.py
=======================
Turns a normal ChatResponse (built for on-screen reading, with emojis,
bullet lists, links, etc.) into a short, clean, speakable string for
text-to-speech playback in the Voice Assistant.

Design goals:
- Real-time friendly: cheap string ops only, no extra model calls.
- Multilingual: works on en / hi / mr text as-is (no translation needed,
  since qa_engine already returns localized text).
- Short: TTS should not read a wall of text. We cap length and stop at a
  sentence boundary so the voice reply sounds natural, not cut off mid-word.
"""

import re
from typing import Any

# Symbols that read badly or not at all through TTS engines
_STRIP_CHARS = [
    "✅", "❌", "💡", "✓", "•", "→", "—", "📄", "💰", "📋", "🌐", "📝",
    "🌾", "👉", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "ℹ️", "⚠️"
]

# Sentence-ending punctuation across en / hi / mr
_SENTENCE_END = r"[.!?।]"

MAX_SPEECH_CHARS = 340


def _clean(text: str) -> str:
    if not text:
        return ""
    # Remove markdown formatting characters (*, #, _, `, ~)
    text = re.sub(r"[*#_`~]", "", text)
    # Remove markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    for ch in _STRIP_CHARS:
        text = text.replace(ch, "")
    # collapse whitespace/newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _truncate_at_sentence(text: str, max_chars: int = MAX_SPEECH_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    # find the last sentence-ending punctuation inside the window
    matches = list(re.finditer(_SENTENCE_END, window))
    if matches:
        cut = matches[-1].end()
        return window[:cut].strip()
    # no sentence boundary found — hard cut on a word boundary
    return window.rsplit(" ", 1)[0].strip() + "…"


def simplify_for_speech(text: str, max_chars: int = MAX_SPEECH_CHARS) -> str:
    """Clean + shorten any free-text message so it sounds natural read aloud."""
    return _truncate_at_sentence(_clean(text), max_chars)


def build_speech_text(response_type: str, payload: dict[str, Any], lang: str = "en") -> str:
    """
    Build the spoken-friendly version of a /chat response.

    response_type: "greeting" | "all_schemes" | "scheme" | "not_found"
    payload: the same fields used to build the on-screen ChatResponse
    """
    if response_type == "greeting":
        return simplify_for_speech(payload.get("message", ""))

    if response_type == "not_found":
        not_found_msgs = {
            "en": "Sorry, I couldn't find a matching scheme. Try asking about crop insurance, solar pump, or PM-KISAN.",
            "hi": "माफ़ कीजिए, मुझे कोई योजना नहीं मिली। फसल बीमा, सौर पंप, या पीएम-किसान के बारे में पूछ कर देखें।",
            "mr": "माफ करा, मला योग्य योजना सापडली नाही. पीक विमा, सौर पंप किंवा पीएम-किसान बद्दल विचारून पहा.",
        }
        return not_found_msgs.get(lang, not_found_msgs["en"])

    if response_type == "all_schemes":
        schemes = payload.get("schemes") or []
        eligible = [s for s in schemes if s.get("eligible")]
        top = eligible[:5] if eligible else schemes[:5]
        names = [s.get("name", "") for s in top if s.get("name")]

        intro = simplify_for_speech(payload.get("message", ""), max_chars=180)
        if not names:
            return intro

        names_str = ", ".join(names)
        joiners = {
            "en": f"{intro} These include: {names_str}. Tap a scheme on screen to hear more about it.",
            "hi": f"{intro} इनमें शामिल हैं: {names_str}। अधिक जानने के लिए स्क्रीन पर किसी योजना पर टैप करें।",
            "mr": f"{intro} यामध्ये समाविष्ट आहेत: {names_str}. अधिक माहितीसाठी स्क्रीनवरील एखाद्या योजनेवर टॅप करा.",
        }
        return simplify_for_speech(joiners.get(lang, joiners["en"]), max_chars=420)

    if response_type == "scheme":
        # qa_engine.synthesize_answer already formats a clean, specific answer tailored to the question
        raw_msg = payload.get("message", "")
        return simplify_for_speech(raw_msg, max_chars=340)

    return simplify_for_speech(payload.get("message", ""))


# ---------------------------------------------------------------------------
# AI chatbot support (Phase 1)
# ---------------------------------------------------------------------------

def simplify_ai_response(
    answer: str,
    language: str = "en",
    max_chars: int = MAX_SPEECH_CHARS,
) -> str:
    """
    Convert an LLM-generated answer into a speakable string.

    LLM responses may contain markdown links, bullet lists, bold text, etc.
    We clean those out before handing off to the speech synthesizer.
    """
    if not answer:
        fallbacks = {
            "en": "I found some information for you. Please check the screen.",
            "hi": "मुझे आपके लिए कुछ जानकारी मिली है। कृपया स्क्रीन देखें।",
            "mr": "मला तुमच्यासाठी काही माहिती मिळाली आहे. कृपया स्क्रीन पहा.",
        }
        return fallbacks.get(language, fallbacks["en"])

    # Remove markdown links: [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", answer)
    # Remove raw URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove markdown headers: #, ##, etc.
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    # Remove markdown bold / italic markers: **, *
    cleaned = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", cleaned)
    # Remove list bullet markers: *, -, + at start of line
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    # Remove numbered list markers: 1., 2., etc.
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    # Remove emojis and special characters
    return simplify_for_speech(cleaned, max_chars=max_chars)

"""
backend/ai_engine.py
====================
Core AI orchestration for Krushi Mitra.

Responsibilities
────────────────
1. Semantic analysis  — intent detection, entity extraction, language detection
2. Context assembly   — gather verified scheme data + deterministic eligibility
3. Grounded response  — LLM produces an answer *only* from supplied context

Design invariants
─────────────────
• Eligibility is NEVER determined by the LLM.  ``rules.py`` is the sole
  authority; the LLM merely *presents* its output.
• Scheme data comes from ``schemes_content.json`` and the existing FAISS
  index.  The LLM does not invent scheme facts.
• If verified information is insufficient, the response says so explicitly.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from backend import ai_prompts, knowledge_base
from backend import rules as eligibility

logger = logging.getLogger(__name__)

# ── Scheme data (loaded once, reused) ─────────────────────────────────────

_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "schemes_content.json"

_schemes_cache: Optional[list[dict[str, Any]]] = None
_scheme_map_cache: Optional[dict[str, dict[str, Any]]] = None


def _load_schemes() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    global _schemes_cache, _scheme_map_cache
    if _schemes_cache is None:
        _schemes_cache = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        _scheme_map_cache = {s["scheme_id"]: s for s in _schemes_cache}
    return _schemes_cache, _scheme_map_cache  # type: ignore[return-value]


# ── OpenAI helpers ────────────────────────────────────────────────────────

def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your-"):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. "
            "Set it in backend/.env (see .env.example)."
        )
    return OpenAI(api_key=api_key)


def _get_chat_model() -> str:
    return os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def is_ai_enabled() -> bool:
    """Feature flag — set ``AI_CHAT_ENABLED=false`` in .env to disable."""
    return os.environ.get("AI_CHAT_ENABLED", "true").lower() in ("true", "1", "yes")


# ══════════════════════════════════════════════════════════════════════════
# 1.  SEMANTIC ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

def analyze_query(query: str, language: Optional[str] = None) -> dict[str, Any]:
    """
    Extract structured intent / entity / language information from a query.

    Returns a dict like::

        {
            "language": "mr",
            "intent": "scheme_query",
            "crop": null,
            "scheme_mentioned": "PM-KISAN",
            "location": null,
            "entities": {},
            "confidence": 0.92
        }

    Falls back to heuristic analysis if the LLM call fails.
    """
    client = _get_client()
    model = _get_chat_model()

    prompt = ai_prompts.SEMANTIC_ANALYSIS_PROMPT.format(query=query)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a query analysis engine.  "
                        "Return ONLY valid JSON — no markdown, no explanation."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        analysis: dict[str, Any] = json.loads(raw)

        # Override language if the caller explicitly provided one
        if language and language in ("en", "hi", "mr"):
            analysis["language"] = language

        # Validate intent
        valid_intents = {
            "scheme_query", "all_schemes", "eligibility_check",
            "greeting", "general_agriculture", "crop_disease", "pest_control", 
            "fertilizer", "irrigation", "crop_protection", "sowing", 
            "harvesting", "soil", "seed", "livestock", "unknown",
        }
        if analysis.get("intent") not in valid_intents:
            analysis["intent"] = "unknown"

        # Ensure all expected keys exist
        analysis.setdefault("language", language or "en")
        analysis.setdefault("intent", "unknown")
        analysis.setdefault("crop", None)
        analysis.setdefault("scheme_mentioned", None)
        analysis.setdefault("location", None)
        analysis.setdefault("entities", {})
        analysis.setdefault("confidence", 0.5)

        return analysis

    except Exception as exc:
        logger.warning("Semantic analysis LLM call failed: %s", exc)
        return {
            "language": language or _fallback_detect_language(query),
            "intent": _fallback_detect_intent(query),
            "crop": None,
            "scheme_mentioned": None,
            "location": None,
            "entities": {},
            "confidence": 0.0,
            "_fallback": True,
        }


# ── Fallback heuristics (no LLM) ─────────────────────────────────────────

def _fallback_detect_language(text: str) -> str:
    devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    total = sum(1 for c in text if c.isalpha()) or 1
    if devanagari / total > 0.3:
        return "mr" if any(w in text for w in ("आहे", "नाही", "साठी", "काय")) else "hi"
    return "en"


def _fallback_detect_intent(text: str) -> str:
    low = text.strip().lower()
    greetings = {"hi", "hello", "hey", "namaste", "namaskar", "नमस्कार", "नमस्ते"}
    if set(low.replace("?", "").replace("!", "").split()).issubset(greetings):
        return "greeting"
    all_kw = ["all scheme", "सर्व योजना", "सभी योजना", "list scheme"]
    if any(k in low for k in all_kw):
        return "all_schemes"
    return "unknown"


# ══════════════════════════════════════════════════════════════════════════
# 2.  CONTEXT ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════

def gather_context(
    analysis: dict[str, Any],
    profile: dict[str, Any],
    faiss_results: Optional[list[dict[str, Any]]] = None,
    agri_kb_results: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Build the ``<VERIFIED_CONTEXT>`` block for the response-generation prompt.

    Pulls data from ``schemes_content.json`` and the deterministic eligibility
    engine — never from the LLM.
    """
    schemes, scheme_map = _load_schemes()
    intent = analysis.get("intent", "unknown")
    lang = analysis.get("language", "en")

    parts: list[str] = []

    # ── greeting ──────────────────────────────────────────────────────────
    if intent == "greeting":
        return (
            "The user is greeting.  Respond with a warm, friendly greeting "
            "as Krushi Mitra, an AI scheme assistant for Indian farmers.  "
            "Mention you can help with scheme queries in English, Hindi, and Marathi."
        )

    # ── all_schemes ───────────────────────────────────────────────────────
    if intent == "all_schemes":
        parts.append("=== ALL AVAILABLE GOVERNMENT SCHEMES ===\n")
        for scheme in schemes:
            ev = eligibility.evaluate(scheme["scheme_id"], profile)
            parts.append(_format_scheme_context(scheme, ev, lang))
        return "\n".join(parts)

    # ── scheme_query / eligibility_check ──────────────────────────────────
    if intent in ("scheme_query", "eligibility_check"):
        matched = _find_scheme(analysis, faiss_results, scheme_map)
        if matched:
            ev = eligibility.evaluate(matched["scheme_id"], profile)
            parts.append("=== VERIFIED SCHEME DATA ===\n")
            parts.append(_format_scheme_context(matched, ev, lang))
            parts.append(
                f"\nSource: Official scheme data — last verified "
                f"{matched.get('last_verified', 'N/A')}"
            )
            parts.append(
                f"Official Portal: {matched.get('official_link', 'N/A')}"
            )
        else:
            parts.append("=== NO SPECIFIC SCHEME MATCHED ===")
            parts.append(
                "The user's query did not match a specific scheme.  "
                "Here is a summary of available schemes:\n"
            )
            for scheme in schemes:
                name = (
                    scheme.get("scheme_name", {}).get(lang)
                    or scheme.get("scheme_name", {}).get("en", scheme["scheme_id"])
                )
                parts.append(f"• {name} ({scheme.get('category', '')})")
        return "\n".join(parts)

    # ── agricultural intents ──────────────────────────────────────────────
    agri_intents = {
        "general_agriculture", "crop_disease", "pest_control", 
        "fertilizer", "irrigation", "crop_protection", "sowing", 
        "harvesting", "soil", "seed", "livestock"
    }
    
    if intent in agri_intents:
        if agri_kb_results:
            parts.append("=== VERIFIED AGRICULTURAL KNOWLEDGE ===\n")
            for i, doc in enumerate(agri_kb_results, 1):
                parts.append(f"[DOCUMENT {i}]")
                parts.append(f"Authority: {doc.get('authority', 'Unknown')}")
                parts.append(f"Source: {doc.get('source', 'Unknown')}")
                parts.append(f"Official URL: {doc.get('official_url', 'Unknown')}")
                parts.append(f"Last Verified: {doc.get('last_verified', 'Unknown')}")
                parts.append(f"Content:\n{doc.get('chunk_content', '')}\n")
            return "\n".join(parts)
        else:
            return (
                "=== INSUFFICIENT VERIFIED CONTEXT ==="
                "There is no verified information in the knowledge base regarding this topic. "
                "Do NOT guess or use general knowledge. Explicitly state that verified information "
                "is unavailable and advise contacting the local Krishi Vigyan Kendra (KVK) or "
                "Kisan Call Center (1800-180-1551)."
            )

    # ── unknown ───────────────────────────────────────────────────────────
    return (
        "No verified context available for this query.  "
        "Respond that you can help with government agricultural scheme "
        "queries and suggest asking about specific schemes (PM-KISAN, "
        "crop insurance, solar pump, drip irrigation, etc.)."
    )


# ── Scheme matching ───────────────────────────────────────────────────────

# Common aliases  →  canonical scheme_id
_ALIASES = {
    "PMKISAN": ["pm kisan", "pm-kisan", "pmkisan", "pradhan mantri kisan", "पीएम किसान", "पी एम किसान", "पीएम-किसान", "पंतप्रधान किसान"],
    "NAMO_SHETKARI": ["namo shetkari", "namo", "नमो शेतकरी", "नमो शेतकारी"],
    "PMFBY": ["pmfby", "crop insurance", "fasal bima", "pik vima", "पीक विमा", "फसल बीमा", "पीएमएफबीवाई", "पीएमएफबीवाय", "pm fasal bima"],
    "MICRO_IRRIGATION": ["micro irrigation", "drip irrigation", "sprinkler", "thibak", "pmksy", "ठिबक", "ठिबक सिंचन", "सूक्ष्म सिंचाई", "ड्रिप", "स्प्रिंकलर", "तुषार"],
    "SOLAR_PUMP": ["solar pump", "kusum", "pm-kusum", "सौर पंप", "सौर कृषी पंप", "सोलर पंप", "कुसुम"],
    "WELL_SUBSIDY": ["well subsidy", "vihir", "vihir anudan", "विहीर", "विहीर अनुदान", "कुआं अनुदान", "कुआं"],
    "KCC": ["kcc", "kisan credit", "credit card", "किसान क्रेडिट", "कर्ज कार्ड", "किसान क्रेडिट कार्ड"],
    "KARJMAFI": ["karjmafi", "loan waiver", "mahatma jyotirao phule", "mjpssy", "कर्जमाफी", "कर्ज माफी", "ऋण माफी"],
    "PKVY": ["pkvy", "organic farming", "paramparagat", "सेंद्रिय शेती", "सेंद्रिय", "जैविक खेती", "जैविक"],
    "SMAM": ["smam", "farm mechanization", "tractor", "implement", "अवजारे", "औजार", "कृषी अवजारे", "कृषि यंत्रीकरण", "ट्रॅक्टर", "शेती यंत्रीकरण"],
    "FARM_POND": ["farm pond", "shet tale", "magel tyala", "शेततळे", "खेत तालाब", "शेत तळे", "फार्म पॉन्ड"]
}

def _find_scheme(
    analysis: dict[str, Any],
    faiss_results: Optional[list[dict[str, Any]]],
    scheme_map: dict[str, dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Return the best-matching scheme dict, or ``None``."""

    mentioned: str = (analysis.get("scheme_mentioned") or "").strip()

    if mentioned:
        mentioned_lower = mentioned.lower()

        # 1. Exact alias match
        for sid, aliases in _ALIASES.items():
            if any(alias in mentioned_lower for alias in aliases):
                return scheme_map.get(sid)

        # 2. Exact scheme_id match
        for sid in scheme_map:
            if sid.lower() == mentioned_lower:
                return scheme_map[sid]

        # 3. Substring match on localised scheme names
        for sid, scheme in scheme_map.items():
            for name in scheme.get("scheme_name", {}).values():
                if isinstance(name, str) and mentioned_lower in name.lower():
                    return scheme

        # 3. Alias lookup
        for alias, sid in _ALIASES.items():
            if alias in mentioned_lower and sid in scheme_map:
                return scheme_map[sid]

    # 4. Fall back to the top FAISS result
    if faiss_results:
        top_sid = faiss_results[0].get("scheme_id")
        if top_sid and top_sid in scheme_map:
            return scheme_map[top_sid]

    return None


# ── Format scheme + eligibility for the LLM context ──────────────────────

def _format_scheme_context(
    scheme: dict[str, Any],
    eval_result: dict[str, Any],
    lang: str = "en",
) -> str:
    """Render one scheme as a structured text block for the LLM."""

    sid = scheme.get("scheme_id", "")
    name_dict = scheme.get("scheme_name", {})
    name_en = name_dict.get("en", sid)
    name_local = name_dict.get(lang, name_en)

    benefit = (
        scheme.get("benefit_text", {}).get(lang)
        or scheme.get("benefit_text", {}).get("en", "")
    )
    elig_summary = (
        scheme.get("eligibility_summary", {}).get(lang)
        or scheme.get("eligibility_summary", {}).get("en", "")
    )
    docs = (
        scheme.get("documents_required", {}).get(lang)
        or scheme.get("documents_required", {}).get("en", [])
    )
    docs_str = ", ".join(docs) if isinstance(docs, list) else str(docs)
    status = (
        scheme.get("status_notes", {}).get(lang)
        or scheme.get("status_notes", {}).get("en", "")
    )

    eligible = eval_result.get("eligible", True)
    note = eval_result.get("note", "")

    lines = [
        f"Scheme ID: {sid}",
        f"Name: {name_local}" + (f" ({name_en})" if name_local != name_en else ""),
        f"Type: {scheme.get('type', '')}",
        f"Category: {scheme.get('category', '')}",
        f"Benefit: {benefit}",
        f"Eligibility Summary: {elig_summary}",
        f"Documents Required: {docs_str}",
        f"Status: {status}",
        f"Official Link: {scheme.get('official_link', '')}",
        f"Last Verified: {scheme.get('last_verified', '')}",
        "",
        "--- ELIGIBILITY EVALUATION (deterministic rules engine) ---",
        f"Eligible: {'Yes' if eligible else 'No'}",
        f"Determination: {note}",
        "(Present this eligibility result as-is.  Do NOT modify or reinterpret.)",
        "",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# 3.  GROUNDED RESPONSE GENERATION
# ══════════════════════════════════════════════════════════════════════════

def generate_response(
    query: str,
    analysis: dict[str, Any],
    context: str,
    profile: dict[str, Any],
    agri_kb_results: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Produce a grounded conversational answer using the assembled context.

    Returns::

        {
            "answer": "...",
            "language": "en",
            "intent": "scheme_query",
            "sources": [ { "name": ..., "authority": ..., ... } ],
            "grounded": True,
            "analysis": { ... },
        }
    """
    lang = analysis.get("language", "en")
    intent = analysis.get("intent", "unknown")

    # ── Try to generate via LLM ───────────────────────────────────────────
    try:
        client = _get_client()
        model = _get_chat_model()

        user_prompt = ai_prompts.RESPONSE_GENERATION_PROMPT.format(
            context=context,
            query=query,
            language={"en": "English", "hi": "Hindi", "mr": "Marathi"}.get(lang, "English"),
        )

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ai_prompts.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.15,
            max_tokens=1024,
        )

        answer = (completion.choices[0].message.content or "").strip()

    except Exception as exc:
        logger.error("Response generation LLM call failed: %s", exc)
        # Provide a safe, non-hallucinated fallback
        answer = ai_prompts.UNVERIFIED_FALLBACK.get(lang, ai_prompts.UNVERIFIED_FALLBACK["en"])

    # ── Assemble structured response ──────────────────────────────────────
    grounded = _is_grounded(intent, context)
    sources = _extract_sources(analysis, agri_kb_results)

    return {
        "answer": answer,
        "language": lang,
        "intent": intent,
        "sources": sources,
        "grounded": grounded,
        "analysis": analysis,
    }


# ── Helpers ───────────────────────────────────────────────────────────────

def _is_grounded(intent: str, context: str) -> bool:
    """Conservative check: is the response backed by verified data?"""
    if intent == "greeting":
        return True
    if "VERIFIED SCHEME DATA" in context or "ALL AVAILABLE" in context:
        return True
    if "VERIFIED AGRICULTURAL KNOWLEDGE" in context:
        return True
    return False


def _extract_sources(analysis: dict[str, Any], agri_kb_results: Optional[list[dict[str, Any]]] = None) -> list[dict[str, str]]:
    """Build source-citation entries from the matched scheme or agri KB."""
    sources: list[dict[str, str]] = []
    _, scheme_map = _load_schemes()
    intent = analysis.get("intent", "unknown")

    if intent in ("scheme_query", "eligibility_check"):
        mentioned = analysis.get("scheme_mentioned") or ""
        for sid, scheme in scheme_map.items():
            names = scheme.get("scheme_name", {})
            if sid.lower() == mentioned.lower() or any(
                isinstance(n, str) and mentioned.lower() in n.lower()
                for n in names.values()
            ):
                sources.append({
                    "name": names.get("en", sid),
                    "authority": f"Government of India / Maharashtra — {scheme.get('type', '')}",
                    "url": scheme.get("official_link", ""),
                    "last_verified": scheme.get("last_verified", ""),
                })
                break

    if intent == "all_schemes":
        sources.append({
            "name": "Government Scheme Database",
            "authority": "Central & Maharashtra State Government",
            "url": "mahadbt.maharashtra.gov.in",
            "last_verified": "2026-08-22",
        })

    agri_intents = {
        "general_agriculture", "crop_disease", "pest_control", 
        "fertilizer", "irrigation", "crop_protection", "sowing", 
        "harvesting", "soil", "seed", "livestock"
    }
    
    if intent in agri_intents and agri_kb_results:
        # Deduplicate sources based on official URL
        seen_urls = set()
        for doc in agri_kb_results:
            url = doc.get('official_url', '')
            if url not in seen_urls:
                sources.append({
                    "name": doc.get('title', 'Verified Agricultural Advisory'),
                    "authority": doc.get('authority', 'Verified Authority'),
                    "url": url,
                    "last_verified": doc.get('last_verified', ''),
                })
                seen_urls.add(url)

    return sources

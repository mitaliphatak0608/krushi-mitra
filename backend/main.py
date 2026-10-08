import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from backend import auth_utils, database, knowledge_base, qa_engine, stt_tts, voice_utils
from backend import ai_engine, ai_prompts
from backend import rules as eligibility
from backend.sms_service import process_sms

logger = logging.getLogger(__name__)

# Initialize SQLite database
database.init_db()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parent / ".env")

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "schemes_content.json"
VECTOR_STORE = Path(__file__).resolve().parent / "vector_store"
INDEX_FILE = VECTOR_STORE / "schemes.faiss"
METADATA_FILE = VECTOR_STORE / "metadata.json"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Admin key is read from the environment — never hardcoded here.
# Set ADMIN_KEY in backend/.env (see .env.example).
ADMIN_KEY: str = os.environ.get("ADMIN_KEY", "")

# ---------------------------------------------------------------------------
# Load scheme data once at startup
# ---------------------------------------------------------------------------
with DATA_FILE.open(encoding="utf-8") as _f:
    schemes: list[dict[str, Any]] = json.load(_f)

# Fast lookup by scheme_id — used by /eligibility
scheme_map: dict[str, dict[str, Any]] = {s["scheme_id"]: s for s in schemes}

# ---------------------------------------------------------------------------
# Embedding model singleton — loaded once, reused for every /search request
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


# ---------------------------------------------------------------------------
# Vector store helpers
# ---------------------------------------------------------------------------
def load_vector_store() -> tuple[faiss.Index, list[dict[str, Any]]]:
    if not INDEX_FILE.exists() or not METADATA_FILE.exists():
        raise RuntimeError(
            "Vector store not found. Run `python backend/ingest.py` first."
        )
    index = faiss.read_index(str(INDEX_FILE))
    metadata: list[dict[str, Any]] = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    return index, metadata


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Krushi Mitra API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Allow the Vite dev server (port 5173) and any production origin.
    # Tighten this list before production deployment.
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class SchemeSearchResult(BaseModel):
    scheme: dict[str, Any]
    score: float
    language: str


class AdminKeyRequest(BaseModel):
    key: str


class AdminKeyResponse(BaseModel):
    valid: bool


class EligibilityRequest(BaseModel):
    profile: dict[str, Any] = {}
    lang: str = "en"       # en | hi | mr — controls display name/benefit language


class SchemeEligibilityResult(BaseModel):
    scheme_id: str
    name: str              # localized scheme name
    category: str
    benefit: str           # localized benefit text
    eligible: bool
    note: str              # personalised eligibility note from rules engine


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "farmer"
    adminKey: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str = "farmer"
    adminKey: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: dict[str, Any]
    profile: dict[str, Any]


class ProfileUpdateRequest(BaseModel):
    profile: dict[str, Any]


class NotificationItem(BaseModel):
    id: int
    scheme_id: str
    type: str          # "new_scheme" | "closing_soon"
    title: dict[str, str]
    body: dict[str, str]
    deadline: str | None
    eligible_categories: list[str]
    min_land: float | None
    max_income: float | None
    official_source: str | None = None
    official_link: str | None = None
    is_active: int
    created_at: str


class CreateNotificationRequest(BaseModel):
    scheme_id: str
    type: str          # "new_scheme" | "closing_soon"
    title: dict[str, str]
    body: dict[str, str]
    deadline: str | None = None
    eligible_categories: list[str] = []
    min_land: float | None = None
    max_income: float | None = None
    official_source: str | None = None
    official_link: str | None = None


class SmsSimulatorRequest(BaseModel):
    from_str: str = Field(..., alias="from")
    message: str

class SmsSimulatorResponse(BaseModel):
    success: bool
    message: str
    state: str
    language: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check — returns instantly without touching the vector store."""
    return {"status": "ok", "service": "krushi-mitra-api"}


@app.get("/schemes")
def get_schemes() -> list[dict[str, Any]]:
    """Return all scheme records from the JSON data file."""
    return schemes


@app.post("/sms/simulator", response_model=SmsSimulatorResponse)
def sms_simulator(body: SmsSimulatorRequest) -> SmsSimulatorResponse:
    """Isolated SMS simulation endpoint."""
    result = process_sms(body.from_str, body.message)
    return SmsSimulatorResponse(**result)


@app.get("/sms/history/{phone_number}")
def get_sms_conversation_history(phone_number: str) -> list[dict[str, Any]]:
    """Retrieves SMS history for the simulator."""
    history = database.get_sms_history(phone_number)
    return history


# ---------------------------------------------------------------------------
# Auth & Profile Endpoints
# ---------------------------------------------------------------------------
@app.post("/auth/register", response_model=AuthResponse)
def register(body: RegisterRequest) -> AuthResponse:
    """Registers a new user and returns JWT token + profile."""
    role = "admin" if body.role == "admin" else "farmer"
    if role == "admin":
        if not body.adminKey or body.adminKey.strip() != ADMIN_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Admin Access Key",
            )

    existing = database.get_user_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long",
        )

    pw_hash, salt = auth_utils.hash_password(body.password)
    user = database.create_user(
        name=body.name,
        email=body.email,
        password_hash=pw_hash,
        salt=salt,
        role=role,
    )

    token = auth_utils.create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
    })

    return AuthResponse(
        token=token,
        user={
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
        profile=user["profile"],
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    """Authenticates a user and returns JWT token + saved profile."""
    role = "admin" if body.role == "admin" else "farmer"
    if role == "admin":
        if not body.adminKey or body.adminKey.strip() != ADMIN_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Admin Access Key",
            )

    user = database.get_user_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not auth_utils.verify_password(body.password, user["password_hash"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = auth_utils.create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
    })

    return AuthResponse(
        token=token,
        user={
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
        profile=user["profile"],
    )


@app.get("/auth/me")
def get_me(current_user: dict[str, Any] = Depends(auth_utils.get_current_user)) -> dict[str, Any]:
    """Returns currently authenticated user data and their saved profile."""
    return {
        "user": {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
            "role": current_user["role"],
        },
        "profile": current_user["profile"],
    }


@app.put("/profile")
def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict[str, Any] = Depends(auth_utils.get_current_user),
) -> dict[str, Any]:
    """Updates and permanently persists the authenticated farmer's profile in SQLite."""
    success = database.update_user_profile(current_user["id"], body.profile)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    return {"status": "ok", "profile": body.profile}


@app.get("/admin/users")
def list_admin_users() -> list[dict[str, Any]]:
    """Returns list of registered users and their farm profile data for admin view."""
    return database.get_all_users()


# ---------------------------------------------------------------------------
# Notification endpoints
# ---------------------------------------------------------------------------

class ProfileQueryBody(BaseModel):
    profile: dict[str, Any] = {}
    lang: str = "en"


@app.post("/notifications")
def get_notifications(body: ProfileQueryBody) -> list[dict[str, Any]]:
    """
    Returns active notifications filtered by the farmer's profile.
    The profile is passed in the request body for eligibility filtering.
    """
    return database.get_active_notifications(profile=body.profile)


@app.get("/admin/notifications")
def list_all_notifications() -> list[dict[str, Any]]:
    """Returns ALL notifications (active + inactive) for the admin panel."""
    return database.get_all_notifications_admin()


@app.post("/admin/notifications", response_model=dict[str, Any])
def create_notification(body: CreateNotificationRequest) -> dict[str, Any]:
    """Admin creates a new scheme notification/alert."""
    if body.type not in ("new_scheme", "closing_soon"):
        raise HTTPException(
            status_code=422,
            detail="type must be 'new_scheme' or 'closing_soon'",
        )
    notif = database.create_notification(
        scheme_id=body.scheme_id,
        notif_type=body.type,
        title=body.title,
        body=body.body,
        deadline=body.deadline,
        eligible_categories=body.eligible_categories,
        min_land=body.min_land,
        max_income=body.max_income,
        official_source=body.official_source,
        official_link=body.official_link,
    )
    return notif


@app.patch("/admin/notifications/{notif_id}/deactivate")
def deactivate_notification(notif_id: int) -> dict[str, Any]:
    """Admin deactivates (soft-deletes) a notification by ID."""
    success = database.deactivate_notification(notif_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok", "id": notif_id}


# ---------------------------------------------------------------------------
# Settings Endpoints
# ---------------------------------------------------------------------------

@app.get("/settings")
def get_system_settings() -> dict[str, Any]:
    """Returns current system settings for admin console & system configuration."""
    return database.get_all_settings()


@app.put("/settings")
def update_system_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Updates system settings in the database."""
    return database.update_settings(updates)


@app.post("/settings/reset")
def reset_system_settings() -> dict[str, Any]:
    """Resets system settings to default baseline."""
    return database.reset_settings()


@app.post("/eligibility", response_model=list[SchemeEligibilityResult])
def check_eligibility(body: EligibilityRequest) -> list[SchemeEligibilityResult]:
    """
    Evaluate all 11 scheme eligibility rules against the given farmer profile.

    Returns every scheme (eligible and ineligible) sorted eligible-first, so the
    dashboard can show a ranked list without any client-side filtering.

    The ``lang`` field controls which language the ``name`` and ``benefit`` fields
    are returned in (en / hi / mr, defaults to en).
    """
    lang = body.lang if body.lang in ("en", "hi", "mr") else "en"
    results: list[SchemeEligibilityResult] = []

    for scheme_id, _rule_fn in eligibility.RULES.items():
        scheme = scheme_map.get(scheme_id)
        if scheme is None:
            continue   # scheme in rules but not in data — skip gracefully

        eval_result = eligibility.evaluate(scheme_id, body.profile)

        # Resolve localized display text (fall back to English if lang missing)
        name_dict    = scheme.get("scheme_name", {})
        benefit_dict = scheme.get("benefit_text", {})
        name    = name_dict.get(lang)    or name_dict.get("en", scheme_id)
        benefit = benefit_dict.get(lang) or benefit_dict.get("en", "")

        results.append(SchemeEligibilityResult(
            scheme_id=scheme_id,
            name=name,
            category=scheme.get("category", ""),
            benefit=benefit,
            eligible=eval_result["eligible"],
            note=eval_result["note"],
        ))

    # Sort: eligible schemes first, then ineligible
    results.sort(key=lambda r: (0 if r.eligible else 1, r.scheme_id))
    return results


@app.get("/search", response_model=list[SchemeSearchResult])
def search_schemes(q: str, limit: int = 5, lang: str = "en") -> list[SchemeSearchResult]:
    """
    Semantic search over the FAISS index.

    Parameters
    ----------
    q     : Free-text query (any language — the multilingual model handles it).
    limit : Maximum number of results (default 5).
    lang  : Filter results to a specific language variant: 'en', 'hi', or 'mr'.
            Defaults to 'en'. Pass 'all' to return results across all languages.
    """
    if lang not in ("en", "hi", "mr", "all"):
        raise HTTPException(status_code=422, detail="lang must be one of: en, hi, mr, all")

    try:
        index, metadata = load_vector_store()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    model = get_model()
    query_vec: np.ndarray = model.encode([q], normalize_embeddings=True)
    scores, indices = index.search(query_vec, min(limit * 3, len(metadata)))

    results: list[SchemeSearchResult] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        entry = metadata[idx]
        if lang != "all" and entry["language"] != lang:
            continue
        results.append(
            SchemeSearchResult(
                scheme=entry["original_scheme"],
                score=float(score),
                language=entry["language"],
            )
        )
        if len(results) >= limit:
            break

    return results


@app.post("/verify-admin-key", response_model=AdminKeyResponse)
def verify_admin_key(body: AdminKeyRequest) -> AdminKeyResponse:
    """
    Validate the admin access key.

    The expected key lives in the ADMIN_KEY environment variable (backend/.env).
    It is never shipped in the frontend JS bundle.
    """
    if not ADMIN_KEY:
        # Misconfigured server — refuse all admin logins rather than silently granting them.
        raise HTTPException(
            status_code=503,
            detail="Admin key is not configured on the server. "
                   "Set ADMIN_KEY in backend/.env.",
        )
    return AdminKeyResponse(valid=body.key == ADMIN_KEY)


# ---------------------------------------------------------------------------
# Chat endpoint — semantic search + eligibility evaluation in one call
# ---------------------------------------------------------------------------
NO_MATCH_THRESHOLD = 0.20


class ChatRequest(BaseModel):
    query: str
    lang: str = "en"
    profile: dict[str, Any] = {}


class SchemeSummaryItem(BaseModel):
    scheme_id: str
    name: str
    category: str
    benefit: str
    eligible: bool
    note: str


class ChatResponse(BaseModel):
    found: bool
    type: str = "scheme"  # "scheme" | "all_schemes" | "greeting"
    message: str | None = None
    schemes: list[SchemeSummaryItem] | None = None
    scheme_id: str | None = None
    scheme_name: dict[str, str] | None = None   # { en, hi, mr }
    eligible: bool | None = None
    note: str | None = None                      # personalised eligibility note
    benefit: dict[str, str] | None = None        # { en, hi, mr }
    documents: dict[str, list[str]] | None = None
    link: str | None = None
    score: float | None = None


GREETINGS = {
    "hi", "hello", "hey", "namaste", "namaskar", "namaskaram",
    "नमस्कार", "नमस्ते", "हॅलो", "हाय", "प्रणाम", "सुप्रभात"
}

ALL_SCHEMES_KEYWORDS = [
    # English — all / list
    "all scheme", "all schemes", "list scheme", "list schemes",
    "every scheme", "all the schemes", "what schemes", "which schemes",
    "available schemes", "schemes available", "show schemes", "show all",
    "tell me about all", "give all schemes", "how many schemes",
    "schemes for me", "eligible schemes", "show me schemes",
    # Marathi — all / list
    "सर्व योजना", "सगळ्या योजना", "सर्व शासकीय योजना", "योजनांची यादी",
    "सर्व योजनांची माहिती", "कोणत्या योजना", "उपलब्ध योजना", "सर्व माहिती",
    "कोणत्या योजनांसाठी", "माझ्यासाठी कोणत्या योजना",
    # Hindi — all / list
    "सभी योजना", "सभी योजनाएं", "योजनाओं की सूची", "कौन सी योजनाएं",
    "कुल योजनाएं", "योजनाओं के नाम", "सारी योजनाएं", "मेरे लिए योजनाएं",
]

# Queries specifically asking WHY a farmer is NOT eligible for schemes
INELIGIBLE_REASONS_KEYWORDS = [
    # English
    "why not eligible", "why am i not", "not eligible for", "ineligible",
    "which schemes not", "which scheme not", "not qualify", "don't qualify",
    "do not qualify", "why can't i", "why cannot", "reason not eligible",
    "not getting", "why i am not", "why am i ineligible", "not approved",
    "cannot get", "can't get", "which schemes am i not", "schemes i am not",
    "schemes i'm not", "not covered", "excluded from", "what makes me ineligible",
    # Marathi
    "का पात्र नाही", "पात्र का नाही", "पात्र नाही का", "कोणत्या योजनांसाठी पात्र नाही",
    "अपात्र का", "अपात्र आहे का", "का मिळत नाही", "का मिळणार नाही",
    "कारण काय", "नाकारले का", "का नाही पात्र",
    # Hindi
    "क्यों पात्र नहीं", "पात्र क्यों नहीं", "अपात्र क्यों", "क्यों नहीं मिलेगा",
    "कौन सी योजना नहीं", "किन योजनाओं के लिए नहीं", "क्यों नहीं मिलता",
    "कारण बताएं", "अयोग्य क्यों", "क्यों नहीं पात्र",
]


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """
    Conversational scheme assistant with intent classification and RAG retrieval:
    1. Greeting intent: Returns a helpful greeting in the user's language.
    2. Ineligible-reasons intent: Lists ALL schemes the farmer does NOT qualify for, with reasons.
    3. All schemes intent: Returns all 11 central and state schemes evaluated against profile.
    4. Specific scheme intent: FAISS cross-lingual embedding search + eligibility evaluation.
    """
    lang = body.lang if body.lang in ("en", "hi", "mr") else "en"
    raw_query = body.query.strip().lower()

    # 1. Greeting intent check
    clean_words = set(raw_query.replace("?", "").replace("!", "").replace(".", "").split())
    if clean_words and clean_words.issubset(GREETINGS):
        greeting_msgs = {
            "en": "Namaste! I am Krushi Mitra, your AI scheme assistant. You can ask me about any specific farmer welfare scheme (like Solar Pump, Drip Irrigation, Crop Insurance, PM-KISAN), or ask 'Tell me about all schemes' for a full list!",
            "hi": "नमस्ते! मैं कृषी मित्र हूँ, आपका एआई योजना सहायक। आप मुझसे किसी भी विशिष्ट किसान कल्याण योजना (जैसे सौर पंप, ड्रिप सिंचाई, फसल बीमा, पीएम-किसान) के बारे में पूछ सकते हैं, या पूरी सूची के लिए 'सभी योजनाएं बताओ' कह सकते हैं!",
            "mr": "नमस्कार! मी कृषी मित्र आहे, तुमचा एआई योजना सहाय्यक. तुम्ही मला कोणत्याही विशिष्ट शेतकरी योजनेबद्दल (जसे की सौर कृषी पंप, ठिबक सिंचन, पीक विमा, पीएम-किसान) विचारू शकता किंवा संपूर्ण यादीसाठी 'सर्व योजना सांगा' विचारू शकता!"
        }
        return ChatResponse(
            found=True,
            type="greeting",
            message=greeting_msgs.get(lang, greeting_msgs["en"]),
        )

    # 2. Ineligible-reasons intent — "why am I not eligible / which schemes am I not eligible for"
    is_ineligible_query = any(k in raw_query for k in INELIGIBLE_REASONS_KEYWORDS)

    if is_ineligible_query:
        ineligible_items: list[SchemeSummaryItem] = []
        for s_id in eligibility.RULES.keys():
            scheme = scheme_map.get(s_id)
            if not scheme:
                continue
            eval_res = eligibility.evaluate(s_id, body.profile)
            if eval_res["eligible"]:
                continue  # skip eligible schemes — user only asked about ineligible ones
            name_d = scheme.get("scheme_name", {})
            ben_d  = scheme.get("benefit_text", {})
            name_val = name_d.get(lang) or name_d.get("en", s_id)
            ben_val  = ben_d.get(lang) or ben_d.get("en", "")

            ineligible_items.append(SchemeSummaryItem(
                scheme_id=s_id,
                name=name_val,
                category=scheme.get("category", ""),
                benefit=ben_val,
                eligible=False,
                note=eval_res["note"],
            ))

        ineligible_count = len(ineligible_items)

        if ineligible_count == 0:
            congrats_msgs = {
                "en": "Great news! Based on your current farm profile, you are eligible for ALL available schemes. Update your profile if your details have changed.",
                "hi": "बहुत बढ़िया! आपकी वर्तमान प्रोफ़ाइल के अनुसार, आप सभी उपलब्ध योजनाओं के लिए पात्र हैं।",
                "mr": "अभिनंदन! तुमच्या सध्याच्या प्रोफाइलनुसार, तुम्ही सर्व उपलब्ध योजनांसाठी पात्र आहात.",
            }
            return ChatResponse(
                found=True,
                type="ineligible_reasons",
                message=congrats_msgs.get(lang, congrats_msgs["en"]),
                schemes=[],
            )

        intro_msgs = {
            "en": (
                f"Based on your farm profile, you are NOT eligible for {ineligible_count} scheme(s). "
                f"Here is the reason for each:"
            ),
            "hi": (
                f"आपकी प्रोफ़ाइल के अनुसार, आप {ineligible_count} योजना(ओं) के लिए पात्र नहीं हैं। "
                f"नीचे प्रत्येक का कारण दिया गया है:"
            ),
            "mr": (
                f"तुमच्या प्रोफाइलनुसार, तुम्ही {ineligible_count} योजना(ना)साठी पात्र नाही. "
                f"खाली प्रत्येकाचे कारण दिले आहे:"
            ),
        }

        return ChatResponse(
            found=True,
            type="ineligible_reasons",
            message=intro_msgs.get(lang, intro_msgs["en"]),
            schemes=ineligible_items,
        )

    # 3. 'All schemes' / 'List schemes' overview intent check
    is_all_schemes = any(k in raw_query for k in ALL_SCHEMES_KEYWORDS) or (
        ("all" in raw_query or "every" in raw_query or "list" in raw_query) and "scheme" in raw_query
    ) or (
        ("सर्व" in raw_query or "सगळ्या" in raw_query) and "योजना" in raw_query
    ) or (
        ("सभी" in raw_query or "सारे" in raw_query or "सूची" in raw_query) and "योजना" in raw_query
    )

    if is_all_schemes:
        scheme_items: list[SchemeSummaryItem] = []
        for s_id in eligibility.RULES.keys():
            scheme = scheme_map.get(s_id)
            if not scheme:
                continue
            eval_res = eligibility.evaluate(s_id, body.profile)
            name_d = scheme.get("scheme_name", {})
            ben_d = scheme.get("benefit_text", {})
            name_val = name_d.get(lang) or name_d.get("en", s_id)
            ben_val = ben_d.get(lang) or ben_d.get("en", "")

            scheme_items.append(SchemeSummaryItem(
                scheme_id=s_id,
                name=name_val,
                category=scheme.get("category", ""),
                benefit=ben_val,
                eligible=eval_res["eligible"],
                note=eval_res["note"]
            ))

        # Sort eligible first
        scheme_items.sort(key=lambda x: (0 if x.eligible else 1, x.name))
        eligible_count = sum(1 for s in scheme_items if s.eligible)

        intro_msgs = {
            "en": f"Here is the complete overview of all {len(scheme_items)} Maharashtra & Central Government schemes. Based on your current farm profile, you are eligible for {eligible_count} schemes:",
            "hi": f"यहाँ महाराष्ट्र और केंद्र सरकार की सभी {len(scheme_items)} योजनाओं का विवरण है। आपकी वर्तमान प्रोफ़ाइल के अनुसार, आप {eligible_count} योजनाओं के लिए पात्र हैं:",
            "mr": f"येथे महाराष्ट्र व केंद्र शासनाच्या सर्व {len(scheme_items)} योजनांची संपूर्ण माहिती आहे. तुमच्या सध्याच्या प्रोफाइलनुसार, तुम्ही {eligible_count} योजनांसाठी पात्र आहात:"
        }

        return ChatResponse(
            found=True,
            type="all_schemes",
            message=intro_msgs.get(lang, intro_msgs["en"]),
            schemes=scheme_items,
        )

    # 4. Specific Scheme RAG Semantic Search
    try:
        index, metadata = load_vector_store()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    model = get_model()
    query_vec: np.ndarray = model.encode([body.query], normalize_embeddings=True)

    # Cross-lingual: search all vectors, best match wins regardless of language
    scores, indices = index.search(query_vec, 1)
    best_idx   = int(indices[0][0])
    best_score = float(scores[0][0])

    if best_idx < 0 or best_score < NO_MATCH_THRESHOLD:
        return ChatResponse(found=False, score=best_score)

    best_entry: dict[str, Any] = metadata[best_idx]
    scheme:     dict[str, Any] = best_entry["original_scheme"]
    scheme_id:  str             = best_entry["scheme_id"]

    # Apply eligibility rule
    result = eligibility.evaluate(scheme_id, body.profile)

    # Synthesize plain-language direct answer
    conversational_answer = qa_engine.synthesize_answer(
        query=body.query,
        scheme=scheme,
        profile=body.profile,
        eval_result=result,
        lang=lang,
    )

    return ChatResponse(
        found=True,
        type="scheme",
        message=conversational_answer,
        scheme_id=scheme_id,
        scheme_name=scheme.get("scheme_name"),
        eligible=result["eligible"],
        note=result["note"],
        benefit=scheme.get("benefit_text"),
        documents=scheme.get("documents_required"),
        link=scheme.get("official_link"),
        score=best_score,
    )

class AIChatRequest(BaseModel):
    message: str
    language: str = "en"
    profile: dict[str, Any] = {}
    voice: str | None = None


class AIChatResponse(BaseModel):
    answer: str
    language: str
    intent: str
    sources: list[Any] = []
    grounded: bool = True
    analysis: dict[str, Any] | None = None
    speech_text: str | None = None
    found: bool = True
    type: str | None = None
    scheme_id: str | None = None
    scheme_name: dict[str, Any] | None = None
    eligible: bool | None = None
    note: str | None = None
    benefit: dict[str, Any] | None = None
    documents: dict[str, Any] | None = None
    link: str | None = None
    score: float | None = None
    schemes: list[Any] | None = None


class AITranscribeResponse(BaseModel):
    text: str
    language: str


class AISpeakRequest(BaseModel):
    text: str
    language: str = "en"
    voice: str | None = None


def _require_ai():
    if not ai_engine.is_ai_enabled():
        raise HTTPException(
            status_code=503,
            detail="AI chat is disabled. Set AI_CHAT_ENABLED=true in backend/.env",
        )


def _chat_to_ai_response(chat_res: ChatResponse, lang: str) -> AIChatResponse:
    """Map a deterministic /chat response into an AIChatResponse."""
    if not chat_res.found:
        not_found_msgs = {
            "en": "I couldn't find a matching scheme for that query. Try asking about: crop insurance, drip irrigation, solar pump, kisan credit card, or loan waiver.",
            "hi": "इस प्रश्न के लिए कोई योजना नहीं मिली। कोशिश करें: फसल बीमा, ड्रिप सिंचाई, सौर पंप, किसान क्रेडिट कार्ड।",
            "mr": "या प्रश्नासाठी योजना सापडली नाही. वापरून पाहा: पीक विमा, ठिबक सिंचन, सौर पंप, किसान क्रेडिट कार्ड.",
        }
        ans = not_found_msgs.get(lang, not_found_msgs["en"])
        return AIChatResponse(
            answer=ans,
            language=lang,
            intent="unknown",
            sources=[],
            grounded=False,
            analysis={"intent": "unknown", "language": lang, "_fallback": True},
            speech_text=ans,
            found=False,
            type=chat_res.type,
            score=chat_res.score,
        )

    sources = []
    if chat_res.link:
        s_name = ""
        if isinstance(chat_res.scheme_name, dict):
            s_name = chat_res.scheme_name.get(lang) or chat_res.scheme_name.get("en") or (chat_res.scheme_id or "")
        elif chat_res.scheme_name:
            s_name = str(chat_res.scheme_name)
        elif chat_res.scheme_id:
            s_name = chat_res.scheme_id

        sources.append({
            "name": s_name or "Government Scheme Database",
            "authority": "Central & Maharashtra State Government",
            "url": chat_res.link,
            "last_verified": "2026-08-22",
        })
    elif chat_res.type == "all_schemes":
        sources.append({
            "name": "Government Scheme Database",
            "authority": "Central & Maharashtra State Government",
            "url": "mahadbt.maharashtra.gov.in",
            "last_verified": "2026-08-22",
        })

    speech_text = None
    if chat_res.message:
        speech_text = voice_utils.simplify_ai_response(chat_res.message, lang)

    return AIChatResponse(
        answer=chat_res.message or "",
        language=lang,
        intent=chat_res.type or "scheme_query",
        sources=sources,
        grounded=True,
        analysis={"intent": chat_res.type or "scheme_query", "language": lang, "_fallback": True},
        speech_text=speech_text or chat_res.message,
        found=True,
        type=chat_res.type,
        scheme_id=chat_res.scheme_id,
        scheme_name=chat_res.scheme_name,
        eligible=chat_res.eligible,
        note=chat_res.note,
        benefit=chat_res.benefit,
        documents=chat_res.documents,
        link=chat_res.link,
        score=chat_res.score,
        schemes=chat_res.schemes,
    )


@app.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(body: AIChatRequest):
    lang = body.language if body.language in ("en", "hi", "mr") else "en"

    # If AI provider / API key is not configured or disabled, fall back safely to /chat
    if not ai_engine.is_ai_enabled() or not ai_engine.has_llm_api_key():
        chat_res = chat(ChatRequest(query=body.message, lang=lang, profile=body.profile))
        return _chat_to_ai_response(chat_res, lang)

    try:
        analysis = ai_engine.analyze_query(body.message, lang)

        faiss_results = None
        if analysis.get("intent") in ("scheme_query", "eligibility_check", "unknown") or not analysis.get("intent"):
            try:
                model_st = get_model()
                index, meta = load_vector_store()
                q_vec = model_st.encode([body.message], normalize_embeddings=True)
                scores, indices = index.search(q_vec, min(5, len(meta)))

                seen: set[str] = set()
                faiss_results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0:
                        continue
                    entry = meta[idx]
                    sid = entry["scheme_id"]
                    if sid in seen:
                        continue
                    seen.add(sid)
                    faiss_results.append({"scheme_id": sid, "score": float(score)})
                    if len(faiss_results) >= 3:
                        break
            except Exception as exc:
                logger.warning("FAISS search error in ai_chat: %s", exc)
                faiss_results = None

        agri_kb_results = None
        agri_intents = {
            "general_agriculture", "crop_disease", "pest_control",
            "fertilizer", "irrigation", "crop_protection", "sowing",
            "harvesting", "soil", "seed", "livestock"
        }

        if analysis.get("intent") in agri_intents:
            try:
                agri_kb_results = knowledge_base.search_agri_knowledge(
                    query=body.message,
                    language=lang,
                    crop=analysis.get("crop"),
                    use_test=False,
                )
            except Exception:
                agri_kb_results = None

        context = ai_engine.gather_context(
            analysis, body.profile, faiss_results, agri_kb_results
        )

        result = ai_engine.generate_response(
            body.message, analysis, context, body.profile, agri_kb_results
        )

        # If LLM response failed to ground or gave an unverified fallback despite a good FAISS match, fall back to /chat
        if (not result.get("grounded") or result.get("answer") in ai_prompts.UNVERIFIED_FALLBACK.values()) and faiss_results:
            top_score = faiss_results[0].get("score", 0.0) if faiss_results else 0.0
            if top_score >= NO_MATCH_THRESHOLD:
                chat_res = chat(ChatRequest(query=body.message, lang=lang, profile=body.profile))
                if chat_res.found:
                    return _chat_to_ai_response(chat_res, lang)

        speech_text = voice_utils.simplify_ai_response(
            result["answer"], result["language"]
        )

        # Matched scheme details from deterministic rules engine
        matched_scheme = None
        _, s_map = ai_engine._load_schemes()
        matched_scheme = ai_engine._find_scheme(analysis, faiss_results, s_map)
        ev_result = None
        if matched_scheme:
            ev_result = eligibility.evaluate(matched_scheme["scheme_id"], body.profile)

        return AIChatResponse(
            answer=result["answer"],
            language=result["language"],
            intent=result["intent"],
            sources=result["sources"],
            grounded=result["grounded"],
            analysis=result.get("analysis"),
            speech_text=speech_text,
            found=result["grounded"],
            type=analysis.get("intent"),
            scheme_id=matched_scheme.get("scheme_id") if matched_scheme else None,
            scheme_name=matched_scheme.get("scheme_name") if matched_scheme else None,
            eligible=ev_result.get("eligible") if ev_result else None,
            note=ev_result.get("note") if ev_result else None,
            benefit=matched_scheme.get("benefit_text") if matched_scheme else None,
            documents=matched_scheme.get("documents_required") if matched_scheme else None,
            link=matched_scheme.get("official_link") if matched_scheme else None,
            score=faiss_results[0].get("score") if faiss_results else None,
        )

    except Exception as exc:
        logger.warning("AI processing failed, safely falling back to /chat: %s", exc)
        chat_res = chat(ChatRequest(query=body.message, lang=lang, profile=body.profile))
        return _chat_to_ai_response(chat_res, lang)


@app.post("/ai/transcribe", response_model=AITranscribeResponse)
async def ai_transcribe(file: UploadFile = File(...)):
    _require_ai()

    ctype = (file.content_type or "").lower()
    if ctype and not ctype.startswith("audio/"):
        raise HTTPException(
            status_code=422,
            detail=f"Expected audio file, received: {ctype}",
        )

    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Empty audio file.")

    if len(audio_bytes) > stt_tts.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large. Max {stt_tts.MAX_AUDIO_SIZE_BYTES // (1024*1024)} MB.",
        )

    try:
        text, lang = stt_tts.transcribe_audio(
            audio_bytes,
            filename=file.filename or "audio.webm",
        )
        return AITranscribeResponse(text=text, language=lang)

    except stt_tts.ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except stt_tts.ExternalAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed. Please try again.")


@app.post("/ai/speak")
def ai_speak(body: AISpeakRequest):

    if not body.text.strip():
        raise HTTPException(status_code=422, detail="Text cannot be empty.")

    try:
        audio_bytes = stt_tts.synthesize_speech(
            body.text,
            body.language,
            body.voice,
        )
        return Response(content=audio_bytes, media_type="audio/mpeg")

    except stt_tts.ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except stt_tts.ExternalAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="Speech synthesis failed. Please try again.")


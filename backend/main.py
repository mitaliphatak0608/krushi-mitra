import json
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from backend import auth_utils, database, knowledge_base, qa_engine, stt_tts, voice_utils
from backend import ai_engine
from backend import rules as eligibility

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
# ---------------------------------------------------------------------------
# Embedding model + vector store — loaded ONCE at startup, never again
# This eliminates the per-request cold-start delay (was ~5-15s per first call)
# ---------------------------------------------------------------------------
def _load_model() -> SentenceTransformer:
    print("[startup] Loading embedding model...", flush=True)
    m = SentenceTransformer(EMBEDDING_MODEL)
    print("[startup] Embedding model ready.", flush=True)
    return m


def _load_vector_store() -> tuple[faiss.Index, list[dict[str, Any]]]:
    if not INDEX_FILE.exists() or not METADATA_FILE.exists():
        raise RuntimeError(
            "Vector store not found. Run `python backend/ingest.py` first."
        )
    print("[startup] Loading FAISS index...", flush=True)
    index = faiss.read_index(str(INDEX_FILE))
    metadata: list[dict[str, Any]] = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    print(f"[startup] FAISS index ready — {index.ntotal} vectors.", flush=True)
    return index, metadata


# Singletons — assigned at startup; safe because FastAPI is single-process by default
_EMBED_MODEL: SentenceTransformer = _load_model()
_FAISS_INDEX: faiss.Index
_FAISS_META:  list[dict[str, Any]]
_FAISS_INDEX, _FAISS_META = _load_vector_store()


def get_model() -> SentenceTransformer:
    """Return the pre-loaded embedding model."""
    return _EMBED_MODEL


def load_vector_store() -> tuple[faiss.Index, list[dict[str, Any]]]:
    """Return the pre-loaded FAISS index and metadata (no disk I/O)."""
    return _FAISS_INDEX, _FAISS_META


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
    application_status: str = "open"          # open | seasonal | active_auto | portal_closed | closed | cycle_based | unconfirmed
    application_status_note: str = ""         # localized human-readable status description


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

        # Resolve localized application status note
        app_status      = scheme.get("application_status", "open")
        app_status_note_dict = scheme.get("application_status_note", {})
        app_status_note = (
            app_status_note_dict.get(lang)
            or app_status_note_dict.get("en", "")
        )

        results.append(SchemeEligibilityResult(
            scheme_id=scheme_id,
            name=name,
            category=scheme.get("category", ""),
            benefit=benefit,
            eligible=eval_result["eligible"],
            note=eval_result["note"],
            application_status=app_status,
            application_status_note=app_status_note,
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
    application_status: str = "open"


class ChatResponse(BaseModel):
    found: bool
    type: str = "scheme"  # "scheme" | "all_schemes" | "greeting"
    message: str | None = None
    speech_text: str | None = None               # spoken-friendly string for Voice Assistant TTS
    schemes: list[SchemeSummaryItem] | None = None
    scheme_id: str | None = None
    scheme_name: dict[str, str] | None = None   # { en, hi, mr }
    eligible: bool | None = None
    note: str | None = None                      # personalised eligibility note
    benefit: dict[str, str] | None = None        # { en, hi, mr }
    documents: dict[str, list[str]] | None = None
    link: str | None = None
    score: float | None = None
    application_status: str | None = None    # forwarded from scheme data for single-scheme results


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
    "what scheme am i", "which scheme am i", "scheme am i eligible",
    "schemes am i eligible", "scheme can i get", "schemes can i get",
    "scheme will i get", "schemes will i get", "scheme do i qualify",
    "schemes do i qualify", "am i eligible for any scheme",
    "any scheme for me", "any schemes for me", "which scheme for me",
    "what scheme for me", "scheme for farmer", "schemes for farmer",
    "which schemes can i", "what schemes can i", "scheme i can apply",
    "schemes i can apply", "eligible for which scheme", "eligible for which schemes",
    "tell me schemes", "give me schemes", "check my eligibility",
    "my eligibility", "my scheme", "my schemes", "schemes i qualify",
    "scheme i qualify", "what am i eligible", "what schemes am i",
    # Marathi — all / list / eligible
    "सर्व योजना", "सगळ्या योजना", "सर्व शासकीय योजना", "योजनांची यादी",
    "सर्व योजनांची माहिती", "कोणत्या योजना", "उपलब्ध योजना", "सर्व माहिती",
    "कोणत्या योजनांसाठी", "माझ्यासाठी कोणत्या योजना",
    "मी कोणत्या योजनांसाठी पात्र", "मला कोणती योजना", "कोणती योजना मिळेल",
    "कोणत्या योजना मला मिळतील", "माझ्यासाठी कोणती योजना", "योजना पात्रता",
    "कोणत्या योजनांसाठी पात्र आहे", "कोणती योजना लागू होते",
    "माझी पात्रता", "मला पात्र योजना", "पात्र योजना कोणत्या",
    "कोणत्या कोणत्या", "कोणत्या स्कीम", "कोणत्या स्कीमसाठी", "कोणत्या स्कीम्स",
    "कोणत्या कोणत्या स्कीमसाठी", "कोणत्या योजनेसाठी", "कोणत्या योजनांसाठी",
    "स्कीमसाठी एलिजिबल", "योजनेसाठी एलिजिबल", "योजनांसाठी एलिजिबल",
    "एलिजिबल आहे", "एलिजिबल आहेत", "मी कोणत्या", "मी कोणत्या कोणत्या",
    "कशासाठी पात्र", "कोणत्या लाभासाठी",
    "किन स्कीम", "किस स्कीम", "स्कीम के लिए एलिजिबल", "एलिजिबल हूं", "एलिजिबल हैं",
    # Hindi — all / list / eligible
    "सभी योजना", "सभी योजनाएं", "योजनाओं की सूची", "कौन सी योजनाएं",
    "कुल योजनाएं", "योजनाओं के नाम", "सारी योजनाएं", "मेरे लिए योजनाएं",
    "कौन सी योजना मिलेगी", "मुझे कौन सी योजना", "किस योजना के लिए पात्र",
    "कौन सी योजना के लिए पात्र", "मेरी पात्रता", "पात्र योजनाएं",
    "कौन सी योजना मिल सकती", "कौन सी योजनाओं के लिए पात्र",
    "मेरे लिए कौन सी योजना", "मुझे कौन सी योजनाएं", "योजना पात्रता",
    # Romanized Marathi (phonetically typed)
    "mala konti yojana", "konti yojana milel", "konty yojnansathi",
    "maze patra", "mazya sathi yojana", "patra ahe ka", "yojana milel ka",
    "konte yojana", "mla konti yojana",
    # Romanized Hindi (phonetically typed)
    "mujhe kaun si yojana", "kaun si yojana milegi", "kaunsi yojana",
    "kis yojana ke liye", "patra hun kya", "yojana milegi kya", "kon si yojana",
]

# Queries specifically asking WHY a farmer is NOT eligible for schemes
INELIGIBLE_REASONS_KEYWORDS = [
    # English
    "why not eligible", "why am i not", "not eligible for",
    "ineligible", "which schemes not", "which scheme not",
    "not qualify", "don't qualify", "do not qualify",
    "why can't i", "why cannot", "reason not eligible",
    "not getting", "why i am not", "why am i ineligible",
    "not approved", "cannot get", "can't get",
    "which schemes am i not", "schemes i am not", "schemes i'm not",
    "not covered", "excluded from", "what makes me ineligible",
    "why didn't i", "why don't i qualify", "not entitled",
    "not getting benefit", "benefit not coming", "why rejected",
    # Marathi
    "का पात्र नाही", "पात्र का नाही", "पात्र नाही का",
    "कोणत्या योजनांसाठी पात्र नाही", "अपात्र का", "अपात्र आहे का",
    "का मिळत नाही", "का मिळणार नाही", "कारण काय", "नाकारले का",
    "का नाही पात्र", "का मिळाले नाही", "का लाभ मिळत नाही",
    # Hindi
    "क्यों पात्र नहीं", "पात्र क्यों नहीं", "अपात्र क्यों",
    "क्यों नहीं मिलेगा", "कौन सी योजना नहीं", "किन योजनाओं के लिए नहीं",
    "क्यों नहीं मिलता", "कारण बताएं", "अयोग्य क्यों", "क्यों नहीं पात्र",
    "क्यों नहीं मिला", "लाभ क्यों नहीं", "क्यों वंचित",
]


# ---------------------------------------------------------------------------
# Pre-FAISS keyword alias lookup (Hindi / Marathi / transliterations -> scheme_id)
# ---------------------------------------------------------------------------
_SCHEME_ALIASES: dict[str, str] = {
    # 1. PM-KISAN
    "pm kisan": "PMKISAN", "pm-kisan": "PMKISAN", "pmkisan": "PMKISAN",
    "pm kisaan": "PMKISAN", "pradhan mantri kisan": "PMKISAN",
    "kisan samman nidhi": "PMKISAN", "kisan samman": "PMKISAN",
    "kisan installment": "PMKISAN",

    # 2. PMFBY (Crop Insurance)
    "pmfby": "PMFBY", "fasal bima": "PMFBY", "crop insurance": "PMFBY",
    "pm fasal bima": "PMFBY", "pik vima": "PMFBY", "pikvima": "PMFBY",
    "vima yojana": "PMFBY", "pradhan mantri fasal bima": "PMFBY",
    "farm insurance": "PMFBY", "weather insurance": "PMFBY",

    # 3. KCC (Kisan Credit Card)
    "kcc": "KCC", "kisan credit card": "KCC", "kisan credit": "KCC",
    "kcc loan": "KCC", "crop loan card": "KCC", "agri credit card": "KCC",

    # 4. NAMO SHETKARI
    "namo shetkari": "NAMO_SHETKARI", "shetkari nidhi": "NAMO_SHETKARI",
    "sanman nidhi": "NAMO_SHETKARI", "namo kisan": "NAMO_SHETKARI",
    "namo yojana": "NAMO_SHETKARI", "namo maha sanman": "NAMO_SHETKARI",

    # 5. MICRO IRRIGATION (Drip / Sprinkler)
    "micro irrigation": "MICRO_IRRIGATION", "drip irrigation": "MICRO_IRRIGATION",
    "drip subsidy": "MICRO_IRRIGATION", "sprinkler": "MICRO_IRRIGATION",
    "thibak": "MICRO_IRRIGATION", "thibak sinchan": "MICRO_IRRIGATION",
    "drip system": "MICRO_IRRIGATION", "pdmc": "MICRO_IRRIGATION",
    "tushar sinchan": "MICRO_IRRIGATION", "sprinkler subsidy": "MICRO_IRRIGATION",

    # 6. SMAM (Farm Mechanization / Tractor)
    "smam": "SMAM", "farm mechanization": "SMAM", "tractor subsidy": "SMAM",
    "tractor": "SMAM", "yantrikikaran": "SMAM", "rotavator": "SMAM",
    "agri machinery": "SMAM", "farm equipment": "SMAM", "krishi yantra": "SMAM",

    # 7. SOLAR PUMP (Magel Tyala Saur Krishi Pump)
    "solar pump": "SOLAR_PUMP", "saur pump": "SOLAR_PUMP",
    "solar krishi pump": "SOLAR_PUMP", "magel tyala saur": "SOLAR_PUMP",
    "pm kusum": "SOLAR_PUMP", "kusum": "SOLAR_PUMP",
    "solar water pump": "SOLAR_PUMP", "saur urja pump": "SOLAR_PUMP",
    "saur urja": "SOLAR_PUMP",

    # 8. FARM POND (Shet Tale)
    "farm pond": "FARM_POND", "shet tale": "FARM_POND", "shettale": "FARM_POND",
    "farm pond subsidy": "FARM_POND", "khet talab": "FARM_POND", "khet talai": "FARM_POND",
    "magel tyala shet tale": "FARM_POND", "magel tyala shettale": "FARM_POND",

    # 9. WELL SUBSIDY
    "well subsidy": "WELL_SUBSIDY", "kuan anudan": "WELL_SUBSIDY",
    "vihar anudan": "WELL_SUBSIDY", "boring subsidy": "WELL_SUBSIDY",
    "vihir anudan": "WELL_SUBSIDY", "new well": "WELL_SUBSIDY",
    "kua": "WELL_SUBSIDY", "kuan": "WELL_SUBSIDY", "vihir": "WELL_SUBSIDY",
    "vhir": "WELL_SUBSIDY", "dug well": "WELL_SUBSIDY", "well repair": "WELL_SUBSIDY",

    # 10. KARJMAFI (Loan Waiver)
    "karjmafi": "KARJMAFI", "loan waiver": "KARJMAFI", "karz mafi": "KARJMAFI",
    "karj mafi": "KARJMAFI", "ahilyadevi": "KARJMAFI", "rin mafi": "KARJMAFI",
    "debt relief": "KARJMAFI", "crop loan waiver": "KARJMAFI",
    "karj mukti": "KARJMAFI", "karz mukti": "KARJMAFI",

    # 11. PKVY (Organic Farming)
    "pkvy": "PKVY", "organic farming": "PKVY", "paramparagat krishi": "PKVY",
    "jaivik kheti": "PKVY", "sendriya sheti": "PKVY", "vermicompost": "PKVY",
    "bio farming": "PKVY", "organic cluster": "PKVY",
}

_SCHEME_ALIASES_DEVA: dict[str, str] = {
    # 1. PM-KISAN
    "पीएम किसान": "PMKISAN", "पीएम-किसान": "PMKISAN", "पीएमकिसान": "PMKISAN",
    "पीम किसान": "PMKISAN", "पीम-किसान": "PMKISAN", "पीज किसान": "PMKISAN",
    "पी.एम. किसान": "PMKISAN", "पी एम किसान": "PMKISAN", "पीएम किसानी": "PMKISAN",
    "किसान योजना": "PMKISAN", "पीएम योजना": "PMKISAN",
    "किसान सम्मान निधि": "PMKISAN", "किसान सन्मान निधी": "PMKISAN",
    "किसान सम्मान": "PMKISAN", "किसान सन्मान": "PMKISAN",
    "पंतप्रधान किसान सन्मान": "PMKISAN", "प्रधानमंत्री किसान सम्मान": "PMKISAN",

    # 2. PMFBY (Crop Insurance)
    "पीएमएफबीवाई": "PMFBY", "पीएमएफबीवाय": "PMFBY", "फसल बीमा": "PMFBY",
    "पीक विमा": "PMFBY", "पीकविमा": "PMFBY", "पंतप्रधान पीक विमा": "PMFBY",
    "प्रधानमंत्री फसल बीमा": "PMFBY", "विमा योजना": "PMFBY", "पीक नुकसान": "PMFBY",
    "फसल नुकसान": "PMFBY",

    # 3. KCC (Kisan Credit Card)
    "केसीसी": "KCC", "के.सी.सी.": "KCC", "किसान क्रेडिट कार्ड": "KCC",
    "किसान क्रेडिट": "KCC", "किसान कार्ड": "KCC", "केसीसी कर्ज": "KCC",

    # 4. NAMO SHETKARI
    "नमो शेतकरी": "NAMO_SHETKARI", "नमो शेतकरी महा सन्मान": "NAMO_SHETKARI",
    "नमो शेतकरी महा सम्मान": "NAMO_SHETKARI", "नमो शेतकरी योजना": "NAMO_SHETKARI",
    "सन्मान निधि": "NAMO_SHETKARI", "सन्मान निधी": "NAMO_SHETKARI",
    "नमो योजना": "NAMO_SHETKARI",

    # 5. MICRO IRRIGATION (Drip / Sprinkler)
    "ठिबक सिंचन": "MICRO_IRRIGATION", "ठिबक": "MICRO_IRRIGATION",
    "तुषार सिंचन": "MICRO_IRRIGATION", "तुषार": "MICRO_IRRIGATION",
    "ड्रिप सिंचाई": "MICRO_IRRIGATION", "ड्रिप": "MICRO_IRRIGATION",
    "सूक्ष्म सिंचाई": "MICRO_IRRIGATION", "सूक्ष्म सिंचन": "MICRO_IRRIGATION",
    "स्प्रिंकलर": "MICRO_IRRIGATION", "ड्रिप अनुदान": "MICRO_IRRIGATION",
    "ठिबक अनुदान": "MICRO_IRRIGATION", "फव्वारा सिंचाई": "MICRO_IRRIGATION",

    # 6. SMAM (Farm Mechanization / Tractor)
    "एसएमएएम": "SMAM", "कृषि यंत्रीकरण": "SMAM", "कृषी यांत्रिकीकरण": "SMAM",
    "यंत्रीकरण": "SMAM", "यांत्रिकीकरण": "SMAM", "ट्रॅक्टर": "SMAM",
    "ट्रैक्टर": "SMAM", "कृषि यंत्र": "SMAM", "कृषी अवजारे": "SMAM",
    "अवजार अनुदान": "SMAM", "ट्रॅक्टर अनुदान": "SMAM", "ट्रैक्टर अनुदान": "SMAM",
    "ट्रॅक्टर योजना": "SMAM", "ट्रैक्टर योजना": "SMAM", "रोटाव्हेटर": "SMAM",
    "रोटावेटर": "SMAM",

    # 7. SOLAR PUMP
    "सौर कृषी पंप": "SOLAR_PUMP", "सौर कृषि पंप": "SOLAR_PUMP",
    "सोलर पंप": "SOLAR_PUMP", "सौर पंप": "SOLAR_PUMP",
    "सोलर कृषी पंप": "SOLAR_PUMP", "सोलर कृषि पंप": "SOLAR_PUMP",
    "मागेल त्याला सौर": "SOLAR_PUMP", "कुसुम योजना": "SOLAR_PUMP",
    "पीएम कुसुम": "SOLAR_PUMP", "सौर ऊर्जा पंप": "SOLAR_PUMP",
    "सौर ऊर्जा": "SOLAR_PUMP", "सोलर योजना": "SOLAR_PUMP",

    # 8. FARM POND (Shet Tale)
    "शेततळे": "FARM_POND", "शेत तळे": "FARM_POND",
    "खेत तालाब": "FARM_POND", "खेत तलाई": "FARM_POND",
    "फार्म पॉन्ड": "FARM_POND", "शेततळे अनुदान": "FARM_POND",
    "मागेल त्याला शेततळे": "FARM_POND", "मागेल त्याला शेत तळे": "FARM_POND",

    # 9. WELL SUBSIDY
    "विहीर अनुदान": "WELL_SUBSIDY", "विहीर": "WELL_SUBSIDY",
    "विहिरीसाठी": "WELL_SUBSIDY", "नवीन विहीर": "WELL_SUBSIDY",
    "विहीर दुरुस्ती": "WELL_SUBSIDY", "इनवेल बोअरिंग": "WELL_SUBSIDY",
    "कुआं अनुदान": "WELL_SUBSIDY", "कुआं": "WELL_SUBSIDY",
    "कुएं": "WELL_SUBSIDY", "कूप निर्माण": "WELL_SUBSIDY",
    "बोरिंग अनुदान": "WELL_SUBSIDY", "विहीर योजना": "WELL_SUBSIDY",

    # 10. KARJMAFI
    "कर्जमाफी": "KARJMAFI", "कर्ज माफी": "KARJMAFI", "कर्ज माफ": "KARJMAFI",
    "ऋण माफी": "KARJMAFI", "अहिल्यादेवी": "KARJMAFI", "पीक कर्ज माफी": "KARJMAFI",
    "शेतकरी कर्जमाफी": "KARJMAFI", "कर्जमुक्ती": "KARJMAFI", "कर्ज मुक्ती": "KARJMAFI",

    # 11. PKVY (Organic Farming)
    "पीकेवीवाई": "PKVY", "पीकेव्हीवाय": "PKVY",
    "परंपरागत कृषि": "PKVY", "परंपरागत कृषी": "PKVY",
    "जैविक खेती": "PKVY", "सेंद्रिय शेती": "PKVY",
    "सेंद्रिय प्रमाणन": "PKVY", "जैविक प्रमाणन": "PKVY",
    "गांडूळ खत": "PKVY", "जीवामृत": "PKVY", "नैसर्गिक शेती": "PKVY",
    "सेंद्रिय": "PKVY", "जैविक": "PKVY",
}


def _alias_lookup(query: str) -> str | None:
    """Return scheme_id if a known alias matches in the query, else None.
    Checks longest aliases first to avoid partial mismatches."""
    import unicodedata
    q = unicodedata.normalize("NFKC", query.strip().replace("\u093c", ""))
    q_lower = q.lower()
    # Check Devanagari aliases (exact substring after NFKC and nukta strip)
    for alias, sid in sorted(_SCHEME_ALIASES_DEVA.items(), key=lambda x: len(x[0]), reverse=True):
        a_norm = unicodedata.normalize("NFKC", alias.replace("\u093c", ""))
        if a_norm in q:
            return sid
    # Check Latin aliases (lowercase)
    for alias, sid in sorted(_SCHEME_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in q_lower:
            return sid
    return None


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
        greeting_msg = greeting_msgs.get(lang, greeting_msgs["en"])
        return ChatResponse(
            found=True,
            type="greeting",
            message=greeting_msg,
            speech_text=voice_utils.simplify_for_speech(greeting_msg),
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
                application_status=scheme.get("application_status", "open"),
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

    # 3. 'All schemes' / 'List schemes' / 'What am I eligible for' overview intent check
    _alias_match = _alias_lookup(body.query)

    _scheme_words = {
        "scheme", "schemes", "yojana", "योजना", "योजनाएं", "योजनांसाठी", "योजनेसाठी",
        "योजनांना", "स्कीम", "स्कीमसाठी", "स्कीम्स"
    }
    _eligible_words = {
        "eligible", "qualify", "patra", "पात्र", "पात्रता", "एलिजिबल",
        "मिलेगा", "मिळेल", "मिळतील", "लागू", "milega"
    }
    _which_words = {
        "which", "what", "any", "konti", "konte", "कोणती", "कोणत्या", "कोणते",
        "कोणत्याही", "कोणत्या-कोणत्या", "कौन", "कौनसी", "कौन-सी", "कौन सी", "किस", "किन"
    }
    _query_words = set(raw_query.replace("?", "").replace("!", "").replace(",", "").split())

    # If an exact specific scheme was mentioned (e.g. "PM-KISAN", "KCC"), it is NOT an all-schemes query
    is_all_schemes = (_alias_match is None) and (
        any(k in raw_query for k in ALL_SCHEMES_KEYWORDS)
        or (({"all", "every", "list"} & _query_words) and ("scheme" in raw_query or "yojana" in raw_query or "स्कीम" in raw_query))
        # Pattern: "eligible" + "scheme/yojana" + "which/what" — "what scheme am I eligible for" / "कोणत्या स्कीमसाठी एलिजिबल"
        or bool(_eligible_words & _query_words and _scheme_words & _query_words and _which_words & _query_words)
        # Pattern: "eligible" + "which/what/konti/konte/कौन"
        or bool(_eligible_words & _query_words and _which_words & _query_words)
        # Pattern: "which/what" + "scheme/yojana" — "which schemes can I get"
        or bool(_which_words & _query_words and _scheme_words & _query_words)
        # Marathi combos
        or (("सर्व" in raw_query or "सगळ्या" in raw_query or "कोणती" in raw_query or "कोणत्या" in raw_query) and ("योजना" in raw_query or "स्कीम" in raw_query))
        or ("माझ्यासाठी" in raw_query and ("सर्व" in raw_query or "कोणती" in raw_query or "कोणत्या" in raw_query or "पात्र" in raw_query))
        or ("मी" in raw_query and ("कोणत्या" in raw_query or "कशासाठी" in raw_query) and ("पात्र" in raw_query or "एलिजिबल" in raw_query))
        # Hindi combos
        or (("सभी" in raw_query or "सारे" in raw_query or "सूची" in raw_query or "कौन सी" in raw_query or "किस" in raw_query) and ("योजना" in raw_query or "स्कीम" in raw_query))
        or ("मेरे लिए" in raw_query and ("सभी" in raw_query or "कौन सी" in raw_query or "पात्र" in raw_query))
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
                note=eval_res["note"],
                application_status=scheme.get("application_status", "open"),
            ))

        # Sort eligible first
        scheme_items.sort(key=lambda x: (0 if x.eligible else 1, x.name))
        eligible_count = sum(1 for s in scheme_items if s.eligible)

        intro_msgs = {
            "en": f"Here is the complete overview of all {len(scheme_items)} Maharashtra & Central Government schemes. Based on your current farm profile, you are eligible for {eligible_count} schemes:",
            "hi": f"यहाँ महाराष्ट्र और केंद्र सरकार की सभी {len(scheme_items)} योजनाओं का विवरण है। आपकी वर्तमान प्रोफ़ाइल के अनुसार, आप {eligible_count} योजनाओं के लिए पात्र हैं:",
            "mr": f"येथे महाराष्ट्र व केंद्र शासनाच्या सर्व {len(scheme_items)} योजनांची संपूर्ण माहिती आहे. तुमच्या सध्याच्या प्रोफाइलनुसार, तुम्ही {eligible_count} योजनांसाठी पात्र आहात:"
        }

        speech_t = voice_utils.build_speech_text(
            "all_schemes",
            {
                "message": intro_msgs.get(lang, intro_msgs["en"]),
                "schemes": [s.model_dump() for s in scheme_items],
            },
            lang=lang,
        )
        return ChatResponse(
            found=True,
            type="all_schemes",
            message=intro_msgs.get(lang, intro_msgs["en"]),
            schemes=scheme_items,
            speech_text=speech_t,
        )



    # 4. Specific Scheme RAG Semantic Search
    # 4a. Try keyword alias lookup first (handles Hindi/Marathi transliterations)
    alias_scheme_id = _alias_lookup(body.query)
    if alias_scheme_id and alias_scheme_id in scheme_map:
        scheme = scheme_map[alias_scheme_id]
        result = eligibility.evaluate(alias_scheme_id, body.profile)
        conversational_answer = qa_engine.synthesize_answer(
            query=body.query, scheme=scheme, profile=body.profile,
            eval_result=result, lang=lang,
            application_status=scheme.get("application_status", "open"),
        )
        speech_t = voice_utils.build_speech_text(
            "scheme",
            {"message": conversational_answer, "eligible": result["eligible"], "note": result["note"]},
            lang=lang,
        )
        return ChatResponse(
            found=True, type="scheme",
            message=conversational_answer,
            speech_text=speech_t,
            scheme_id=alias_scheme_id,
            scheme_name=scheme.get("scheme_name"),
            eligible=result["eligible"],
            note=result["note"],
            benefit=scheme.get("benefit_text"),
            documents=scheme.get("documents_required"),
            link=scheme.get("official_link"),
            score=1.0,
            application_status=scheme.get("application_status", "open"),
        )

    # 4b. Fall back to FAISS semantic search
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
    scheme:     dict[str, Any] = scheme_map.get(scheme_id, best_entry.get("original_scheme", {}))

    # Apply eligibility rule
    result = eligibility.evaluate(scheme_id, body.profile)

    # Synthesize plain-language direct answer
    conversational_answer = qa_engine.synthesize_answer(
        query=body.query,
        scheme=scheme,
        profile=body.profile,
        eval_result=result,
        lang=lang,
        application_status=scheme.get("application_status", "open"),
    )

    speech_t = voice_utils.build_speech_text(
        "scheme",
        {"message": conversational_answer, "eligible": result["eligible"], "note": result["note"]},
        lang=lang,
    )
    return ChatResponse(
        found=True,
        type="scheme",
        message=conversational_answer,
        speech_text=speech_t,
        scheme_id=scheme_id,
        scheme_name=scheme.get("scheme_name"),
        eligible=result["eligible"],
        note=result["note"],
        benefit=scheme.get("benefit_text"),
        documents=scheme.get("documents_required"),
        link=scheme.get("official_link"),
        score=best_score,
        application_status=scheme.get("application_status", "open"),
    )

# ---------------------------------------------------------------------------
# Voice / AI chat endpoints
# ---------------------------------------------------------------------------

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


@app.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(body: AIChatRequest):
    _require_ai()
    try:
        analysis = ai_engine.analyze_query(body.message, body.language)
        faiss_results = None
        if analysis.get("intent") in ("scheme_query", "eligibility_check"):
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
            except Exception:
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
                    query=body.message, language=body.language,
                    crop=analysis.get("crop"), use_test=False,
                )
            except Exception:
                agri_kb_results = None

        context = ai_engine.gather_context(analysis, body.profile, faiss_results, agri_kb_results)
        result = ai_engine.generate_response(body.message, analysis, context, body.profile, agri_kb_results)
        speech_text = voice_utils.simplify_ai_response(result["answer"], result["language"])

        return AIChatResponse(
            answer=result["answer"], language=result["language"],
            intent=result["intent"], sources=result["sources"],
            grounded=result["grounded"], analysis=result.get("analysis"),
            speech_text=speech_text,
        )
    except stt_tts.ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except stt_tts.ExternalAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        logger.exception("AI chat failed")
        raise HTTPException(status_code=500, detail="AI processing failed. Please try again.")


@app.post("/ai/transcribe", response_model=AITranscribeResponse)
async def ai_transcribe(file: UploadFile = File(...)):
    _require_ai()
    ctype = (file.content_type or "").lower()
    if ctype and not ctype.startswith("audio/"):
        raise HTTPException(status_code=422, detail=f"Expected audio file, received: {ctype}")
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Empty audio file.")
    if len(audio_bytes) > stt_tts.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"Audio too large. Max {stt_tts.MAX_AUDIO_SIZE_BYTES // (1024*1024)} MB.")
    try:
        text, lang = stt_tts.transcribe_audio(audio_bytes, filename=file.filename or "audio.webm")
        return AITranscribeResponse(text=text, language=lang)
    except stt_tts.ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except stt_tts.ExternalAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed.")


@app.post("/ai/speak")
def ai_speak(body: AISpeakRequest):
    """TTS endpoint. Marathi uses gTTS (free). EN/HI uses OpenAI TTS."""
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="Text cannot be empty.")
    try:
        audio_bytes = stt_tts.synthesize_speech(body.text, body.language, body.voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except stt_tts.ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except stt_tts.ExternalAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")

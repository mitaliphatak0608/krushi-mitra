from typing import Any
import backend.database as db

# In-memory store for demo (cache)
_sms_sessions: dict[str, dict[str, Any]] = {}

def get_session(phone: str) -> dict[str, Any]:
    session = db.get_sms_session(phone)
    if not session:
        session = {"state": "INIT", "language": "en", "profile": {}, "recommended_schemes": [], "focused_scheme_id": None}
        db.save_sms_session(phone, session)
    
    # Update cache
    _sms_sessions[phone] = session
    return session

def update_session(phone: str, state: str, language: str = None, profile: dict[str, Any] = None, recommended_schemes: list = None, focused_scheme_id: str = None, **kwargs):
    session = get_session(phone)
    session["state"] = state
    if language is not None:
        session["language"] = language
    if profile is not None:
        session["profile"] = profile
    if recommended_schemes is not None:
        session["recommended_schemes"] = recommended_schemes
    if focused_scheme_id is not None:
        session["focused_scheme_id"] = focused_scheme_id
    for k, v in kwargs.items():
        session[k] = v
        
    _sms_sessions[phone] = session
    db.save_sms_session(phone, session)

def reset_session(phone: str, language: str = "en"):
    session = {"state": "INIT", "language": language, "profile": {}, "recommended_schemes": [], "focused_scheme_id": None}
    _sms_sessions[phone] = session
    db.save_sms_session(phone, session)

def stop_session(phone: str):
    session = get_session(phone)
    lang = session.get("language", "en")
    new_session = {"state": "STOPPED", "language": lang, "profile": {}, "recommended_schemes": [], "focused_scheme_id": None}
    _sms_sessions[phone] = new_session
    db.save_sms_session(phone, new_session)

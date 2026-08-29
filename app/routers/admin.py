"""Admin router - manage schemes and metadata."""
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT_DIR / "data" / "schemes_content.json"

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Load schemes at module import
with DATA_FILE.open(encoding="utf-8") as f:
    SCHEMES: list[dict[str, Any]] = json.load(f)


class SchemeUpdate(BaseModel):
    scheme_id: str
    updates: dict[str, Any]


@router.get("/schemes", response_model=list[dict[str, Any]])
def admin_list_schemes() -> list[dict[str, Any]]:
    """Admin endpoint to list all schemes with full details."""
    return SCHEMES


@router.post("/schemes/update")
def update_scheme(update: SchemeUpdate) -> dict[str, Any]:
    """Update a scheme (admin only)."""
    for scheme in SCHEMES:
        if scheme.get("scheme_id") == update.scheme_id:
            scheme.update(update.updates)
            # In production, persist to disk
            return {"status": "updated", "scheme_id": update.scheme_id}
    return {"status": "error", "message": "Scheme not found"}

"""Schemes router - list and retrieve schemes."""
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT_DIR / "data" / "schemes_content.json"

router = APIRouter(prefix="/api/schemes", tags=["schemes"])

# Load schemes at module import
with DATA_FILE.open(encoding="utf-8") as f:
    SCHEMES: list[dict[str, Any]] = json.load(f)


@router.get("", response_model=list[dict[str, Any]])
def list_schemes() -> list[dict[str, Any]]:
    """Return all schemes."""
    return SCHEMES


@router.get("/{scheme_id}", response_model=dict[str, Any])
def get_scheme(scheme_id: str) -> dict[str, Any]:
    """Retrieve a single scheme by ID."""
    for scheme in SCHEMES:
        if scheme.get("scheme_id") == scheme_id:
            return scheme
    return {"error": "Scheme not found"}

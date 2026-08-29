"""Eligibility router - check farmer eligibility for schemes."""
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[2]
ELIGIBILITY_RULES_FILE = ROOT_DIR / "data" / "eligibility_rules.json"

router = APIRouter(prefix="/api/eligibility", tags=["eligibility"])

# Load eligibility rules at module import
with ELIGIBILITY_RULES_FILE.open(encoding="utf-8") as f:
    ELIGIBILITY_RULES: dict[str, Any] = json.load(f)


class EligibilityCheckRequest(BaseModel):
    scheme_id: str
    farmer_data: dict[str, Any]


class EligibilityCheckResponse(BaseModel):
    scheme_id: str
    eligible: bool
    reason: str


@router.post("/check", response_model=EligibilityCheckResponse)
def check_eligibility(req: EligibilityCheckRequest) -> EligibilityCheckResponse:
    """Check if a farmer is eligible for a scheme."""
    scheme_id = req.scheme_id
    if scheme_id not in ELIGIBILITY_RULES:
        return EligibilityCheckResponse(
            scheme_id=scheme_id,
            eligible=False,
            reason="Scheme eligibility rules not found"
        )
    
    # Placeholder: actual eligibility logic would go here
    return EligibilityCheckResponse(
        scheme_id=scheme_id,
        eligible=True,
        reason="Eligibility check passed (placeholder)"
    )

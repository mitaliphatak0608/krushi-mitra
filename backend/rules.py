"""
backend/rules.py
================
Single Source of Truth for Scheme Eligibility Rules.

Evaluates farmer profiles against all 11 central and state agricultural schemes.
Robustly supports:
- camelCase (isTaxPayer, isOrganic, hasOutstandingLoan, cropSeason, landholding, primaryCrop)
- snake_case (is_tax_payer, is_organic, has_outstanding_loan, crop_season, land_holding, primary_crop)
- Boolean (True/False) and String ("Yes"/"No", "True"/"False", "होय", "हाँ") values.
"""

from typing import Any


def _is_truthy(p: dict[str, Any], *keys: str) -> bool:
    """Checks if any of the given keys in profile p represent a truthy/Yes value."""
    for k in keys:
        if k in p:
            val = p[k]
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return val > 0
            if isinstance(val, str):
                cleaned = val.strip().lower()
                if cleaned in ("yes", "true", "1", "y", "t", "होय", "हाँ"):
                    return True
                if cleaned in ("no", "false", "0", "n", "f", "नाही", "नहीं"):
                    return False
    return False


def _get_float(p: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    """Extracts a float value for the first matching key."""
    for k in keys:
        if k in p and p[k] is not None:
            try:
                return float(p[k])
            except (ValueError, TypeError):
                pass
    return default


def _get_str(p: dict[str, Any], *keys: str, default: str = "") -> str:
    """Extracts a string value for the first matching key."""
    for k in keys:
        if k in p and p[k] is not None:
            return str(p[k]).strip()
    return default


# ---------------------------------------------------------------------------
# Individual Scheme Rule Functions
# ---------------------------------------------------------------------------

def _pmkisan(p: dict[str, Any]) -> dict[str, Any]:
    if _is_truthy(p, "isTaxPayer", "is_tax_payer", "is_taxpayer", "taxPayer"):
        return {"eligible": False, "note": "Income tax payers are excluded from PM-KISAN."}
    return {"eligible": True, "note": "Direct benefit transfer of ₹6,000/year to Aadhaar-linked bank account."}


def _namo_shetkari(p: dict[str, Any]) -> dict[str, Any]:
    if _is_truthy(p, "isTaxPayer", "is_tax_payer", "is_taxpayer", "taxPayer"):
        return {"eligible": False, "note": "Requires active PM-KISAN eligibility (income tax payers excluded)."}
    return {"eligible": True, "note": "Maharashtra state top-up of ₹6,000/year paired with PM-KISAN."}


def _pmfby(p: dict[str, Any]) -> dict[str, Any]:
    valid_seasons = {"Kharif", "Rabi", "Annual Commercial"}
    season = _get_str(p, "cropSeason", "crop_season", "season", default="Kharif")
    if season not in valid_seasons:
        return {"eligible": False, "note": f"Crop season '{season}' is not notified for PMFBY insurance."}
    caps = {"Kharif": "2%", "Rabi": "1.5%", "Annual Commercial": "5%"}
    return {"eligible": True, "note": f"Farmer premium capped at {caps.get(season, '2%')} for {season} crops."}


def _micro_irrigation(p: dict[str, Any]) -> dict[str, Any]:
    land = _get_float(p, "landholding", "land_holding", "land", "land_size", default=0.0)
    if land <= 0 or land > 5:
        return {"eligible": False, "note": "Landholding must be between 0 and 5 ha for micro-irrigation subsidy."}
    subsidy = 80 if land <= 1 else 70
    region = _get_str(p, "region", "farming_region", "district", default="")
    if region in ("Marathwada", "Vidarbha"):
        subsidy += 10
    return {"eligible": True, "note": f"{subsidy}% subsidy on drip/sprinkler system for {region or 'your farm'}."}


def _solar_pump(p: dict[str, Any]) -> dict[str, Any]:
    category = _get_str(p, "category", "social_category", "caste_category", default="General")
    share = "5%" if category.upper() in ("SC", "ST") else "10%"
    return {"eligible": True, "note": f"Beneficiary contribution is only {share} ({category} category). Rest subsidized by state."}


def _well_subsidy(p: dict[str, Any]) -> dict[str, Any]:
    land = _get_float(p, "landholding", "land_holding", "land", default=0.0)
    if land < 0.4 or land > 6:
        return {"eligible": False, "note": "Requires landholding between 0.4 ha and 6 ha."}
    return {"eligible": True, "note": "Eligible — up to ₹4,00,000 for new well; ₹1,00,000 for repair (Boja-free land required)."}


def _kcc(p: dict[str, Any]) -> dict[str, Any]:
    crop = _get_str(p, "primaryCrop", "primary_crop", "crop", default="crops")
    return {"eligible": True, "note": f"Short-term crop credit at 4% effective interest for {crop}."}


def _karjmafi(p: dict[str, Any]) -> dict[str, Any]:
    if not _is_truthy(p, "hasOutstandingLoan", "has_outstanding_loan", "outstandingLoan", "hasLoan", "loan"):
        return {"eligible": False, "note": "Requires an active outstanding institutional crop loan."}
    return {"eligible": True, "note": "Eligible for consideration under the current debt-relief cycle."}


def _pkvy(p: dict[str, Any]) -> dict[str, Any]:
    if not _is_truthy(p, "isOrganic", "is_organic", "organic", "organicFarming", "organic_practice"):
        return {"eligible": False, "note": "Only applicable for certified organic farming clusters."}
    return {"eligible": True, "note": "₹50,000/ha grant for organic inputs, vermicompost & PGS certification (3-year cluster)."}


def _smam(p: dict[str, Any]) -> dict[str, Any]:
    return {"eligible": True, "note": "First-come-first-served subsidy up to ₹1,00,000 on tractors & power tillers via MahaDBT."}


def _farm_pond(p: dict[str, Any]) -> dict[str, Any]:
    land = _get_float(p, "landholding", "land_holding", "land", default=0.0)
    if land < 0.4:
        return {"eligible": False, "note": "Minimum 0.4 ha landholding required for farm pond construction."}
    return {"eligible": True, "note": "Subsidy for on-farm water storage pond construction to support irrigation."}


# ---------------------------------------------------------------------------
# Public registry — keyed by scheme_id
# ---------------------------------------------------------------------------
RULES: dict[str, Any] = {
    "PMKISAN":          _pmkisan,
    "NAMO_SHETKARI":    _namo_shetkari,
    "PMFBY":            _pmfby,
    "MICRO_IRRIGATION": _micro_irrigation,
    "SOLAR_PUMP":       _solar_pump,
    "WELL_SUBSIDY":     _well_subsidy,
    "KCC":              _kcc,
    "KARJMAFI":         _karjmafi,
    "PKVY":             _pkvy,
    "SMAM":             _smam,
    "FARM_POND":        _farm_pond,
}


def evaluate(scheme_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    """
    Apply the eligibility rule for *scheme_id* against *profile*.

    Returns { "eligible": bool, "note": str }.
    If no rule is registered for the scheme, defaults to eligible=True.
    """
    rule_fn = RULES.get(scheme_id)
    if rule_fn is None:
        return {"eligible": True, "note": "No specific eligibility rule — consult your local CSC for details."}
    return rule_fn(profile)

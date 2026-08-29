import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend import rules

print("=" * 65)
print("  Krushi Mitra — Eligibility Rules Field Compatibility Tests")
print("=" * 65)

# Test 1: PM-KISAN with camelCase vs snake_case vs boolean
assert rules.evaluate("PMKISAN", {"isTaxPayer": "Yes"})["eligible"] is False
assert rules.evaluate("PMKISAN", {"is_tax_payer": "Yes"})["eligible"] is False
assert rules.evaluate("PMKISAN", {"is_tax_payer": True})["eligible"] is False
assert rules.evaluate("PMKISAN", {"isTaxPayer": "No"})["eligible"] is True
assert rules.evaluate("PMKISAN", {"is_tax_payer": False})["eligible"] is True
print("[PASS] PM-KISAN tax payer exclusion works with isTaxPayer & is_tax_payer (string + bool)")

# Test 2: NAMO_SHETKARI tax payer exclusion
assert rules.evaluate("NAMO_SHETKARI", {"isTaxPayer": "Yes"})["eligible"] is False
assert rules.evaluate("NAMO_SHETKARI", {"is_tax_payer": True})["eligible"] is False
assert rules.evaluate("NAMO_SHETKARI", {"isTaxPayer": "No"})["eligible"] is True
print("[PASS] NAMO_SHETKARI tax payer exclusion works with isTaxPayer & is_tax_payer")

# Test 3: PKVY Organic farming requirement
assert rules.evaluate("PKVY", {"isOrganic": "No"})["eligible"] is False
assert rules.evaluate("PKVY", {"is_organic": False})["eligible"] is False
assert rules.evaluate("PKVY", {})["eligible"] is False  # default missing is not organic
assert rules.evaluate("PKVY", {"isOrganic": "Yes"})["eligible"] is True
assert rules.evaluate("PKVY", {"is_organic": True})["eligible"] is True
print("[PASS] PKVY organic requirement works with isOrganic & is_organic (string + bool)")

# Test 4: KARJMAFI loan requirement
assert rules.evaluate("KARJMAFI", {"hasOutstandingLoan": "No"})["eligible"] is False
assert rules.evaluate("KARJMAFI", {"has_outstanding_loan": False})["eligible"] is False
assert rules.evaluate("KARJMAFI", {})["eligible"] is False  # default missing has no loan
assert rules.evaluate("KARJMAFI", {"hasOutstandingLoan": "Yes"})["eligible"] is True
assert rules.evaluate("KARJMAFI", {"has_outstanding_loan": True})["eligible"] is True
print("[PASS] KARJMAFI loan requirement works with hasOutstandingLoan & has_outstanding_loan")

# Test 5: MICRO_IRRIGATION land & regional bonus
assert rules.evaluate("MICRO_IRRIGATION", {"landholding": 0.8, "region": "Marathwada"})["eligible"] is True
assert "90%" in rules.evaluate("MICRO_IRRIGATION", {"land_holding": 0.8, "region": "Marathwada"})["note"]
assert "80%" in rules.evaluate("MICRO_IRRIGATION", {"landholding": 1.5, "region": "Vidarbha"})["note"]
assert "70%" in rules.evaluate("MICRO_IRRIGATION", {"landholding": 1.5, "region": "Western Maharashtra"})["note"]
assert rules.evaluate("MICRO_IRRIGATION", {"landholding": 6.0})["eligible"] is False
print("[PASS] MICRO_IRRIGATION calculation & regional bonus verified")

# Test 6: SOLAR_PUMP category share
assert "5%" in rules.evaluate("SOLAR_PUMP", {"category": "SC"})["note"]
assert "5%" in rules.evaluate("SOLAR_PUMP", {"social_category": "ST"})["note"]
assert "10%" in rules.evaluate("SOLAR_PUMP", {"category": "General"})["note"]
assert "10%" in rules.evaluate("SOLAR_PUMP", {"category": "OBC"})["note"]
print("[PASS] SOLAR_PUMP category contribution verified")

print("\n" + "=" * 65)
print("  All Eligibility Field Compatibility Tests Passed!")
print("=" * 65)


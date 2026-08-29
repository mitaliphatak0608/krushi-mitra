"""
Automated unit & integration tests for Krushi Mitra Authentication & User DB.
Uses FastAPI TestClient to test endpoints and SQLite database in-memory/in-place.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from backend.main import app, ADMIN_KEY
from backend import database

client = TestClient(app)

print("=" * 65)
print("  Krushi Mitra — Authentication & Database Verification")
print("=" * 65)

# Test 1: User Registration
print("\n[Test 1] User Registration")
reg_payload = {
    "name": "Ramesh Patil",
    "email": "ramesh.patil@example.com",
    "password": "strongPassword123",
    "role": "farmer"
}
res = client.post("/auth/register", json=reg_payload)
if res.status_code == 400 and "already exists" in res.text:
    print("  User already exists from previous run, proceeding to login...")
else:
    assert res.status_code == 200, f"Registration failed: {res.text}"
    data = res.json()
    assert "token" in data, "Token missing in register response"
    assert data["user"]["email"] == "ramesh.patil@example.com"
    assert data["user"]["name"] == "Ramesh Patil"
    assert data["user"]["role"] == "farmer"
    assert data["profile"]["name"] == "Ramesh Patil"
    print(f"  Registered: {data['user']['name']} ({data['user']['email']})")
print("  [PASS]")

# Test 2: Duplicate Registration Check
print("\n[Test 2] Duplicate Email Prevention")
res_dup = client.post("/auth/register", json=reg_payload)
assert res_dup.status_code == 400, f"Expected 400 for duplicate, got {res_dup.status_code}"
assert "already exists" in res_dup.json()["detail"]
print("  Duplicate email rejected with HTTP 400 Bad Request")
print("  [PASS]")

# Test 3: Login with Wrong Password
print("\n[Test 3] Login With Incorrect Password")
res_wrong = client.post("/auth/login", json={
    "email": "ramesh.patil@example.com",
    "password": "wrongPasswordXYZ",
    "role": "farmer"
})
assert res_wrong.status_code == 401, f"Expected 401, got {res_wrong.status_code}"
print("  Incorrect password rejected with HTTP 401 Unauthorized")
print("  [PASS]")

# Test 4: Login with Correct Password
print("\n[Test 4] Login With Correct Password")
res_login = client.post("/auth/login", json={
    "email": "ramesh.patil@example.com",
    "password": "strongPassword123",
    "role": "farmer"
})
assert res_login.status_code == 200, f"Login failed: {res_login.text}"
auth_data = res_login.json()
token = auth_data["token"]
assert token, "JWT token missing"
assert auth_data["user"]["email"] == "ramesh.patil@example.com"
print(f"  Login successful. Received JWT: {token[:20]}...")
print("  [PASS]")

# Test 5: Fetch Profile via /auth/me (Protected Route)
print("\n[Test 5] Fetch /auth/me with Bearer Token")
res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
assert res_me.status_code == 200, f"/auth/me failed: {res_me.text}"
me_data = res_me.json()
assert me_data["user"]["email"] == "ramesh.patil@example.com"
assert "profile" in me_data
print(f"  Profile loaded: region={me_data['profile'].get('region')}, landholding={me_data['profile'].get('landholding')}")
print("  [PASS]")

# Test 6: Update Profile via /profile (Persistence Check)
print("\n[Test 6] Update Profile & Verify SQLite Persistence")
updated_profile = me_data["profile"].copy()
updated_profile["landholding"] = 2.75
updated_profile["region"] = "Vidarbha"
updated_profile["category"] = "OBC"

res_update = client.put("/profile", json={"profile": updated_profile}, headers={"Authorization": f"Bearer {token}"})
assert res_update.status_code == 200, f"Profile update failed: {res_update.text}"

# Verify updated profile is fetched from DB
res_me_updated = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
assert res_me_updated.status_code == 200
reloaded_profile = res_me_updated.json()["profile"]
assert reloaded_profile["landholding"] == 2.75, f"Expected 2.75, got {reloaded_profile['landholding']}"
assert reloaded_profile["region"] == "Vidarbha", f"Expected Vidarbha, got {reloaded_profile['region']}"
assert reloaded_profile["category"] == "OBC", f"Expected OBC, got {reloaded_profile['category']}"
print(f"  Updated and re-verified: landholding={reloaded_profile['landholding']} ha, region={reloaded_profile['region']}")
print("  [PASS]")

# Test 7: Admin Verification
print("\n[Test 7] Admin Key Validation (Reject wrong key, accept valid key)")
res_admin_bad = client.post("/auth/register", json={
    "name": "Admin User",
    "email": "admin@example.com",
    "password": "adminPassword123",
    "role": "admin",
    "adminKey": "WRONG_KEY"
})
assert res_admin_bad.status_code == 403, f"Expected 403, got {res_admin_bad.status_code}"

res_admin_good = client.post("/auth/register", json={
    "name": "Admin Officer",
    "email": "admin.officer@krushimitra.gov.in",
    "password": "adminPassword123",
    "role": "admin",
    "adminKey": ADMIN_KEY or "KRUSHI-ADMIN-2026"
})
if res_admin_good.status_code == 400 and "already exists" in res_admin_good.text:
    print("  Admin already registered in previous run, login test...")
    res_admin_login = client.post("/auth/login", json={
        "email": "admin.officer@krushimitra.gov.in",
        "password": "adminPassword123",
        "role": "admin",
        "adminKey": ADMIN_KEY or "KRUSHI-ADMIN-2026"
    })
    assert res_admin_login.status_code == 200
    assert res_admin_login.json()["user"]["role"] == "admin"
else:
    assert res_admin_good.status_code == 200
    assert res_admin_good.json()["user"]["role"] == "admin"
print("  Admin key authentication verified")
print("  [PASS]")

print("\n" + "=" * 65)
print("  All 7 Authentication & Database Tests Passed!")
print("=" * 65)


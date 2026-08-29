import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent / "users.db"

DEFAULT_PROFILE = {
    "name": "Farmer",
    "location": "Chhatrapati Sambhajinagar",
    "region": "Marathwada",
    "category": "General",
    "landholding": 1.5,
    "language": "English",
    "annualIncome": 120000,
    "isTaxPayer": "No",
    "hasOutstandingLoan": "Yes",
    "cropSeason": "Kharif",
    "primaryCrop": "Cotton & Soybean",
    "isOrganic": "No",
}


def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes the database schema if it doesn't already exist."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'farmer',
                profile_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()


def create_user(
    name: str,
    email: str,
    password_hash: str,
    salt: str,
    role: str = "farmer",
    profile_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Creates a new user record and returns user dict (without sensitive fields)."""
    if profile_data is None:
        profile = DEFAULT_PROFILE.copy()
        profile["name"] = name
    else:
        profile = profile_data

    profile_json = json.dumps(profile, ensure_ascii=False)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, salt, role, profile_data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name.strip(), email.strip().lower(), password_hash, salt, role, profile_json),
        )
        user_id = cursor.lastrowid
        conn.commit()

    return {
        "id": user_id,
        "name": name.strip(),
        "email": email.strip().lower(),
        "role": role,
        "profile": profile,
    }


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    """Fetches full user record including password hash and salt for verification."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        )
        row = cursor.fetchone()
        if not row:
            return None

        user_dict = dict(row)
        try:
            user_dict["profile"] = json.loads(user_dict["profile_data"])
        except Exception:
            user_dict["profile"] = DEFAULT_PROFILE.copy()
        return user_dict


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    """Fetches user record by ID (excluding password hash and salt)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, role, profile_data, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        user_dict = dict(row)
        try:
            user_dict["profile"] = json.loads(user_dict["profile_data"])
        except Exception:
            user_dict["profile"] = DEFAULT_PROFILE.copy()
        del user_dict["profile_data"]
        return user_dict


def update_user_profile(user_id: int, profile_data: dict[str, Any]) -> bool:
    """Updates the user's profile JSON and updates the top-level name if provided."""
    profile_json = json.dumps(profile_data, ensure_ascii=False)
    name = profile_data.get("name")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if name:
            cursor.execute(
                "UPDATE users SET profile_data = ?, name = ? WHERE id = ?",
                (profile_json, name.strip(), user_id),
            )
        else:
            cursor.execute(
                "UPDATE users SET profile_data = ? WHERE id = ?",
                (profile_json, user_id),
            )
        conn.commit()
        return cursor.rowcount > 0


def get_all_users() -> list[dict[str, Any]]:
    """Returns list of all users and profiles for admin inspection (excluding sensitive fields)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, role, profile_data, created_at FROM users ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            u = dict(row)
            try:
                u["profile"] = json.loads(u["profile_data"])
            except Exception:
                u["profile"] = DEFAULT_PROFILE.copy()
            del u["profile_data"]
            results.append(u)
        return results


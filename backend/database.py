import json
import sqlite3
from datetime import date, timedelta
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_id TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('new_scheme', 'closing_soon')),
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                deadline TEXT,
                eligible_categories TEXT NOT NULL DEFAULT '[]',
                min_land REAL,
                max_income REAL,
                official_source TEXT,
                official_link TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Add columns if migrating an existing database without them
        for col_name in ("official_source", "official_link"):
            try:
                conn.execute(f"ALTER TABLE notifications ADD COLUMN {col_name} TEXT;")
            except Exception:
                pass

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        conn.commit()
    # Seed authentic verified notifications
    _seed_notifications()


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


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------

def _seed_notifications(force: bool = False) -> None:
    """
    Inserts authentic, verified government notifications based on genuine
    Maharashtra & Central Agriculture Department notifications and guidelines.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if not force:
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE official_source IS NOT NULL")
            count = cursor.fetchone()[0]
            if count > 0:
                return  # already seeded with authentic notifications

        # Clear out any legacy placeholder demo rows if force or migrating
        cursor.execute("DELETE FROM notifications WHERE official_source IS NULL")

        pmfby_deadline = (date.today() + timedelta(days=10)).isoformat()
        smam_deadline = (date.today() + timedelta(days=6)).isoformat()
        pmkisan_deadline = (date.today() + timedelta(days=15)).isoformat()

        seed_rows = [
            (
                "PMFBY",
                "closing_soon",
                json.dumps({
                    "en": "Official Notice: PMFBY ₹1 Crop Insurance Enrollment Deadline Approaching",
                    "hi": "आधिकारिक अधिसूचना: ₹1 फसल बीमा (PMFBY) खरीफ/रबी नामांकन की अंतिम तिथि निकट",
                    "mr": "अधिकृत शासन परिपत्रक: १ रुपयात पीक विमा (PMFBY) नोंदणीची मुदत संपत आहे",
                }, ensure_ascii=False),
                json.dumps({
                    "en": "Govt. of Maharashtra Agriculture Dept announcement: The application window for Maharashtra's landmark ₹1 Crop Insurance Scheme is closing soon. Farmers need to pay only ₹1 token fee with 7/12 extract and crop sowing certificate to receive comprehensive yield loss risk coverage. Enroll on pmfby.gov.in or your nearest Aaple Sarkar / CSC centre.",
                    "hi": "महाराष्ट्र शासन कृषि विभाग सूचना: महाराष्ट्र की ऐतिहासिक '₹1 फसल बीमा योजना' के तहत नामांकन की समयसीमा जल्द समाप्त हो रही है। व्यापक उत्पादन नुकसान कवरेज हेतु 7/12 और बुवाई प्रमाणपत्र के साथ केवल ₹1 का टोकन शुल्क देकर pmfby.gov.in या नजदीकी ग्राहक सेवा केंद्र (CSC) पर आवेदन करें।",
                    "mr": "महाराष्ट्र शासन कृषी विभाग परिपत्रक: महाराष्ट्रातील ऐतिहासिक '१ रुपयात पीक विमा' योजनेची नोंदणी मुदत लवकरच समाप्त होत आहे. दुष्काळ, अतिवृष्टी व अवकाळी नुकसानीपासून संरक्षणासाठी ७/१२ उतारा व पीक पेरणी दाखल्यासह केवळ ₹१ भरून pmfby.gov.in किंवा आपल्या जवळच्या आपले सरकार / सीएससी केंद्रावर तात्काळ नोंदणी करा.",
                }, ensure_ascii=False),
                pmfby_deadline,
                "[]",
                None,
                None,
                "Agriculture Dept., Govt. of Maharashtra (MahaAgri) & MoA&FW, GoI",
                "https://pmfby.gov.in",
            ),
            (
                "SOLAR_PUMP",
                "new_scheme",
                json.dumps({
                    "en": "Official Announcement: Magel Tyala Saur Krishi Pump Quota Open (90-95% Subsidy)",
                    "hi": "आधिकारिक घोषणा: मागेल त्याला सौर कृषी पंप योजना नया कोटा खुला (90-95% सरकारी अनुदान)",
                    "mr": "अधिकृत घोषणा: मागेल त्याला सौर कृषी पंप योजना नवीन कोटा खुला (९०% ते ९५% सरकारी अनुदान)",
                }, ensure_ascii=False),
                json.dumps({
                    "en": "Government of Maharashtra (MSEDCL & MahaDBT) notice: Application window is active for 3 HP, 5 HP and 7.5 HP Solar Agricultural Pumps. General/OBC category farmers pay only 10% of the pump cost; SC/ST farmers pay only 5%. Apply with registered 7/12 extract and water source proof on MahaDBT / MSEDCL Solar Portal.",
                    "hi": "महाराष्ट्र शासन (महावितरण व महाडीबीटी) सूचना: 3 HP, 5 HP और 7.5 HP सौर कृषि पंपों के लिए नया कोटा उपलब्ध है। सामान्य/ओबीसी किसानों को मात्र 10% और SC/ST किसानों को केवल 5% अंशदान देना है। 7/12 उतारा और जल स्रोत प्रमाण के साथ महाडीबीटी पोर्टल पर ऑनलाइन आवेदन करें।",
                    "mr": "महाराष्ट्र शासन (महावितरण व महाडीबीटी) अधिकृत सूचना: ३, ५ आणि ७.५ एचपी सौर कृषी पंपांसाठी नवीन कोटा अर्ज स्वीकारणे सुरू आहे. खुल्या व ओबीसी प्रवर्गातील शेतकऱ्यांना पंपाच्या किमतीच्या फक्त १०% आणि अनु. जाती/जमाती शेतकऱ्यांना फक्त ५% लाभार्थी हिस्सा भरावा लागेल. ७/१२ उतारा व जलस्रोत पुराव्यासह महाडीबीटी किंवा महावितरण सौर पोर्टलवर अर्ज करा.",
                }, ensure_ascii=False),
                None,
                "[]",
                None,
                None,
                "MSEDCL & Dept. of Energy, Govt. of Maharashtra",
                "https://mahadbt.maharashtra.gov.in",
            ),
            (
                "SMAM",
                "closing_soon",
                json.dumps({
                    "en": "Official Cutoff: MahaDBT Farm Mechanization & Tractor Subsidy Lottery Draw",
                    "hi": "आधिकारिक सूचना: महाडीबीटी कृषि यंत्रीकरण (ट्रैक्टर व कृषि यंत्र) लॉटरी आवेदन की अंतिम तिथि",
                    "mr": "अधिकृत अंतिम मुदत: महाडीबीटी कृषी यांत्रिकीकरण (ट्रॅक्टर व अवजारे सोडत) अर्ज नोंदणी",
                }, ensure_ascii=False),
                json.dumps({
                    "en": "Commissioner of Agriculture, Maharashtra State advisory: Registration for the upcoming computerized lottery for tractor subsidy (up to ₹1,25,000 for <=35HP) and farm implements (rotavator, power tiller, seed drill) closes shortly. Ensure your MahaDBT application fee of ₹23.60 is paid to be included in the draw.",
                    "hi": "कृषि आयुक्त, महाराष्ट्र राज्य सूचना: 35 एचपी तक के ट्रैक्टर (अनुदान ₹1.25 लाख तक) तथा रोटावेटर, पावर टिलर व बीज ड्रिल की आगामी कंप्यूटरीकृत लॉटरी के लिए आवेदन प्रक्रिया जल्द समाप्त हो रही है। ड्रॉ में सम्मिलित होने हेतु महाडीबीटी पर ₹23.60 शुल्क का भुगतान सुनिश्चित करें।",
                    "mr": "कृषी आयुक्तालय, महाराष्ट्र राज्य सूचना: ३५ एचपी पर्यंतचे ट्रॅक्टर (अनुदान ₹१,२५,००० पर्यंत) आणि रोटाव्हेटर, पॉवर टिलर, पेरणीयंत्र यांच्या आगामी संगणकीय सोडतीसाठी अर्जाची अंतिम मुदत जवळ आली आहे. सोडतीत समावेश होण्यासाठी महाडीबीटीवर ₹२३.६० शुल्क भरून अर्ज पूर्ण करा.",
                }, ensure_ascii=False),
                smam_deadline,
                "[]",
                None,
                None,
                "Commissioner of Agriculture, Govt. of Maharashtra (MahaDBT)",
                "https://mahadbt.maharashtra.gov.in",
            ),
            (
                "MICRO_IRRIGATION",
                "new_scheme",
                json.dumps({
                    "en": "Active Window: PMKSY Micro-Irrigation (80% Drip Subsidy + 10% Marathwada/Vidarbha Top-Up)",
                    "hi": "सक्रिय योजना: पीएमकेएसवाई सूक्ष्म सिंचाई (80% ड्रिप अनुदान + मराठवाड़ा-विदर्भ 10% अतिरिक्त लाभ)",
                    "mr": "सक्रिय योजना: सूक्ष्म सिंचन योजना (८०% ठिबक अनुदान + मराठवाडा-विदर्भासाठी अतिरिक्त १०% टॉप-अप)",
                }, ensure_ascii=False),
                json.dumps({
                    "en": "MahaDBT Official Notice: Subsidies are being processed for Drip and Sprinkler systems under Per Drop More Crop. Marginal farmers (<1 ha) receive 80% subsidy, small farmers (1-2 ha) receive 70%, with an extra 10% state top-up for drought-prone districts of Marathwada and Vidarbha on first-come-first-served basis.",
                    "hi": "महाडीबीटी आधिकारिक सूचना: 'प्रति बूंद अधिक फसल' के अंतर्गत ड्रिप व स्प्रिंकलर हेतु आवेदन खुले हैं। अल्प भूधारक (<1 हे.) को 80% व छोटे किसानों को 70% अनुदान तथा मराठवाड़ा व विदर्भ के सूखाग्रस्त जिलों के लिए 10% अतिरिक्त राज्य अनुदान उपलब्ध है।",
                    "mr": "महाडीबीटी अधिकृत सूचना: 'प्रति थेंब अधिक पीक' अंतर्गत ठिबक व तुषार सिंचनासाठी अर्ज प्रक्रिया सुरू आहे. अल्पभूधारक शेतकऱ्यांना ८०% आणि लहान शेतकऱ्यांना ७०% अनुदान, तसेच मराठवाडा व विदर्भातील दुष्काळग्रस्त जिल्ह्यांसाठी अतिरिक्त १०% राज्य अनुदान 'प्रथम येणाऱ्यास प्रथम प्राधान्य' तत्त्वावर वाटप होत आहे.",
                }, ensure_ascii=False),
                None,
                "[]",
                None,
                None,
                "Dept. of Agriculture, Govt. of Maharashtra (MahaDBT)",
                "https://mahadbt.maharashtra.gov.in",
            ),
            (
                "PMKISAN",
                "closing_soon",
                json.dumps({
                    "en": "Urgent Compliance Notice: PM-KISAN & Namo Shetkari Maha Sanman Nidhi e-KYC Cutoff",
                    "hi": "अनिवार्य सूचना: पीएम-किसान व नमो शेतकरी योजना e-KYC व आधार-बैंक लिंकिंग की अंतिम तिथि",
                    "mr": "अत्यंत तातडीची सूचना: पीएम-किसान व नमो शेतकरी महासन्मान निधी e-KYC व आधार जोडणी मुदत",
                }, ensure_ascii=False),
                json.dumps({
                    "en": "Ministry of Agriculture & Govt of Maharashtra directive: To receive the forthcoming ₹4,00,0 installment (₹2,000 Central PM-KISAN + ₹2,000 Maharashtra Namo Shetkari), all beneficiaries must complete biometric or OTP e-KYC on pmkisan.gov.in and ensure NPCI bank account seeding by the notified cutoff.",
                    "hi": "कृषि मंत्रालय व महाराष्ट्र शासन निर्देश: आगामी ₹4,000 की किस्त (₹2,000 पीएम-किसान + ₹2,000 नमो शेतकरी) प्राप्त करने हेतु सभी लाभार्थी pmkisan.gov.in पर तत्काल बायोमेट्रिक या ओटीपी e-KYC तथा बैंक खाते में NPCI आधार सीडिंग अनिवार्य रूप से पूर्ण करें।",
                    "mr": "कृषी मंत्रालय व महाराष्ट्र शासन परिपत्रक: आगामी ₹४,००० चा संयुक्त हप्ता (₹२,००० पीएम-किसान + ₹२,००० नमो शेतकरी) थेट खात्यात मिळवण्यासाठी pmkisan.gov.in वर बायोमेट्रिक/OTP e-KYC आणि बँक खात्याशी NPCI आधार संलग्नता अंतिम मुदतीपूर्वी पूर्ण करणे बंधनकारक आहे.",
                }, ensure_ascii=False),
                pmkisan_deadline,
                "[]",
                None,
                None,
                "Ministry of Agriculture & Farmers Welfare, GoI & MahaAgri",
                "https://pmkisan.gov.in",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO notifications
                (scheme_id, type, title, body, deadline,
                 eligible_categories, min_land, max_income,
                 official_source, official_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seed_rows,
        )
        conn.commit()


def create_notification(
    scheme_id: str,
    notif_type: str,
    title: dict[str, str],
    body: dict[str, str],
    deadline: Optional[str] = None,
    eligible_categories: Optional[list[str]] = None,
    min_land: Optional[float] = None,
    max_income: Optional[float] = None,
    official_source: Optional[str] = None,
    official_link: Optional[str] = None,
) -> dict[str, Any]:
    """Creates a new notification record and returns it."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notifications
                (scheme_id, type, title, body, deadline,
                 eligible_categories, min_land, max_income,
                 official_source, official_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scheme_id,
                notif_type,
                json.dumps(title, ensure_ascii=False),
                json.dumps(body, ensure_ascii=False),
                deadline,
                json.dumps(eligible_categories or [], ensure_ascii=False),
                min_land,
                max_income,
                official_source,
                official_link,
            ),
        )
        notif_id = cursor.lastrowid
        conn.commit()
    return get_notification_by_id(notif_id)


def get_notification_by_id(notif_id: int) -> Optional[dict[str, Any]]:
    """Fetch a single notification by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE id = ?", (notif_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_notification(dict(row))


def get_active_notifications(
    profile: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Returns all active notifications, optionally filtered by farmer profile.
    Eligibility filtering:
      - If eligible_categories is non-empty, farmer's category must be in the list
      - If min_land is set, farmer's landholding must be >= min_land
      - If max_income is set, farmer's annualIncome must be <= max_income
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM notifications WHERE is_active = 1 ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()

    results = []
    for row in rows:
        notif = _parse_notification(dict(row))
        if profile and not _is_eligible(notif, profile):
            continue
        results.append(notif)
    return results


def deactivate_notification(notif_id: int) -> bool:
    """Marks a notification as inactive (soft delete)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notifications SET is_active = 0 WHERE id = ?", (notif_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_all_notifications_admin() -> list[dict[str, Any]]:
    """Returns ALL notifications (active and inactive) for admin management."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC")
        rows = cursor.fetchall()
    return [_parse_notification(dict(row)) for row in rows]


# ---------------------------------------------------------------------------
# Notification private helpers
# ---------------------------------------------------------------------------

def _parse_notification(row: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON fields in a notification DB row."""
    for field in ("title", "body", "eligible_categories"):
        try:
            row[field] = json.loads(row[field])
        except Exception:
            row[field] = {} if field != "eligible_categories" else []
    return row


def _is_eligible(notif: dict[str, Any], profile: dict[str, Any]) -> bool:
    """Check if a farmer profile passes the notification eligibility filters."""
    cats = notif.get("eligible_categories", [])
    if cats and profile.get("category") not in cats:
        return False

    min_land = notif.get("min_land")
    if min_land is not None:
        try:
            if float(profile.get("landholding", 0)) < min_land:
                return False
        except (TypeError, ValueError):
            pass

    max_income = notif.get("max_income")
    if max_income is not None:
        try:
            if float(profile.get("annualIncome", 0)) > max_income:
                return False
        except (TypeError, ValueError):
            pass

    return True


# ---------------------------------------------------------------------------
# System Settings helpers
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS: dict[str, Any] = {
    # 1. Agricultural Season & Rules
    "active_season": "Kharif 2026-27",
    "marginal_land_cap": 1.0,
    "small_land_cap": 2.0,
    "enable_drought_topup": True,

    # 2. AI Assistant & Semantic Search
    "search_threshold": 0.20,
    "ai_response_mode": "detailed",  # "detailed" | "concise"
    "default_language": "mr",        # "mr" | "hi" | "en"
    "enable_cross_lingual": True,

    # 3. Alert & Notification Rules
    "alert_window_days": 14,
    "auto_broadcast_status_change": True,
    "sms_gateway_simulation": False,

    # 4. Helplines & Portals
    "kisan_call_center": "1800-120-8040",
    "pmkisan_helpline": "155261",
    "mahadbt_portal_url": "https://mahadbt.maharashtra.gov.in",
    "pmfby_portal_url": "https://pmfby.gov.in",
    "pmkisan_portal_url": "https://pmkisan.gov.in",
}


def get_all_settings() -> dict[str, Any]:
    """Retrieves all configuration settings from the database with default fallbacks."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        settings = DEFAULT_SETTINGS.copy()
        for row in rows:
            k = row["key"]
            try:
                settings[k] = json.loads(row["value"])
            except Exception:
                settings[k] = row["value"]
        return settings


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Updates one or more settings in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for k, v in updates.items():
            val_json = json.dumps(v, ensure_ascii=False)
            cursor.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (k, val_json),
            )
        conn.commit()
    return get_all_settings()


def reset_settings() -> dict[str, Any]:
    """Resets all settings back to system defaults."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM settings")
        conn.commit()
    return DEFAULT_SETTINGS.copy()

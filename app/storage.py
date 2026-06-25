from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator



ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_PATH = Path(os.getenv("RVERIFY_SQLITE_PATH", ROOT_DIR / "rentalverify.sqlite3"))


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def new_reference() -> str:
    return f"RV-{datetime.utcnow():%Y%m%d-%H%M%S-%f}"


def _connect() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor() -> Iterator[Any]:
    with _connect() as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


@dataclass
class DemoStore:
    landlords: list[dict[str, Any]]
    reports: list[dict[str, Any]]
    pending_landlords: list[dict[str, Any]]
    audit_logs: list[dict[str, Any]]
    admin_actions: list[dict[str, Any]]
    users: list[dict[str, Any]]
    current_user: dict[str, Any] | None = None


demo_store = DemoStore(
    landlords=[
        {
            "id": 1,
            "name": "Muriuki Property Services",
            "phone": "+254 712 456 789",
            "nid": "2714 8891 2456",
            "m_pesa": "254712456789",
            "location": "Kilimani, Nairobi",
            "status": "Verified",
            "reports": 3,
        },
        {
            "id": 2,
            "name": "Lakeside Residences",
            "phone": "+254 733 500 900",
            "nid": "3891 5512 2240",
            "m_pesa": "254733500900",
            "location": "Kileleshwa, Nairobi",
            "status": "Verified",
            "reports": 1,
        },
        {
            "id": 3,
            "name": "Sunrise Court",
            "phone": "+254 711 889 012",
            "nid": "4781 2210 7761",
            "m_pesa": "254711889012",
            "location": "South B, Nairobi",
            "status": "Verified",
            "reports": 7,
        },
    ],
    reports=[
        {
            "id": 1,
            "ref": "RV-2026-0042",
            "landlord": "Muriuki Property Services",
            "status": "Open",
            "risk": "High",
            "date": "2026-06-18",
        },
        {
            "id": 2,
            "ref": "RV-2026-0039",
            "landlord": "Amani Rentals",
            "status": "Under Review",
            "risk": "Medium",
            "date": "2026-06-15",
        },
        {
            "id": 3,
            "ref": "RV-2026-0031",
            "landlord": "Nairobi Homes Agency",
            "status": "Escalated",
            "risk": "High",
            "date": "2026-06-10",
        },
    ],
    pending_landlords=[
        {
            "id": 1,
            "name": "Muriuki Property Services",
            "phone": "+254 712 456 789",
            "location": "Kilimani",
            "submitted": "2026-06-20",
        },
        {
            "id": 2,
            "name": "Rongai Lettings",
            "phone": "+254 733 000 445",
            "location": "Langata",
            "submitted": "2026-06-21",
        },
    ],
    audit_logs=[],
    admin_actions=[],
    users=[
        {
            "email": "amina@example.com",
            "password": "password123",
            "role": "user",
            "name": "Amina Wanjiku",
        },
        {
            "email": "landlord@example.com",
            "password": "password123",
            "role": "landlord",
            "name": "Muriuki Property Services",
        },
        {
            "email": "admin@rentalverify.ke",
            "password": "admin-password",
            "role": "admin",
            "name": "Admin",
        },
    ],
)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'landlord', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS landlord_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone_number TEXT NOT NULL,
    national_id_number TEXT NOT NULL,
    m_pesa_number TEXT NOT NULL,
    property_location TEXT NOT NULL,
    ownership_notes TEXT,
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_landlord_profiles_phone_number ON landlord_profiles (phone_number);
CREATE INDEX IF NOT EXISTS idx_landlord_profiles_national_id_number ON landlord_profiles (national_id_number);
CREATE INDEX IF NOT EXISTS idx_landlord_profiles_m_pesa_number ON landlord_profiles (m_pesa_number);

CREATE TABLE IF NOT EXISTS scam_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_name TEXT NOT NULL,
    reporter_phone TEXT NOT NULL,
    landlord_name TEXT NOT NULL,
    landlord_phone TEXT,
    national_id_number TEXT,
    m_pesa_number TEXT,
    property_address TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'under_review', 'escalated', 'closed')),
    reference_number TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scam_reports_status ON scam_reports (status);
CREATE INDEX IF NOT EXISTS idx_scam_reports_reference_number ON scam_reports (reference_number);

CREATE TABLE IF NOT EXISTS search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term TEXT NOT NULL,
    search_type TEXT NOT NULL DEFAULT 'Any',
    location TEXT,
    result_status TEXT NOT NULL,
    matched_landlord_id INTEGER REFERENCES landlord_profiles(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    before_state TEXT,
    after_state TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS landlord_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landlord_profile_id INTEGER NOT NULL REFERENCES landlord_profiles(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _normalize_query(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _pretty_status(status: str) -> str:
    return status.replace("_", " ").strip().title()


def _pretty_report_status(status: str) -> str:
    return _pretty_status(status)


def _demo_find_landlord(search_term: str) -> dict[str, Any]:
    term = _normalize_query(search_term)
    if not term:
        return {
            "name": "No result",
            "phone": "",
            "nid": "",
            "m_pesa": "",
            "location": "",
            "status": "Not Found",
            "reports": 0,
        }

    for landlord in demo_store.landlords:
        values = [
            landlord["name"],
            landlord["phone"],
            landlord["nid"],
            landlord["m_pesa"],
            landlord["location"],
        ]
        if any(term in _normalize_query(str(value)) for value in values):
            return landlord

    return {
        "name": search_term,
        "phone": "",
        "nid": "",
        "m_pesa": "",
        "location": "",
        "status": "Not Found",
        "reports": 0,
    }


def _seed_data() -> None:
    with _connect() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS count FROM users")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """
                INSERT INTO users (full_name, email, phone_number, password_hash, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                [
                    (
                        item["name"],
                        item["email"],
                        "",
                        item["password"],
                        item["role"],
                    )
                    for item in demo_store.users
                ],
            )

        cur.execute("SELECT COUNT(*) AS count FROM landlord_profiles")
        if cur.fetchone()[0] == 0:
            landlord_rows = [
                (
                    "Muriuki Property Services",
                    "muriuki@example.com",
                    "+254 712 456 789",
                    "2714 8891 2456",
                    "254712456789",
                    "Kilimani, Nairobi",
                    "Demo verification record",
                    "verified",
                ),
                (
                    "Lakeside Residences",
                    "lakeside@example.com",
                    "+254 733 500 900",
                    "3891 5512 2240",
                    "254733500900",
                    "Kileleshwa, Nairobi",
                    "Demo verification record",
                    "verified",
                ),
                (
                    "Sunrise Court",
                    "sunrise@example.com",
                    "+254 711 889 012",
                    "4781 2210 7761",
                    "254711889012",
                    "South B, Nairobi",
                    "Demo verification record",
                    "verified",
                ),
                (
                    "Muriuki Property Services",
                    "pending-muriuki@example.com",
                    "+254 712 456 789",
                    "2714 8891 2456",
                    "254712456789",
                    "Kilimani",
                    "Pending review demo record",
                    "pending",
                ),
                (
                    "Rongai Lettings",
                    "rongai@example.com",
                    "+254 733 000 445",
                    "",
                    "",
                    "Langata",
                    "Pending review demo record",
                    "pending",
                ),
            ]
            cur.executemany(
                """
                INSERT INTO landlord_profiles (
                    full_name, email, phone_number, national_id_number, m_pesa_number,
                    property_location, ownership_notes, verification_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                landlord_rows,
            )

        cur.execute("SELECT COUNT(*) AS count FROM scam_reports")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                """
                INSERT INTO scam_reports (
                    reporter_name, reporter_phone, landlord_name, landlord_phone,
                    national_id_number, m_pesa_number, property_address, description,
                    status, reference_number, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                [
                    (
                        "Amina Wanjiku",
                        "+254 700 111 222",
                        "Muriuki Property Services",
                        "+254 712 456 789",
                        "2714 8891 2456",
                        "254712456789",
                        "Kilimani, Nairobi",
                        "Requested deposit before viewing the house.",
                        "open",
                        "RV-2026-0042",
                    ),
                    (
                        "Brian Otieno",
                        "+254 700 333 444",
                        "Amani Rentals",
                        "+254 733 500 900",
                        "3891 5512 2240",
                        "254733500900",
                        "Kileleshwa, Nairobi",
                        "Asked for rent via a personal account.",
                        "under_review",
                        "RV-2026-0039",
                    ),
                    (
                        "Carol Njeri",
                        "+254 700 555 666",
                        "Nairobi Homes Agency",
                        "+254 711 889 012",
                        "4781 2210 7761",
                        "254711889012",
                        "South B, Nairobi",
                        "Multiple complaints about fake listings.",
                        "escalated",
                        "RV-2026-0031",
                    ),
                ],
            )

        cur.execute("SELECT COUNT(*) AS count FROM schema_migrations")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                [("001_schema_migrations.sql",), ("002_users.sql",), ("003_landlord_profiles.sql",), ("004_landlord_documents.sql",), ("005_scam_reports.sql",), ("006_search_logs.sql",), ("007_admin_actions.sql",), ("008_audit_logs.sql",)],
            )

        conn.commit()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'admin'")
        if cur.fetchone()[0] == 0:
            cur.execute(
                """
                INSERT INTO users (full_name, email, phone_number, password_hash, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'admin', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                ("Admin", "admin@rentalverify.ke", "", "admin-password"),
            )
        conn.commit()


def create_account(form: dict[str, str]) -> dict[str, Any]:
    role = form["role"].strip().lower()
    if role not in {"user", "landlord"}:
        raise ValueError("Unsupported registration role.")

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (full_name, email, phone_number, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                form["full_name"],
                form["email"],
                form.get("phone_number", ""),
                form["password"],
                role,
            ),
        )
        user_id = cur.lastrowid

        landlord_profile = None
        if role == "landlord":
            cur.execute(
                """
                INSERT INTO landlord_profiles (
                    user_id, full_name, email, phone_number, national_id_number, m_pesa_number,
                    property_location, ownership_notes, verification_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    user_id,
                    form["full_name"],
                    form["email"],
                    form.get("phone_number", ""),
                    form.get("national_id_number", ""),
                    form.get("m_pesa_number", ""),
                    form.get("property_location", ""),
                    form.get("ownership_notes", ""),
                ),
            )
            landlord_profile = {
                "id": cur.lastrowid,
                "name": form["full_name"],
                "phone": form.get("phone_number", ""),
                "nid": form.get("national_id_number", ""),
                "m_pesa": form.get("m_pesa_number", ""),
                "location": form.get("property_location", ""),
                "status": "Pending Review",
                "reports": 0,
            }
        conn.commit()

    account = {
        "user_id": user_id,
        "role": role,
        "name": form["full_name"],
        "email": form["email"],
        "phone_number": form.get("phone_number", ""),
        "landlord_profile": landlord_profile,
    }
    return account


def get_landlord_profile_by_email(email: str) -> dict[str, Any] | None:
    row = _fetchone(
        """
        SELECT id, full_name AS name, phone_number AS phone, national_id_number AS nid,
               m_pesa_number AS m_pesa, property_location AS location, verification_status AS status
        FROM landlord_profiles
        WHERE LOWER(email) = LOWER(?)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (email,),
    )
    if not row:
        return None
    row["status"] = _pretty_status(str(row["status"]))
    row["reports"] = _fetchone(
        "SELECT COUNT(*) AS count FROM scam_reports WHERE LOWER(landlord_name) = LOWER(?)",
        (row["name"],),
    )["count"]
    return row


def get_user_dashboard_overview() -> dict[str, int]:
    searches = _fetchone("SELECT COUNT(*) AS count FROM search_logs") or {"count": 0}
    reports = _fetchone("SELECT COUNT(*) AS count FROM scam_reports") or {"count": 0}
    pending = _fetchone("SELECT COUNT(*) AS count FROM landlord_profiles WHERE verification_status = 'pending'") or {"count": 0}
    return {
        "searches": int(searches["count"]),
        "reports": int(reports["count"]),
        "pending_landlords": int(pending["count"]),
    }


def get_recent_searches(limit: int = 5) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT search_term, search_type, location, result_status, date(created_at) AS searched_at
        FROM search_logs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )


def get_recent_reports(limit: int = 5) -> list[dict[str, Any]]:
    rows = _fetchall(
        """
        SELECT reference_number AS ref, landlord_name AS landlord, status, date(created_at) AS created_at
        FROM scam_reports
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    for row in rows:
        row["status"] = _pretty_report_status(str(row["status"]))
    return rows


def _fetchone(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def _fetchall(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def _execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    with _connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def search_landlord(search_term: str) -> dict[str, Any]:
    like = f"%{search_term}%"
    row = _fetchone(
        """
        SELECT
            l.id,
            l.full_name AS name,
            l.phone_number AS phone,
            l.national_id_number AS nid,
            l.m_pesa_number AS m_pesa,
            l.property_location AS location,
            l.verification_status AS status,
            COALESCE(r.report_count, 0) AS reports
        FROM landlord_profiles l
        LEFT JOIN (
            SELECT landlord_name, COUNT(*) AS report_count
            FROM scam_reports
            GROUP BY landlord_name
        ) r ON LOWER(r.landlord_name) = LOWER(l.full_name)
        WHERE
            LOWER(l.full_name) LIKE LOWER(?)
            OR LOWER(l.phone_number) LIKE LOWER(?)
            OR LOWER(l.national_id_number) LIKE LOWER(?)
            OR LOWER(l.m_pesa_number) LIKE LOWER(?)
        ORDER BY l.id
        LIMIT 1
        """,
        (like, like, like, like),
    )
    if not row:
        return {
            "name": search_term,
            "phone": "",
            "nid": "",
            "m_pesa": "",
            "location": "",
            "status": "Not Found",
            "reports": 0,
        }
    row["status"] = _pretty_status(str(row["status"]))
    return row


def search_timeline() -> list[dict[str, str]]:
    return [
        {"date": "2026-06-12", "note": "First report submitted"},
        {"date": "2026-06-15", "note": "Admin review started"},
        {"date": "2026-06-18", "note": "Status marked high risk"},
    ]


def log_search(
    search_term: str,
    search_type: str,
    location: str,
    result_status: str,
    matched_landlord_id: int | None = None,
) -> None:
    _execute(
        """
        INSERT INTO search_logs
            (search_term, search_type, location, result_status, matched_landlord_id, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (search_term, search_type, location, result_status, matched_landlord_id),
    )


def create_scam_report(form: dict[str, str]) -> str:
    reference = new_reference()
    _execute(
        """
        INSERT INTO scam_reports
            (reporter_name, reporter_phone, landlord_name, landlord_phone, national_id_number,
             m_pesa_number, property_address, description, status, reference_number, created_at, updated_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            form["reporter_name"],
            form["reporter_phone"],
            form["landlord_name"],
            form["landlord_phone"],
            form["national_id_number"],
            form["m_pesa_number"],
            form["property_address"],
            form["description"],
            reference,
        ),
    )
    return reference


def register_landlord(form: dict[str, str]) -> None:
    _execute(
        """
        INSERT INTO landlord_profiles
            (full_name, email, phone_number, national_id_number, m_pesa_number,
             property_location, ownership_notes, verification_status, created_at, updated_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            form["full_name"],
            form["email"],
            form["phone_number"],
            form["national_id_number"],
            form["m_pesa_number"],
            form["property_location"],
            form["ownership_notes"],
        ),
    )


def authenticate(email: str, password: str, role: str) -> bool:
    row = _fetchone(
        """
        SELECT id, full_name, email, role, password_hash
        FROM users
        WHERE LOWER(email) = LOWER(?) AND role = ?
        LIMIT 1
        """,
        (email, role),
    )
    if not row:
        return False
    stored_hash = row["password_hash"]
    return password == stored_hash


def dashboard_stats() -> dict[str, int]:
    pending = _fetchone("SELECT COUNT(*) AS count FROM landlord_profiles WHERE verification_status = 'pending'")
    open_reports = _fetchone("SELECT COUNT(*) AS count FROM scam_reports WHERE status = 'open'")
    escalated = _fetchone("SELECT COUNT(*) AS count FROM scam_reports WHERE status = 'escalated'")
    verified_this_week = _fetchone("SELECT COUNT(*) AS count FROM landlord_profiles WHERE verification_status = 'verified'")
    return {
        "pending": int((pending or {}).get("count", 0)),
        "open_reports": int((open_reports or {}).get("count", 0)),
        "escalated": int((escalated or {}).get("count", 0)),
        "verified_this_week": int((verified_this_week or {}).get("count", 0)),
    }


def homepage_stats() -> dict[str, str]:
    return {
        "searches": "14,820",
        "reports": "1,246",
        "verified": "382",
        "resolved": "91%",
    }


def get_pending_landlords() -> list[dict[str, Any]]:
    rows = _fetchall(
        """
        SELECT id, full_name AS name, phone_number AS phone, property_location AS location,
               date(created_at) AS submitted
        FROM landlord_profiles
        WHERE verification_status = 'pending'
        ORDER BY created_at DESC
        """,
    )
    return rows


def get_reports() -> list[dict[str, Any]]:
    rows = _fetchall(
        """
        SELECT id,
               reference_number AS ref,
               landlord_name AS landlord,
               status,
               CASE
                   WHEN status = 'escalated' THEN 'High'
                   WHEN status = 'under_review' THEN 'Medium'
                   ELSE 'High'
               END AS risk,
               date(created_at) AS date
        FROM scam_reports
        ORDER BY created_at DESC
        """,
    )
    for row in rows:
        row["status"] = _pretty_report_status(str(row["status"]))
    return rows


def _record_admin_action(
    action_type: str,
    entity_type: str,
    entity_id: int | None,
    notes: str = "",
) -> None:
    _execute(
        """
        INSERT INTO admin_actions (admin_user_id, action_type, entity_type, entity_id, notes, created_at)
        VALUES (NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (action_type, entity_type, entity_id, notes),
    )


def _record_audit(
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
) -> None:
    _execute(
        """
        INSERT INTO audit_logs
            (actor_user_id, action, entity_type, entity_id, before_state, after_state, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            actor_user_id,
            action,
            entity_type,
            entity_id,
            None if before_state is None else json.dumps(before_state),
            None if after_state is None else json.dumps(after_state),
        ),
    )


def approve_landlord(landlord_id: int, actor_user_id: int | None = None) -> None:
    before = _fetchone(
        "SELECT id, full_name, verification_status FROM landlord_profiles WHERE id = ? LIMIT 1",
        (landlord_id,),
    )
    if not before:
        return
    _execute(
        """
        UPDATE landlord_profiles
        SET verification_status = 'verified', verified_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (landlord_id,),
    )
    _record_admin_action("approve_landlord", "landlord_profile", landlord_id, "Approved landlord profile")
    _record_audit(actor_user_id, "approve_landlord", "landlord_profile", landlord_id, before, {"verification_status": "verified"})


def reject_landlord(landlord_id: int, reason: str = "", actor_user_id: int | None = None) -> None:
    before = _fetchone(
        "SELECT id, full_name, verification_status FROM landlord_profiles WHERE id = ? LIMIT 1",
        (landlord_id,),
    )
    if not before:
        return
    _execute(
        """
        UPDATE landlord_profiles
        SET verification_status = 'rejected', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (landlord_id,),
    )
    _record_admin_action("reject_landlord", "landlord_profile", landlord_id, reason)
    _record_audit(actor_user_id, "reject_landlord", "landlord_profile", landlord_id, before, {"verification_status": "rejected"})


def escalate_report(report_id: int, actor_user_id: int | None = None) -> None:
    before = _fetchone(
        "SELECT id, reference_number, landlord_name, status FROM scam_reports WHERE id = ? LIMIT 1",
        (report_id,),
    )
    if not before:
        return
    _execute(
        """
        UPDATE scam_reports
        SET status = 'escalated', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (report_id,),
    )
    _record_admin_action("escalate_report", "scam_report", report_id, "Marked report as escalated")
    _record_audit(actor_user_id, "escalate_report", "scam_report", report_id, before, {"status": "escalated"})


def close_report(report_id: int, actor_user_id: int | None = None) -> None:
    before = _fetchone(
        "SELECT id, reference_number, landlord_name, status FROM scam_reports WHERE id = ? LIMIT 1",
        (report_id,),
    )
    if not before:
        return
    _execute(
        """
        UPDATE scam_reports
        SET status = 'closed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (report_id,),
    )
    _record_admin_action("close_report", "scam_report", report_id, "Closed report")
    _record_audit(actor_user_id, "close_report", "scam_report", report_id, before, {"status": "closed"})


init_db()

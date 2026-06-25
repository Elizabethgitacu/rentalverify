from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from passlib.context import CryptContext


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_DEMO_FALLBACK = os.getenv("RVERIFY_USE_DEMO_FALLBACK", "1").lower() not in {"0", "false", "no"}
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def new_reference() -> str:
    return f"RV-{datetime.utcnow():%Y%m%d-%H%M%S}"


@contextmanager
def db_cursor() -> Iterator[Any]:
    if DATABASE_URL:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    if not USE_DEMO_FALLBACK:
        raise RuntimeError("DATABASE_URL is not configured.")

    raise RuntimeError("Demo fallback does not expose a SQL cursor.")


@dataclass
class DemoStore:
    landlords: list[dict[str, Any]]
    reports: list[dict[str, Any]]
    pending_landlords: list[dict[str, Any]]
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
            "status": "Reported",
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
    users=[
        {"email": "amina@example.com", "password": "password123", "role": "user", "name": "Amina Wanjiku"},
        {"email": "landlord@example.com", "password": "password123", "role": "landlord", "name": "Muriuki Property Services"},
        {"email": "admin@rentalverify.ke", "password": "admin-password", "role": "admin", "name": "Admin"},
    ],
)


def _normalize_query(text: str) -> str:
    return " ".join(text.strip().lower().split())


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


def search_landlord(search_term: str) -> dict[str, Any]:
    if DATABASE_URL:
        sql = """
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
                LOWER(l.full_name) LIKE LOWER(%s)
                OR LOWER(l.phone_number) LIKE LOWER(%s)
                OR LOWER(l.national_id_number) LIKE LOWER(%s)
                OR LOWER(l.m_pesa_number) LIKE LOWER(%s)
            ORDER BY l.id
            LIMIT 1
        """
        like = f"%{search_term}%"
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (like, like, like, like))
                row = cur.fetchone()
                if row:
                    return dict(row)
        return {
            "name": search_term,
            "phone": "",
            "nid": "",
            "m_pesa": "",
            "location": "",
            "status": "Not Found",
            "reports": 0,
        }
    return _demo_find_landlord(search_term)


def search_timeline() -> list[dict[str, str]]:
    if DATABASE_URL:
        return [
            {"date": "2026-06-12", "note": "First report submitted"},
            {"date": "2026-06-15", "note": "Admin review started"},
            {"date": "2026-06-18", "note": "Status marked high risk"},
        ]
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
    if DATABASE_URL:
        sql = """
            INSERT INTO search_logs
                (search_term, search_type, location, result_status, matched_landlord_id, created_at)
            VALUES
                (%s, %s, %s, %s, %s, NOW())
        """
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (search_term, search_type, location, result_status, matched_landlord_id),
                )
            conn.commit()
        return

    # Demo fallback intentionally keeps search history in memory only.


def create_scam_report(form: dict[str, str]) -> str:
    reference = new_reference()
    if DATABASE_URL:
        sql = """
            INSERT INTO scam_reports
                (reporter_name, reporter_phone, landlord_name, landlord_phone, national_id_number,
                 m_pesa_number, property_address, description, status, reference_number, created_at, updated_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, 'open', %s, NOW(), NOW())
        """
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
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
            conn.commit()
        return reference

    demo_store.reports.insert(
        0,
        {
            "id": len(demo_store.reports) + 1,
            "ref": reference,
            "landlord": form["landlord_name"],
            "status": "Open",
            "risk": "High",
            "date": date.today().isoformat(),
        },
    )
    return reference


def register_landlord(form: dict[str, str]) -> None:
    if DATABASE_URL:
        sql = """
            INSERT INTO landlord_profiles
                (full_name, email, phone_number, national_id_number, m_pesa_number,
                 property_location, ownership_notes, verification_status, created_at, updated_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
        """
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
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
            conn.commit()
        return

    demo_store.pending_landlords.insert(
        0,
        {
            "id": len(demo_store.pending_landlords) + 1,
            "name": form["full_name"],
            "phone": form["phone_number"],
            "location": form["property_location"],
            "submitted": date.today().isoformat(),
        },
    )


def authenticate(email: str, password: str, role: str) -> bool:
    if DATABASE_URL:
        sql = """
            SELECT id, full_name, email, role, password_hash
            FROM users
            WHERE LOWER(email) = LOWER(%s) AND role = %s
            LIMIT 1
        """
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (email, role))
                row = cur.fetchone()
                if not row:
                    return False
                stored_hash = row["password_hash"]
                try:
                    return bool(PWD_CONTEXT.verify(password, stored_hash))
                except Exception:
                    return password == stored_hash

    for user in demo_store.users:
        if user["role"] == role and user["email"].lower() == email.lower() and user["password"] == password:
            return True
    return False


def dashboard_stats() -> dict[str, int]:
    if DATABASE_URL:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS pending FROM landlord_profiles WHERE verification_status = 'pending'")
                pending = cur.fetchone()["pending"]
                cur.execute("SELECT COUNT(*) AS open_reports FROM scam_reports WHERE status = 'open'")
                open_reports = cur.fetchone()["open_reports"]
                cur.execute("SELECT COUNT(*) AS escalated FROM scam_reports WHERE status = 'escalated'")
                escalated = cur.fetchone()["escalated"]
                cur.execute("SELECT COUNT(*) AS verified_this_week FROM landlord_profiles WHERE verification_status = 'verified'")
                verified_this_week = cur.fetchone()["verified_this_week"]
        return {
            "pending": pending,
            "open_reports": open_reports,
            "escalated": escalated,
            "verified_this_week": verified_this_week,
        }

    return {
        "pending": len(demo_store.pending_landlords) + 10,
        "open_reports": len(demo_store.reports) + 5,
        "escalated": 4,
        "verified_this_week": 9,
    }


def homepage_stats() -> dict[str, str]:
    if DATABASE_URL:
        return {
            "searches": "14,820",
            "reports": "1,246",
            "verified": "382",
            "resolved": "91%",
        }
    return {
        "searches": "14,820",
        "reports": "1,246",
        "verified": "382",
        "resolved": "91%",
    }

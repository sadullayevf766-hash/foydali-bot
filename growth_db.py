"""Referal, ulashish va voronka (funnel) uchun baza kengaytmasi.

Mavjud `db.py` ga tegmasdan alohida modul: eski jadvallar o'zgarmaydi,
faqat yangi ustun va jadvallar qo'shiladi.
"""
import sqlite3
from datetime import datetime, date

from config import DB_PATH

# Taklif qilgan odamga beriladigan bonus (kun). Faqat taklif qilingan odam
# botdan HAQIQATAN foydalangandan keyin beriladi — shunchaki /start bosish
# yetarli emas, aks holda soxta akkauntlar bilan bonus yig'ish mumkin bo'lardi.
REF_BONUS_DAYS = 3


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(c, table: str, column: str) -> bool:
    return any(r["name"] == column for r in c.execute(f"PRAGMA table_info({table})"))


def migrate():
    """Yangi ustun/jadvallarni qo'shadi. Bir necha marta chaqirsa ham xavfsiz."""
    with _conn() as c:
        if not _has_column(c, "users", "referred_by"):
            c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        if not _has_column(c, "users", "ref_credited"):
            # 0 = taklif qilgan odamga bonus hali berilmagan
            c.execute("ALTER TABLE users ADD COLUMN ref_credited INTEGER DEFAULT 0")
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event   TEXT,
                source  TEXT,
                at      TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_at ON events(at)")


def track(user_id: int, event: str, source: str = ""):
    """Voronka hodisasini yozadi. Xatolik bot ishini to'xtatmasligi kerak."""
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO events (user_id, event, source, at) VALUES (?, ?, ?, ?)",
                (user_id, event, source, datetime.now().isoformat()),
            )
    except sqlite3.Error:
        pass


# ---------- Referal ----------

def set_referrer(user_id: int, referrer_id: int) -> bool:
    """Yangi foydalanuvchiga taklif qilgan odamni bog'laydi.

    Faqat bir marta va faqat foydalanuvchi hali hech kimga bog'lanmagan bo'lsa.
    O'zini o'zi taklif qilish mumkin emas.
    """
    if user_id == referrer_id:
        return False
    with _conn() as c:
        row = c.execute(
            "SELECT referred_by FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None or row["referred_by"] is not None:
            return False
        # Taklif qiluvchi haqiqatan mavjud bo'lishi kerak.
        exists = c.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (referrer_id,)
        ).fetchone()
        if not exists:
            return False
        c.execute(
            "UPDATE users SET referred_by = ? WHERE user_id = ?",
            (referrer_id, user_id),
        )
    return True


def pending_referrer(user_id: int) -> int | None:
    """Shu foydalanuvchi uchun bonusi hali berilmagan taklif qiluvchini qaytaradi."""
    with _conn() as c:
        row = c.execute(
            "SELECT referred_by, ref_credited FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row or not row["referred_by"] or row["ref_credited"]:
        return None
    return int(row["referred_by"])


def mark_ref_credited(user_id: int):
    with _conn() as c:
        c.execute("UPDATE users SET ref_credited = 1 WHERE user_id = ?", (user_id,))


def referral_count(user_id: int) -> int:
    """Nechta odam shu foydalanuvchi havolasi orqali kelib, botdan foydalangan."""
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) n FROM users WHERE referred_by = ? AND ref_credited = 1",
            (user_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


# ---------- Voronka hisoboti ----------

def funnel(days: int = 30) -> dict:
    """Oxirgi N kundagi voronka: start -> foydalanish -> limit -> to'lov oynasi -> to'lov."""
    since = (datetime.now().timestamp() - days * 86400)
    since_iso = datetime.fromtimestamp(since).isoformat()
    out = {}
    with _conn() as c:
        for name in ("start", "action", "limit_hit", "invoice", "inline"):
            row = c.execute(
                "SELECT COUNT(DISTINCT user_id) n FROM events "
                "WHERE event = ? AND at >= ?",
                (name, since_iso),
            ).fetchone()
            out[name] = int(row["n"]) if row else 0
        row = c.execute(
            "SELECT COUNT(DISTINCT user_id) n FROM payments WHERE paid_at >= ?",
            (since_iso,),
        ).fetchone()
        out["paid"] = int(row["n"]) if row else 0
        row = c.execute(
            "SELECT COUNT(*) n FROM events WHERE event = 'inline' AND at >= ?",
            (since_iso,),
        ).fetchone()
        out["inline_uses"] = int(row["n"]) if row else 0
        row = c.execute(
            "SELECT COUNT(*) n FROM users WHERE referred_by IS NOT NULL AND ref_credited = 1"
        ).fetchone()
        out["referred_users"] = int(row["n"]) if row else 0
        today = date.today().isoformat()
        row = c.execute(
            "SELECT COUNT(*) n FROM events WHERE event = 'start' AND at >= ?",
            (today,),
        ).fetchone()
        out["starts_today"] = int(row["n"]) if row else 0
    return out


def top_sources(days: int = 30, limit: int = 8) -> list[tuple[str, int]]:
    """Yangi foydalanuvchilar qaysi manbadan kelgani (deep-link `start` parametri)."""
    since_iso = datetime.fromtimestamp(datetime.now().timestamp() - days * 86400).isoformat()
    with _conn() as c:
        rows = c.execute(
            "SELECT source, COUNT(DISTINCT user_id) n FROM events "
            "WHERE event = 'start' AND at >= ? AND source != '' "
            "GROUP BY source ORDER BY n DESC LIMIT ?",
            (since_iso, limit),
        ).fetchall()
    return [(r["source"], int(r["n"])) for r in rows]

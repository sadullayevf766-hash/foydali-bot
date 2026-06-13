"""SQLite ma'lumotlar bazasi: foydalanuvchilar, limitlar, premium."""
import sqlite3
from datetime import datetime, timedelta, date
from config import DB_PATH, FREE_DAILY_LIMIT


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                first_name   TEXT,
                joined_at    TEXT,
                premium_until TEXT,            -- ISO sana yoki NULL
                usage_date   TEXT,             -- oxirgi amal kuni (YYYY-MM-DD)
                usage_count  INTEGER DEFAULT 0 -- shu kungi amallar soni
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                stars      INTEGER,
                paid_at    TEXT
            )
        """)


def add_user(user_id: int, username: str, first_name: str):
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, datetime.now().isoformat()),
        )


def is_premium(user_id: int) -> bool:
    with _conn() as c:
        row = c.execute(
            "SELECT premium_until FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row or not row["premium_until"]:
        return False
    return datetime.fromisoformat(row["premium_until"]) > datetime.now()


def grant_premium(user_id: int, days: int):
    """Premiumni uzaytiradi (agar amal qilayotgan bo'lsa, ustiga qo'shadi)."""
    with _conn() as c:
        row = c.execute(
            "SELECT premium_until FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        base = datetime.now()
        if row and row["premium_until"]:
            current = datetime.fromisoformat(row["premium_until"])
            if current > base:
                base = current
        new_until = (base + timedelta(days=days)).isoformat()
        c.execute(
            "UPDATE users SET premium_until = ? WHERE user_id = ?",
            (new_until, user_id),
        )
    return new_until


def record_payment(user_id: int, stars: int):
    with _conn() as c:
        c.execute(
            "INSERT INTO payments (user_id, stars, paid_at) VALUES (?, ?, ?)",
            (user_id, stars, datetime.now().isoformat()),
        )


def remaining_quota(user_id: int) -> int:
    """Bugun yana nechta bepul amal qolganini qaytaradi. Premium = -1 (cheksiz)."""
    if is_premium(user_id):
        return -1
    today = date.today().isoformat()
    with _conn() as c:
        row = c.execute(
            "SELECT usage_date, usage_count FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row or row["usage_date"] != today:
        return FREE_DAILY_LIMIT
    return max(0, FREE_DAILY_LIMIT - row["usage_count"])


def consume_quota(user_id: int) -> bool:
    """Bitta amal hisoblaydi. True = ruxsat berildi, False = limit tugagan."""
    if is_premium(user_id):
        return True
    today = date.today().isoformat()
    with _conn() as c:
        row = c.execute(
            "SELECT usage_date, usage_count FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row or row["usage_date"] != today:
            c.execute(
                "UPDATE users SET usage_date = ?, usage_count = 1 WHERE user_id = ?",
                (today, user_id),
            )
            return True
        if row["usage_count"] >= FREE_DAILY_LIMIT:
            return False
        c.execute(
            "UPDATE users SET usage_count = usage_count + 1 WHERE user_id = ?",
            (user_id,),
        )
        return True


def stats() -> dict:
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        premium = c.execute(
            "SELECT COUNT(*) n FROM users WHERE premium_until > ?",
            (datetime.now().isoformat(),),
        ).fetchone()["n"]
        revenue = c.execute(
            "SELECT COALESCE(SUM(stars), 0) s FROM payments"
        ).fetchone()["s"]
        today = date.today().isoformat()
        active_today = c.execute(
            "SELECT COUNT(*) n FROM users WHERE usage_date = ?", (today,)
        ).fetchone()["n"]
    return {
        "total": total,
        "premium": premium,
        "revenue_stars": revenue,
        "active_today": active_today,
    }

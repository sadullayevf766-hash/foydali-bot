"""IELTS bot uchun baza qatlami.

Foydali Bot bilan bir xil ulanishdan (`storage.py`) foydalanadi, lekin
BARCHA jadval nomlari `ielts_` bilan boshlanadi — shu sababli ikkala bot
bir bazada yonma-yon yashaydi va bir-birining ma'lumotiga tegmaydi.

Sana/vaqt maydonlari ataylab MATN (ISO): SQLite va Postgres'da taqqoslash
mantiqi bir xil qoladi.
"""
from datetime import date, datetime, timedelta

import storage
from storage import conn as _conn

from . import config


def migrate():
    """Jadvallarni yaratadi. Necha marta chaqirilsa ham xavfsiz."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS ielts_users (
                user_id         BIGINT PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                lang            TEXT DEFAULT 'uz',
                credits         INTEGER DEFAULT 0,
                unlimited_until TEXT,
                joined_at       TEXT,
                referred_by     BIGINT,
                ref_credited    INTEGER DEFAULT 0,
                checks_total    INTEGER DEFAULT 0,
                usage_date      TEXT,
                usage_count     INTEGER DEFAULT 0,
                source          TEXT
            )
        """)
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS ielts_checks (
                id        {storage.autoincrement_pk()},
                user_id   BIGINT,
                task_type TEXT,
                overall   REAL,
                words     INTEGER,
                at        TEXT
            )
        """)
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS ielts_payments (
                id         {storage.autoincrement_pk()},
                user_id    BIGINT,
                plan       TEXT,
                amount     INTEGER,
                status     TEXT,
                at         TEXT,
                decided_at TEXT
            )
        """)
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS ielts_events (
                id      {storage.autoincrement_pk()},
                user_id BIGINT,
                event   TEXT,
                source  TEXT,
                at      TEXT
            )
        """)
        # Natija keshi. Sabab: bir xil insho har safar boshqacha ball olsa
        # (model 0 haroratda ham biroz tebranadi), foydalanuvchi vositaga
        # ishonmay qo'yadi. Kesh "bir xil kirish -> bir xil natija" ni
        # KAFOLATLAYDI va bepul kvotani ham tejaydi.
        c.execute("""
            CREATE TABLE IF NOT EXISTS ielts_cache (
                key    TEXT PRIMARY KEY,
                result TEXT,
                at     TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_ielts_ev ON ielts_events(event)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ielts_pay ON ielts_payments(status)")


def _insert_id(c, sql: str, params) -> int:
    """INSERT qilib, yangi yozuv id sini qaytaradi (ikkala bazada ham)."""
    if storage.IS_POSTGRES:
        return c.execute(sql + " RETURNING id", params).fetchone()["id"]
    return c.execute(sql, params).lastrowid


# ---------- Foydalanuvchi ----------

def add_user(user_id: int, username: str, first_name: str, source: str = "") -> bool:
    """Yangi bo'lsa qo'shadi va bepul kreditlarni beradi. True = yangi odam."""
    with _conn() as c:
        row = c.execute(
            "SELECT user_id FROM ielts_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            # Ism/username o'zgargan bo'lishi mumkin — yangilab qo'yamiz.
            c.execute(
                "UPDATE ielts_users SET username = ?, first_name = ? WHERE user_id = ?",
                (username, first_name, user_id),
            )
            return False
        c.execute(
            "INSERT INTO ielts_users "
            "(user_id, username, first_name, credits, joined_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                username,
                first_name,
                config.FREE_CHECKS,
                datetime.now().isoformat(),
                source,
            ),
        )
        return True


def get(user_id: int):
    with _conn() as c:
        return c.execute(
            "SELECT * FROM ielts_users WHERE user_id = ?", (user_id,)
        ).fetchone()


def set_lang(user_id: int, lang: str):
    with _conn() as c:
        c.execute("UPDATE ielts_users SET lang = ? WHERE user_id = ?", (lang, user_id))


def lang_of(user_id: int) -> str:
    row = get(user_id)
    return row["lang"] if row and row["lang"] else "uz"


# ---------- Kredit va limit ----------

def _unlimited_active(row) -> bool:
    if not row or not row["unlimited_until"]:
        return False
    return datetime.fromisoformat(row["unlimited_until"]) > datetime.now()


def balance(user_id: int) -> dict:
    """Foydalanuvchining hozirgi imkoniyati."""
    row = get(user_id)
    if not row:
        return {"credits": 0, "unlimited": False, "until": None,
                "today_left": 0, "checks_total": 0}
    unlimited = _unlimited_active(row)
    today_left = 0
    if unlimited:
        used = row["usage_count"] if row["usage_date"] == date.today().isoformat() else 0
        today_left = max(0, config.UNLIMITED_DAILY_CAP - (used or 0))
    return {
        "credits": row["credits"] or 0,
        "unlimited": unlimited,
        "until": row["unlimited_until"],
        "today_left": today_left,
        "checks_total": row["checks_total"] or 0,
    }


def can_check(user_id: int) -> bool:
    b = balance(user_id)
    if b["unlimited"]:
        return b["today_left"] > 0
    return b["credits"] > 0


def consume(user_id: int) -> bool:
    """Bitta tekshiruvni hisobdan yechadi.

    Faqat tekshiruv MUVAFFAQIYATLI tugagandan keyin chaqiriladi — model
    xato bersa foydalanuvchi kreditini yo'qotmasligi kerak.
    """
    today = date.today().isoformat()
    with _conn() as c:
        row = c.execute(
            "SELECT credits, unlimited_until, usage_date, usage_count "
            "FROM ielts_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return False
        unlimited = bool(
            row["unlimited_until"]
            and datetime.fromisoformat(row["unlimited_until"]) > datetime.now()
        )
        if unlimited:
            used = row["usage_count"] if row["usage_date"] == today else 0
            if (used or 0) >= config.UNLIMITED_DAILY_CAP:
                return False
            c.execute(
                "UPDATE ielts_users SET usage_date = ?, usage_count = ?, "
                "checks_total = checks_total + 1 WHERE user_id = ?",
                (today, (used or 0) + 1, user_id),
            )
            return True
        if (row["credits"] or 0) <= 0:
            return False
        c.execute(
            "UPDATE ielts_users SET credits = credits - 1, "
            "checks_total = checks_total + 1 WHERE user_id = ?",
            (user_id,),
        )
        return True


def add_credits(user_id: int, n: int):
    with _conn() as c:
        c.execute(
            "UPDATE ielts_users SET credits = COALESCE(credits, 0) + ? WHERE user_id = ?",
            (n, user_id),
        )


def grant_days(user_id: int, days: int) -> str:
    """Cheksiz tarifni uzaytiradi (amaldagisi bo'lsa — ustiga qo'shadi)."""
    with _conn() as c:
        row = c.execute(
            "SELECT unlimited_until FROM ielts_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        base = datetime.now()
        if row and row["unlimited_until"]:
            cur = datetime.fromisoformat(row["unlimited_until"])
            if cur > base:
                base = cur
        until = (base + timedelta(days=days)).isoformat()
        c.execute(
            "UPDATE ielts_users SET unlimited_until = ? WHERE user_id = ?",
            (until, user_id),
        )
    return until


def record_check(user_id: int, task_type: str, overall, words: int):
    with _conn() as c:
        c.execute(
            "INSERT INTO ielts_checks (user_id, task_type, overall, words, at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, task_type, overall, words, datetime.now().isoformat()),
        )


# ---------- To'lov ----------

def create_payment(user_id: int, plan: str, amount: int) -> int:
    with _conn() as c:
        return _insert_id(
            c,
            "INSERT INTO ielts_payments (user_id, plan, amount, status, at) "
            "VALUES (?, ?, ?, 'kutilmoqda', ?)",
            (user_id, plan, amount, datetime.now().isoformat()),
        )


def get_payment(pid: int):
    with _conn() as c:
        return c.execute("SELECT * FROM ielts_payments WHERE id = ?", (pid,)).fetchone()


def set_payment_status(pid: int, status: str) -> bool:
    """Holatni faqat 'kutilmoqda' dan o'zgartiradi.

    Shart muhim: admin tugmani ikki marta bossa ham tarif ikki marta
    berilib ketmasligi kerak.
    """
    with _conn() as c:
        cur = c.execute(
            "UPDATE ielts_payments SET status = ?, decided_at = ? "
            "WHERE id = ? AND status = 'kutilmoqda'",
            (status, datetime.now().isoformat(), pid),
        )
        return (cur.rowcount or 0) > 0


def pending_payments():
    with _conn() as c:
        return c.execute(
            "SELECT * FROM ielts_payments WHERE status = 'kutilmoqda' ORDER BY id"
        ).fetchall()


# ---------- Referal ----------

def set_referrer(user_id: int, referrer_id: int) -> bool:
    if user_id == referrer_id:
        return False
    with _conn() as c:
        row = c.execute(
            "SELECT referred_by FROM ielts_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or row["referred_by"]:
            return False
        exists = c.execute(
            "SELECT 1 FROM ielts_users WHERE user_id = ?", (referrer_id,)
        ).fetchone()
        if not exists:
            return False
        c.execute(
            "UPDATE ielts_users SET referred_by = ? WHERE user_id = ?",
            (referrer_id, user_id),
        )
        return True


def credit_referrer(user_id: int):
    """Taklif qilgan odamga bonus beradi — faqat bir marta va faqat taklif
    qilingan odam HAQIQIY tekshiruvdan o'tkazgandan keyin (soxta akkauntga
    qarshi). Qaytaradi: bonus olgan odam id si yoki None.
    """
    with _conn() as c:
        row = c.execute(
            "SELECT referred_by, ref_credited FROM ielts_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row or not row["referred_by"] or row["ref_credited"]:
            return None
        c.execute("UPDATE ielts_users SET ref_credited = 1 WHERE user_id = ?", (user_id,))
        c.execute(
            "UPDATE ielts_users SET credits = COALESCE(credits, 0) + ? WHERE user_id = ?",
            (config.REFERRAL_BONUS, row["referred_by"]),
        )
        return row["referred_by"]


def invited_count(user_id: int) -> int:
    with _conn() as c:
        return c.execute(
            "SELECT COUNT(*) n FROM ielts_users WHERE referred_by = ? AND ref_credited = 1",
            (user_id,),
        ).fetchone()["n"]


# ---------- Natija keshi ----------

def cache_get(key: str) -> str | None:
    try:
        with _conn() as c:
            row = c.execute(
                "SELECT result FROM ielts_cache WHERE key = ?", (key,)
            ).fetchone()
        return row["result"] if row else None
    except Exception:
        # Kesh yordamchi vosita — u ishlamasa baholash to'xtamasligi kerak.
        return None


def cache_put(key: str, result: str):
    try:
        with _conn() as c:
            c.execute(
                storage.insert_ignore(
                    "ielts_cache", "key, result, at", "?, ?, ?", "key"
                ),
                (key, result, datetime.now().isoformat()),
            )
    except Exception:
        pass


# ---------- Kuzatuv va hisobot ----------

def track(user_id: int, event: str, source: str = ""):
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO ielts_events (user_id, event, source, at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, event, source, datetime.now().isoformat()),
            )
    except Exception:
        pass


def stats() -> dict:
    today = date.today().isoformat()
    with _conn() as c:
        users = c.execute("SELECT COUNT(*) n FROM ielts_users").fetchone()["n"]
        checks = c.execute("SELECT COUNT(*) n FROM ielts_checks").fetchone()["n"]
        checks_today = c.execute(
            "SELECT COUNT(*) n FROM ielts_checks WHERE at >= ?", (today,)
        ).fetchone()["n"]
        paid = c.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(amount), 0) s FROM ielts_payments "
            "WHERE status = 'tasdiqlandi'"
        ).fetchone()
        pending = c.execute(
            "SELECT COUNT(*) n FROM ielts_payments WHERE status = 'kutilmoqda'"
        ).fetchone()["n"]
        buyers = c.execute(
            "SELECT COUNT(DISTINCT user_id) n FROM ielts_payments "
            "WHERE status = 'tasdiqlandi'"
        ).fetchone()["n"]
    return {
        "users": users,
        "checks": checks,
        "checks_today": checks_today,
        "sales": paid["n"],
        "revenue": paid["s"],
        "buyers": buyers,
        "pending": pending,
    }

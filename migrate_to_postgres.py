"""Mavjud SQLite ma'lumotini Postgres'ga ko'chiradi.

Ishlatish (bir marta):

    set DATABASE_URL=postgresql://...neon.tech/...
    venv\\Scripts\\python.exe migrate_to_postgres.py

Skript avval jadvallarni yaratadi, keyin bot.db dagi hamma yozuvni
ko'chiradi va oxirida sonlarni solishtirib tekshiradi. Qayta ishga
tushirish xavfsiz: mavjud yozuvlar takrorlanmaydi.
"""
import os
import sqlite3
import sys

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.db")

if not os.getenv("DATABASE_URL", "").strip():
    sys.exit(
        "DATABASE_URL o'rnatilmagan.\n"
        "Neon'dan connection string oling va shunday ishga tushiring:\n"
        '  set DATABASE_URL=postgresql://user:parol@host/dbname?sslmode=require\n'
        "  venv\\Scripts\\python.exe migrate_to_postgres.py"
    )

import storage
import db
import growth_db

if not storage.IS_POSTGRES:
    sys.exit("storage Postgres rejimida emas — DATABASE_URL ni tekshiring.")

print(f"Manba : SQLite  {SQLITE_PATH}")
print(f"Maqsad: {storage.label()}")

if not os.path.exists(SQLITE_PATH):
    print("\nbot.db topilmadi — ko'chiradigan ma'lumot yo'q.")
    print("Faqat jadvallar yaratiladi.")
    db.init_db()
    growth_db.migrate()
    print("Jadvallar tayyor ✅")
    sys.exit(0)

# 1. Postgres'da jadvallarni yaratamiz
db.init_db()
growth_db.migrate()
print("Jadvallar yaratildi.")

# 2. SQLite'dan o'qiymiz
src = sqlite3.connect(SQLITE_PATH)
src.row_factory = sqlite3.Row


def table_exists(name: str) -> bool:
    return src.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def columns_of(name: str) -> list[str]:
    return [r["name"] for r in src.execute(f"PRAGMA table_info({name})")]


copied = {}

# --- users ---
if table_exists("users"):
    cols = columns_of("users")
    rows = src.execute("SELECT * FROM users").fetchall()
    with storage.conn() as c:
        for r in rows:
            values = [r[col] for col in cols]
            placeholders = ", ".join("?" for _ in cols)
            c.execute(
                storage.insert_ignore(
                    "users", ", ".join(cols), placeholders, "user_id"
                ),
                tuple(values),
            )
    copied["users"] = len(rows)

# --- payments (id ni ko'chirmaymiz, Postgres o'zi beradi) ---
if table_exists("payments"):
    rows = src.execute(
        "SELECT user_id, stars, paid_at FROM payments ORDER BY id"
    ).fetchall()
    with storage.conn() as c:
        existing = c.execute("SELECT COUNT(*) n FROM payments").fetchone()["n"]
        if existing:
            print(f"  payments: Postgres'da allaqachon {existing} yozuv bor, o'tkazib yuborildi.")
            rows = []
        for r in rows:
            c.execute(
                "INSERT INTO payments (user_id, stars, paid_at) VALUES (?, ?, ?)",
                (r["user_id"], r["stars"], r["paid_at"]),
            )
    copied["payments"] = len(rows)

# --- events ---
if table_exists("events"):
    rows = src.execute(
        "SELECT user_id, event, source, at FROM events ORDER BY id"
    ).fetchall()
    with storage.conn() as c:
        existing = c.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
        if existing:
            print(f"  events: Postgres'da allaqachon {existing} yozuv bor, o'tkazib yuborildi.")
            rows = []
        for r in rows:
            c.execute(
                "INSERT INTO events (user_id, event, source, at) VALUES (?, ?, ?, ?)",
                (r["user_id"], r["event"], r["source"], r["at"]),
            )
    copied["events"] = len(rows)

src.close()

# 3. Tekshiruv — nafaqat sonlar, balki asosiy so'rovlar ham ishlashi kerak
print("\nKo'chirildi:", copied or "(bo'sh)")
with storage.conn() as c:
    users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    pays = c.execute("SELECT COUNT(*) n FROM payments").fetchone()["n"]
print(f"Postgres holati: {users} foydalanuvchi, {pays} to'lov")

s = db.stats()
f = growth_db.funnel(30)
print(f"stats() ishladi : {s}")
print(f"funnel() ishladi: start={f['start']} action={f['action']} paid={f['paid']}")
print("\nKo'chirish tugadi ✅")
print("Endi Render'da DATABASE_URL o'zgaruvchisini o'rnating va qayta deploy qiling.")

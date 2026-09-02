"""Baza qatlami: SQLite (lokal) va Postgres (bulut) bir xil interfeys bilan.

Nega kerak: Render bepul tarifida fayl tizimi vaqtinchalik — har uyquga
ketganda yoki qayta deploy qilinganda SQLite fayli o'chadi. Pul to'lagan
foydalanuvchi Premium'ini yo'qotishi mumkin emas, shuning uchun bulutda
ma'lumot tashqi Postgres'da (Neon) saqlanadi.

`DATABASE_URL` o'zgaruvchisi bo'lsa Postgres, bo'lmasa SQLite ishlatiladi.
Shu sababli lokal ishlash va testlar hech narsa sozlamasdan davom etadi.
"""
import os
import sqlite3
from contextlib import contextmanager

from config import DB_PATH

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row


class _Cursor:
    """Ikkala bazada ham bir xil ishlaydigan o'ram.

    Yagona farq — parametr belgisi: SQLite `?`, Postgres `%s`. Shuni shu
    yerda almashtiramiz, natijada qolgan kod ikkala baza uchun bir xil.
    """

    def __init__(self, raw, is_pg: bool):
        self._raw = raw
        self._is_pg = is_pg

    def execute(self, sql: str, params=()):
        if self._is_pg:
            sql = sql.replace("?", "%s")
        return self._raw.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._raw, name)


@contextmanager
def conn():
    """Tranzaksiya. Muvaffaqiyatli tugasa commit, xato bo'lsa rollback."""
    if IS_POSTGRES:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as raw:
            yield _Cursor(raw, True)
    else:
        raw = sqlite3.connect(DB_PATH)
        raw.row_factory = sqlite3.Row
        try:
            with raw:
                yield _Cursor(raw, False)
        finally:
            raw.close()


def autoincrement_pk() -> str:
    """Avtomatik o'suvchi birlamchi kalit ta'rifi."""
    return "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def insert_ignore(table: str, columns: str, placeholders: str, pk: str) -> str:
    """Mavjud yozuvni takrorlamaydigan INSERT."""
    if IS_POSTGRES:
        return (
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT ({pk}) DO NOTHING"
        )
    return f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})"


def has_column(c, table: str, column: str) -> bool:
    if IS_POSTGRES:
        row = c.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = ? AND column_name = ?",
            (table, column),
        ).fetchone()
        return row is not None
    return any(r["name"] for r in c.execute(f"PRAGMA table_info({table})")
               if r["name"] == column)


def add_column(c, table: str, column: str, definition: str):
    """Ustunni qo'shadi, allaqachon bo'lsa jim o'tadi."""
    if IS_POSTGRES:
        c.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
    elif not has_column(c, table, column):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def label() -> str:
    return "Postgres" if IS_POSTGRES else f"SQLite ({DB_PATH})"

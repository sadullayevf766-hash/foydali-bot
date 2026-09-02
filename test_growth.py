"""Referal va voronka mantiqini nusxa bazada sinaydi. Haqiqiy bot.db ga tegmaydi.

DATABASE_URL o'rnatilgan bo'lsa Postgres'da, aks holda vaqtinchalik
SQLite faylida ishlaydi.
"""
import os
import shutil
import tempfile

tmp = tempfile.mkdtemp()
# config DB_PATH ni env dan o'qiydi — import qilishdan OLDIN o'rnatamiz.
os.environ["DB_PATH"] = os.path.join(tmp, "test.db")

import storage
import db
import growth_db

print(f"Baza: {storage.label()}")

# Test ID lari — haqiqiy Telegram ID lari bunchalik kichik bo'lmaydi, shuning
# uchun to'qnashuv xavfi yo'q. Postgres'da sinaganda haqiqiy bazaga yozamiz,
# shuning uchun oxirida (va boshida) shu yozuvlarni tozalaymiz.
TEST_IDS = (111, 222, 333, 999)


def cleanup():
    with storage.conn() as c:
        for table, col in (("events", "user_id"), ("payments", "user_id"), ("users", "user_id")):
            for uid in TEST_IDS:
                try:
                    c.execute(f"DELETE FROM {table} WHERE {col} = ?", (uid,))
                except Exception:
                    pass  # jadval hali yaratilmagan bo'lishi mumkin


db.init_db()
growth_db.migrate()
growth_db.migrate()  # ikki marta chaqirish xavfsiz bo'lishi kerak
print("migratsiya: OK (ikki marta chaqirildi)")

cleanup()  # oldingi sinovdan qolgan yozuvlar bo'lsa

ALICE, BOB, MALLORY = 111, 222, 333
db.add_user(ALICE, "alice", "Alice")
db.add_user(BOB, "bob", "Bob")
db.add_user(ALICE, "alice", "Alice")  # takror qo'shish yozuvni buzmasligi kerak
assert db.stats()["total"] >= 2
print("foydalanuvchi qo'shish (takror ham): OK")

# 1. Oddiy referal
assert growth_db.set_referrer(BOB, ALICE) is True, "referal bog'lanishi kerak edi"
assert growth_db.pending_referrer(BOB) == ALICE
print("referal bog'landi: OK")

# 2. Ikkinchi marta bog'lash mumkin emas
db.add_user(MALLORY, "m", "M")
assert growth_db.set_referrer(BOB, MALLORY) is False, "qayta bog'lash mumkin emas"
print("qayta bog'lanish bloklandi: OK")

# 3. O'zini o'zi taklif qilish mumkin emas
assert growth_db.set_referrer(ALICE, ALICE) is False
print("o'z-o'zini taklif bloklandi: OK")

# 4. Mavjud bo'lmagan taklifchi
db.add_user(999, "x", "X")
assert growth_db.set_referrer(999, 555555) is False, "mavjud bo'lmagan taklifchi"
print("soxta taklifchi bloklandi: OK")

# 5. Bonus faqat bir marta
assert growth_db.referral_count(ALICE) == 0, "amal qilinmaguncha hisoblanmaydi"
growth_db.mark_ref_credited(BOB)
db.grant_premium(ALICE, growth_db.REF_BONUS_DAYS)
assert growth_db.referral_count(ALICE) == 1
assert growth_db.pending_referrer(BOB) is None, "bonus ikkinchi marta berilmasligi kerak"
assert db.is_premium(ALICE) is True, "taklifchi Premium olishi kerak"
print("bonus bir marta berildi va Premium yoqildi: OK")

# 6. Kvota: bepul limit tugagach False qaytarishi kerak
for i in range(config_limit := __import__("config").FREE_DAILY_LIMIT):
    assert db.consume_quota(BOB) is True, f"{i+1}-amal ruxsat etilishi kerak"
assert db.consume_quota(BOB) is False, "limitdan keyin rad etilishi kerak"
assert db.remaining_quota(BOB) == 0
# Premium egasi limitga tushmaydi
assert db.consume_quota(ALICE) is True and db.remaining_quota(ALICE) == -1
print(f"kvota ({config_limit}/kun) va Premium cheksizligi: OK")

# 7. Voronka
for ev in ("start", "action", "limit_hit", "invoice"):
    growth_db.track(BOB, ev, "referal")
growth_db.track(ALICE, "start", "guruh")
f = growth_db.funnel(30)
assert f["start"] == 2, f
assert f["action"] == 1, f
assert f["limit_hit"] == 1, f
assert f["invoice"] == 1, f
assert f["paid"] == 0, f
assert f["referred_users"] == 1, f
print("voronka:", {k: f[k] for k in ("start", "action", "limit_hit", "invoice", "paid")})

# 8. Manbalar
srcs = dict(growth_db.top_sources(30))
assert srcs.get("referal") == 1 and srcs.get("guruh") == 1, srcs
print("manbalar:", srcs)

# 9. To'lov voronkaga tushishi kerak
db.record_payment(BOB, 25)
f2 = growth_db.funnel(30)
assert f2["paid"] == 1, f2
assert db.stats()["revenue_stars"] >= 25
print("to'lov voronkada va statistikada: OK")

cleanup()
shutil.rmtree(tmp, ignore_errors=True)
print("\nHAMMA TEST O'TDI ✅")
if storage.IS_POSTGRES:
    print("Postgres yo'li tekshirildi, sinov yozuvlari tozalandi.")

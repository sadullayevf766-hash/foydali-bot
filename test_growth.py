"""Referal va voronka mantiqini nusxa bazada sinaydi. Haqiqiy bot.db ga tegmaydi."""
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

tmp = tempfile.mkdtemp()
test_db = os.path.join(tmp, "test.db")
os.environ["DB_PATH"] = test_db

import config
config.DB_PATH = test_db
import db
db.DB_PATH = test_db
import growth_db
growth_db.DB_PATH = test_db

db.init_db()
growth_db.migrate()
growth_db.migrate()  # ikki marta chaqirish xavfsiz bo'lishi kerak
print("migratsiya: OK (ikki marta chaqirildi)")

ALICE, BOB, MALLORY = 111, 222, 333
db.add_user(ALICE, "alice", "Alice")
db.add_user(BOB, "bob", "Bob")

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

# 6. Voronka
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

# 7. Manbalar
srcs = dict(growth_db.top_sources(30))
assert srcs.get("referal") == 1 and srcs.get("guruh") == 1, srcs
print("manbalar:", srcs)

# 8. To'lov voronkaga tushishi kerak
db.record_payment(BOB, 25)
f2 = growth_db.funnel(30)
assert f2["paid"] == 1, f2
print("to'lov voronkada ko'rindi: OK")

# 9. Eski bazada ham migratsiya ishlashi kerak (ustunlarsiz baza)
old = os.path.join(tmp, "old.db")
con = sqlite3.connect(old)
con.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT, "
            "first_name TEXT, joined_at TEXT, premium_until TEXT, usage_date TEXT, "
            "usage_count INTEGER DEFAULT 0)")
con.execute("CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, "
            "stars INTEGER, paid_at TEXT)")
con.execute("INSERT INTO users VALUES (1,'a','A',?,NULL,NULL,0)", (datetime.now().isoformat(),))
con.commit(); con.close()
growth_db.DB_PATH = old
growth_db.migrate()
cols = [r[1] for r in sqlite3.connect(old).execute("PRAGMA table_info(users)")]
assert "referred_by" in cols and "ref_credited" in cols, cols
print("eski bazaga migratsiya: OK")

shutil.rmtree(tmp, ignore_errors=True)
print("\nHAMMA TEST O'TDI ✅")

"""IELTS bot uchun sinovlar — tarmoqsiz, vaqtinchalik bazada.

Ishga tushirish:  python test_ielts.py
Postgres'da tekshirish uchun DATABASE_URL bilan ishga tushiring.
"""
import os
import sys
import tempfile

# Bazani vaqtinchalik faylga yo'naltiramiz — haqiqiy bot.db ga tegmaymiz.
if not os.getenv("DATABASE_URL"):
    os.environ["DB_PATH"] = os.path.join(tempfile.gettempdir(), "ielts_test.db")
    if os.path.exists(os.environ["DB_PATH"]):
        os.remove(os.environ["DB_PATH"])

from ielts import config, db, grader  # noqa: E402
from ielts.bot import format_result  # noqa: E402

UID = 999_000_111
REF = 999_000_222
ok_count = 0


def check(name, cond):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  ok  {name}")
    else:
        print(f"  XATO {name}")
        raise SystemExit(1)


def cleanup():
    from storage import conn
    with conn() as c:
        for t in ("ielts_events", "ielts_checks", "ielts_payments", "ielts_users"):
            c.execute(f"DELETE FROM {t} WHERE user_id IN (?, ?)", (UID, REF))


print("1) Baza yaratilishi")
db.migrate()
db.migrate()  # ikkinchi marta ham xavfsiz bo'lishi kerak
cleanup()
check("migrate ikki marta ishladi", True)

print("2) Foydalanuvchi va bepul kreditlar")
check("yangi foydalanuvchi", db.add_user(UID, "test", "Test") is True)
check("takroriy qo'shish yangi emas", db.add_user(UID, "test", "Test") is False)
check(f"bepul {config.FREE_CHECKS} kredit", db.balance(UID)["credits"] == config.FREE_CHECKS)

print("3) Kredit yechish")
check("tekshirish mumkin", db.can_check(UID) is True)
for i in range(config.FREE_CHECKS):
    check(f"kredit {i+1} yechildi", db.consume(UID) is True)
check("kreditlar tugadi", db.can_check(UID) is False)
check("bo'sh hisobdan yechilmaydi", db.consume(UID) is False)
check("checks_total sanaldi", db.balance(UID)["checks_total"] == config.FREE_CHECKS)

print("4) Kredit qo'shish va cheksiz tarif")
db.add_credits(UID, 5)
check("5 kredit qo'shildi", db.balance(UID)["credits"] == 5)
db.grant_days(UID, 30)
b = db.balance(UID)
check("cheksiz yoqildi", b["unlimited"] is True)
check("kunlik chegara bor", b["today_left"] == config.UNLIMITED_DAILY_CAP)
for _ in range(config.UNLIMITED_DAILY_CAP):
    db.consume(UID)
check("kunlik chegara ishladi", db.can_check(UID) is False)

print("5) To'lov oqimi")
pid = db.create_payment(REF, "pro", 49000)
check("to'lov yaratildi", isinstance(pid, int) and pid > 0)
check("holati kutilmoqda", db.get_payment(pid)["status"] == "kutilmoqda")
check("tasdiqlash ishladi", db.set_payment_status(pid, "tasdiqlandi") is True)
check("IKKINCHI marta tasdiqlanmaydi", db.set_payment_status(pid, "tasdiqlandi") is False)

print("6) Referal")
db.add_user(REF, "ref", "Ref")
db.add_user(UID + 1, "yangi", "Yangi")
check("referrer bog'landi", db.set_referrer(UID + 1, REF) is True)
check("ikkinchi marta bog'lanmaydi", db.set_referrer(UID + 1, REF) is False)
check("o'zini o'zi taklif qilolmaydi", db.set_referrer(REF, REF) is False)
before = db.balance(REF)["credits"]
check("bonus berildi", db.credit_referrer(UID + 1) == REF)
check("bonus faqat bir marta", db.credit_referrer(UID + 1) is None)
check("kredit oshdi", db.balance(REF)["credits"] == before + config.REFERRAL_BONUS)

print("7) IELTS yaxlitlash qoidasi")
cases = [(6.0, 6.0), (6.125, 6.0), (6.25, 6.5), (6.5, 6.5), (6.74, 6.5),
         (6.75, 7.0), (6.875, 7.0), (5.375, 5.5)]
for raw, want in cases:
    got = grader.round_band(raw)
    check(f"{raw} -> {want}", got == want)

print("8) Model javobini normallashtirish")
raw = {
    "word_count": 260, "off_topic": False, "memorised": False,
    "criteria": [
        {"key": "tr", "band": 6.0, "comment": "Position is clear."},
        {"key": "CC", "band": 6.5, "comment": "Paragraphing works."},
        {"key": "LR", "band": 6.0, "comment": "Limited range."},
        {"key": "GRA", "band": 5.5, "comment": "Frequent errors."},
    ],
    "errors": [{"quote": "people is", "fix": "people are", "why": "plural"},
               {"quote": "", "fix": "x", "why": "y"}],
    "upgrades": ["a", "b", "c", "d"],
    "improved_paragraph": {"original": "orig", "improved": "better"},
    "summary": "Solid but grammar holds you back.",
}
essay = " ".join(["word"] * 260)
r = grader._normalise(raw, "task2", essay, False)
check("umumiy ball kodda hisoblandi (6.0)", r["overall"] == 6.0)
check("kichik harfli kalit tanildi", r["criteria"][0]["key"] == "TR")
check("mezon nomi qo'shildi", r["criteria"][0]["name"] == "Task Response")
check("bo'sh iqtibos tashlandi", len(r["errors"]) == 1)
check("upgrades 3 ta bilan cheklandi", len(r["upgrades"]) == 3)
check("so'zlar kodda sanaldi", r["words"] == 260)

print("9) Mezon yetishmasa xato")
bad = dict(raw, criteria=raw["criteria"][:3])
try:
    grader._normalise(bad, "task2", essay, False)
    check("xato ko'tarilishi kerak edi", False)
except grader.GraderError:
    check("yetishmagan mezon aniqlandi", True)

print("10) Natijani chiqarish (HTML va uzunlik)")
out = format_result(r, "uz", {"credits": 3, "unlimited": False, "today_left": 0})
check("ball ko'rinadi", "6.0" in out)
check("ogohlantirish bor", "Taxminiy" in out)
check("HTML buzilmagan", out.count("<b>") == out.count("</b>"))
out_en = format_result(r, "en", {"credits": 0, "unlimited": True, "today_left": 4})
check("inglizcha ishlaydi", "Estimated" in out_en)

print("11) HTML xavfsizligi (foydalanuvchi matni)")
evil = dict(r)
evil["summary"] = "<script>alert(1)</script> & <b>x"
out = format_result(evil, "uz", {"credits": 1, "unlimited": False, "today_left": 0})
check("teg qochirildi", "<script>" not in out and "&lt;script&gt;" in out)

print("12) So'z sanash")
check("bo'sh matn 0", grader.count_words("   ") == 0)
check("ko'p bo'sh joy", grader.count_words("a   b\n\nc") == 3)

cleanup()
print(f"\n✅ {ok_count} ta tekshiruv o'tdi")
sys.exit(0)

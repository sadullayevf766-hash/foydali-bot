"""IELTS bot sozlamalari. Hammasi .env / Render env dan o'qiladi."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Telegram ---
BOT_TOKEN = os.getenv("IELTS_BOT_TOKEN", "").strip()
# Alohida admin ko'rsatilmasa, Foydali Bot admini ishlatiladi.
ADMIN_ID = int(os.getenv("IELTS_ADMIN_ID") or os.getenv("ADMIN_ID") or "0")
BOT_USERNAME = os.getenv("IELTS_BOT_USERNAME", "").strip().lstrip("@")

# --- Sun'iy intellekt ---
# Asosiy yo'l: Google AI Studio (bepul tarif, karta talab qilmaydi).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
# Zaxira yo'l: Gemini mintaqada ishlamasa OpenRouter bepul modellari.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
).strip()

# --- To'lov (mahalliy karta) ---
CARD_NUMBER = os.getenv("CARD_NUMBER", "").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "").strip()
# Foydalanuvchi muammo bilan murojaat qiladigan manzil, masalan @username.
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "").strip()

# --- Iqtisod ---
# Bepul tekshiruv: ikkita — biri Task 1 ga, biri Task 2 ga yetadi.
# Bittasi qiymatni ko'rsatishga kamlik qiladi, uchtasi esa pul to'lash
# sababini yo'qotadi.
FREE_CHECKS = int(os.getenv("IELTS_FREE_CHECKS") or "2")
# Do'st HAQIQATAN tekshiruvdan o'tkazgandagina beriladi (soxta akkauntga qarshi).
REFERRAL_BONUS = int(os.getenv("IELTS_REFERRAL_BONUS") or "1")
# Cheksiz tarifda kunlik adolatli foydalanish chegarasi.
UNLIMITED_DAILY_CAP = int(os.getenv("IELTS_UNLIMITED_CAP") or "5")

# Insho chegaralari — juda qisqa matn baholanmaydi (kredit ham yechilmaydi),
# juda uzuni esa modelga ortiqcha yuk va bepul kvotani tez tugatadi.
MIN_WORDS = 40
MAX_CHARS = 12000

# Tariflar. Narx so'mda. `checks=None` => muddatli cheksiz tarif.
PLANS = {
    "start": {
        "title": "Boshlang'ich",
        "title_en": "Starter",
        "checks": 5,
        "days": None,
        "price": 19000,
    },
    "pro": {
        "title": "Pro",
        "title_en": "Pro",
        "checks": 20,
        "days": None,
        "price": 49000,
    },
    "month": {
        "title": "30 kun cheksiz",
        "title_en": "30 days unlimited",
        "checks": None,
        "days": 30,
        "price": 79000,
    },
}


def missing() -> list[str]:
    """Ishga tushirishga yetishmayotgan sozlamalar ro'yxati."""
    gaps = []
    if not BOT_TOKEN:
        gaps.append("IELTS_BOT_TOKEN")
    if not (GEMINI_API_KEY or OPENROUTER_API_KEY):
        gaps.append("GEMINI_API_KEY")
    return gaps

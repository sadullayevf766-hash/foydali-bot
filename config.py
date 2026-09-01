"""Sozlamalar. Maxfiy ma'lumotlar .env faylidan o'qiladi."""
import os
from dotenv import load_dotenv

# Bu fayl joylashgan papka (qaysi joydan ishga tushishidan qat'i nazar to'g'ri ishlasin)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env ni shu papkadan o'qiymiz (CWD boshqa bo'lsa ham)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# BotFather'dan olingan token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin Telegram ID (siz). /stats kabi buyruqlar uchun.
ADMIN_ID = int(os.getenv("ADMIN_ID") or "0")

# --- Monetizatsiya ---
# Bepul foydalanuvchi kuniga nechta "og'ir" amal qila oladi (PDF, birlashtirish)
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT") or "5")

# Premium narxi (Telegram Stars / XTR). 30 kunlik.
PREMIUM_PRICE_STARS = int(os.getenv("PREMIUM_PRICE_STARS") or "25")
PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS") or "30")

# Ikkinchi tarif: uzoqroq muddat, bir Stardan arzonroq.
# Ikki narx bo'lgani qimmatrog'ini oqilona ko'rsatadi va o'rtacha
# tushumni oshiradi.
PREMIUM_YEAR_PRICE_STARS = int(os.getenv("PREMIUM_YEAR_PRICE_STARS") or "150")
PREMIUM_YEAR_DAYS = int(os.getenv("PREMIUM_YEAR_DAYS") or "365")

# Inline QR uchun saqlash chati. Inline javob ichida fayl yuklab bo'lmaydi,
# shuning uchun rasm avval shu chatga yuborilib, file_id olinadi.
# Bo'sh bo'lsa inline QR o'chiq qoladi, qolgan inline natijalar ishlaydi.
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID") or "0")

# Markaziy bank valyuta API (bepul, ochiq)
CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"

DB_PATH = os.getenv("DB_PATH") or os.path.join(BASE_DIR, "bot.db")

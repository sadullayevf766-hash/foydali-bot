"""Foydali Bot — asosiy fayl. Ishga tushirish: python bot.py"""
import os
import sys
import socket
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    LabeledPrice,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

import config
import db
import utils

# Loglar: konsolga VA faylga (bot.log) yoziladi — pythonw/avtoyuklashda ham ko'rinadi
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")
logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(_LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"),
    ],
)
log = logging.getLogger("foydali-bot")

# Bitta nusxa qulfi: ikkinchi nusxa ishga tushsa, darhol chiqib ketadi
# (Telegram'da bir vaqtda faqat bitta getUpdates ruxsat etiladi — 409 oldini oladi)
_instance_lock = None


def _ensure_single_instance():
    global _instance_lock
    _instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _instance_lock.bind(("127.0.0.1", 47654))
        _instance_lock.listen(1)
    except OSError:
        log.warning("Bot allaqachon ishlayapti — bu nusxa to'xtatildi.")
        sys.exit(0)


class _HealthHandler(BaseHTTPRequestHandler):
    """Render kabi bulutli xizmatlar uchun oddiy 'health' javobi (200 OK).
    Bu, shuningdek, xizmat uxlab qolmasligi uchun 'ping' nishoni bo'lib xizmat qiladi."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write("Foydali Bot ishlayapti ✅".encode("utf-8"))

    def log_message(self, *args):
        pass  # log'larni jim qoldiramiz


def _start_health_server():
    """PORT env mavjud bo'lsa (Render/bulut), HTTP server ishga tushiramiz."""
    port = os.environ.get("PORT")
    if not port:
        return
    try:
        server = HTTPServer(("0.0.0.0", int(port)), _HealthHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        log.info(f"Health server {port}-portda ishga tushdi (bulut rejimi)")
    except Exception:
        log.exception("Health server ishga tushmadi")

# Tugmalar matni
B_PDF = "📄 Rasm → PDF"
B_MERGE = "🔗 PDF birlashtirish"
B_QR = "⚡ QR-kod"
B_RATES = "💱 Valyuta kursi"
B_PREMIUM = "💎 Premium"
B_DONE = "✅ Tayyor"
B_CANCEL = "❌ Bekor qilish"

# Telegram bot API orqali yuklab olish chegarasi: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024

MAIN_KB = ReplyKeyboardMarkup(
    [[B_PDF, B_MERGE], [B_QR, B_RATES], [B_PREMIUM]],
    resize_keyboard=True,
)
DONE_KB = ReplyKeyboardMarkup(
    [[B_DONE], [B_CANCEL]], resize_keyboard=True
)


def reset(context):
    context.user_data["mode"] = None
    context.user_data["images"] = []
    context.user_data["pdfs"] = []


# ---------- Buyruqlar ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.add_user(u.id, u.username or "", u.first_name or "")
    reset(context)
    text = (
        f"Assalomu alaykum, {u.first_name}! 👋\n\n"
        "Men *Foydali Bot*man. Quyidagilarni qila olaman:\n\n"
        "📄 *Rasm → PDF* — rasmlarni bitta PDF qilaman\n"
        "🔗 *PDF birlashtirish* — bir nechta PDF'ni bitta qilaman\n"
        "⚡ *QR-kod* — istalgan matn/havoladan QR\n"
        "💱 *Valyuta kursi* — Markaziy bank kursi\n\n"
        "Pastdagi tugmalardan birini tanlang 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KB)


async def premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db.is_premium(user_id):
        await update.message.reply_text(
            "✅ Sizda *Premium* faol! Cheksiz foydalaning.",
            parse_mode="Markdown",
            reply_markup=MAIN_KB,
        )
        return
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="💎 Premium obuna",
        description=(
            f"{config.PREMIUM_DAYS} kun cheksiz foydalanish. "
            "Kunlik limitlarsiz PDF va birlashtirish."
        ),
        payload="premium_30",
        provider_token="",  # Telegram Stars uchun bo'sh qoldiriladi
        currency="XTR",
        prices=[LabeledPrice("Premium", config.PREMIUM_PRICE_STARS)],
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        return
    s = db.stats()
    await update.message.reply_text(
        f"📊 *Statistika*\n\n"
        f"👥 Jami foydalanuvchi: {s['total']}\n"
        f"🟢 Bugun faol: {s['active_today']}\n"
        f"💎 Premium: {s['premium']}\n"
        f"⭐ Daromad: {s['revenue_stars']} Stars",
        parse_mode="Markdown",
    )


# ---------- Tugma / matn ----------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == B_CANCEL:
        reset(context)
        await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KB)
        return

    if text == B_PDF:
        reset(context)
        context.user_data["mode"] = "pdf"
        await update.message.reply_text(
            "📄 Rasmlarni yuboring (bittadan yoki bir nechta). "
            "Tugagach *✅ Tayyor* tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=DONE_KB,
        )
        return

    if text == B_MERGE:
        reset(context)
        context.user_data["mode"] = "merge"
        await update.message.reply_text(
            "🔗 PDF fayllarni yuboring (fayl sifatida). "
            "Tugagach *✅ Tayyor* tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=DONE_KB,
        )
        return

    if text == B_QR:
        reset(context)
        context.user_data["mode"] = "qr"
        await update.message.reply_text(
            "⚡ QR-kodga aylantirmoqchi bo'lgan matn yoki havolani yuboring:",
            reply_markup=MAIN_KB,
        )
        return

    if text == B_RATES:
        reset(context)
        try:
            msg = await utils.get_rates()
        except Exception:
            msg = "❌ Kurs olishda xatolik. Birozdan keyin urinib ko'ring."
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=MAIN_KB)
        return

    if text == B_PREMIUM:
        await premium_cmd(update, context)
        return

    if text == B_DONE:
        await finish(update, context)
        return

    # QR rejimida oddiy matn kelsa
    if context.user_data.get("mode") == "qr":
        png = utils.make_qr(text)
        await update.message.reply_photo(
            photo=InputFile(png, filename="qr.png"),
            caption="✅ Tayyor! QR-kodingiz.",
            reply_markup=MAIN_KB,
        )
        reset(context)
        return

    # Hech qaysi rejimda emas
    await update.message.reply_text(
        "Tugmalardan birini tanlang 👇", reply_markup=MAIN_KB
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "pdf":
        await update.message.reply_text(
            "Rasmni PDF qilish uchun avval 📄 *Rasm → PDF* tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=MAIN_KB,
        )
        return
    photo = update.message.photo[-1]  # eng yuqori sifat
    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            "⚠️ Rasm juda katta (20 MB dan ortiq). Kichikroq rasm yuboring."
        )
        return
    file = await context.bot.get_file(photo.file_id)
    data = bytes(await file.download_as_bytearray())
    context.user_data.setdefault("images", []).append(data)
    n = len(context.user_data["images"])
    await update.message.reply_text(
        f"✅ {n}-rasm qabul qilindi. Yana yuboring yoki *✅ Tayyor* bosing.",
        parse_mode="Markdown",
        reply_markup=DONE_KB,
    )


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if context.user_data.get("mode") != "merge":
        await update.message.reply_text(
            "PDF birlashtirish uchun avval 🔗 *PDF birlashtirish* tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=MAIN_KB,
        )
        return
    if not (doc.mime_type == "application/pdf" or doc.file_name.lower().endswith(".pdf")):
        await update.message.reply_text("❌ Bu PDF fayl emas. PDF yuboring.")
        return
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            "⚠️ Bu fayl juda katta (20 MB dan ortiq). "
            "Telegram botlari katta fayllarni qabul qila olmaydi. "
            "Iltimos, kichikroq PDF yuboring."
        )
        return
    file = await context.bot.get_file(doc.file_id)
    data = bytes(await file.download_as_bytearray())
    context.user_data.setdefault("pdfs", []).append(data)
    n = len(context.user_data["pdfs"])
    await update.message.reply_text(
        f"✅ {n}-PDF qabul qilindi. Yana yuboring yoki *✅ Tayyor* bosing.",
        parse_mode="Markdown",
        reply_markup=DONE_KB,
    )


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = context.user_data.get("mode")

    if mode == "pdf":
        images = context.user_data.get("images", [])
        if not images:
            await update.message.reply_text("Avval rasm yuboring.", reply_markup=DONE_KB)
            return
        if not db.consume_quota(user_id):
            await _limit_reached(update)
            return
        try:
            pdf = utils.images_to_pdf(images)
        except Exception as e:
            log.exception("PDF xatolik")
            await update.message.reply_text("❌ PDF yasashda xatolik.", reply_markup=MAIN_KB)
            reset(context)
            return
        await update.message.reply_document(
            document=InputFile(pdf, filename="hujjat.pdf"),
            caption=_quota_caption(user_id),
            parse_mode="Markdown",
            reply_markup=MAIN_KB,
        )
        reset(context)
        return

    if mode == "merge":
        pdfs = context.user_data.get("pdfs", [])
        if len(pdfs) < 2:
            await update.message.reply_text(
                "Birlashtirish uchun kamida 2 ta PDF kerak.", reply_markup=DONE_KB
            )
            return
        if not db.consume_quota(user_id):
            await _limit_reached(update)
            return
        try:
            merged = utils.merge_pdfs(pdfs)
        except Exception:
            log.exception("Merge xatolik")
            await update.message.reply_text("❌ Birlashtirvishda xatolik.", reply_markup=MAIN_KB)
            reset(context)
            return
        await update.message.reply_document(
            document=InputFile(merged, filename="birlashtirilgan.pdf"),
            caption=_quota_caption(user_id),
            parse_mode="Markdown",
            reply_markup=MAIN_KB,
        )
        reset(context)
        return

    await update.message.reply_text("Avval amalni tanlang.", reply_markup=MAIN_KB)


def _quota_caption(user_id: int) -> str:
    left = db.remaining_quota(user_id)
    if left == -1:
        return "✅ Tayyor! (💎 Premium — cheksiz)"
    return f"✅ Tayyor!\n\nBugun yana {left} ta bepul amal qoldi."


async def _limit_reached(update: Update):
    await update.message.reply_text(
        "⏳ *Bugungi bepul limit tugadi.*\n\n"
        "💎 *Premium* oling — cheksiz foydalaning. "
        "Pastdagi 💎 Premium tugmasini bosing.",
        parse_mode="Markdown",
        reply_markup=MAIN_KB,
    )


# ---------- To'lov ----------

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def on_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sp = update.message.successful_payment
    user_id = update.effective_user.id
    db.grant_premium(user_id, config.PREMIUM_DAYS)
    db.record_payment(user_id, sp.total_amount)
    await update.message.reply_text(
        f"🎉 Rahmat! *Premium* {config.PREMIUM_DAYS} kunga faollashtirildi. "
        "Endi cheksiz foydalaning!",
        parse_mode="Markdown",
        reply_markup=MAIN_KB,
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Har qanday ushlanmagan xatoni log qiladi va foydalanuvchini ogohlantiradi.
    Bu funksiya bot to'xtab qolishining oldini oladi."""
    log.error("Xatolik yuz berdi:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring "
                "yoki /start bosing.",
                reply_markup=MAIN_KB,
            )
        except Exception:
            pass


def main():
    if not config.BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN topilmadi! .env faylga tokeningizni yozing "
            "(.env.example dan nusxa oling)."
        )
    _ensure_single_instance()
    _start_health_server()  # Render/bulut uchun (PORT env bo'lsa)
    db.init_db()
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_paid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(error_handler)

    log.info("Bot ishga tushdi ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

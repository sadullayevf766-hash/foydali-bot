"""Foydali Bot — asosiy fayl. Ishga tushirish: python bot.py"""
import os
import re
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

# Tugmalar matni — asosiy menyu
B_TEXT2DOC = "📝 Matn → Word/PDF"
B_FILES = "📂 Fayl & Rasm"
B_ACCT = "🧮 Buxgalter"
B_QR = "⚡ QR-kod"
B_RATES = "💱 Valyuta kursi"
B_PREMIUM = "💎 Premium"
B_BACK = "⬅️ Orqaga"

# Matn -> hujjat bo'limi
B_MK_WORD = "📄 Word hujjat"
B_MK_PDF = "📑 PDF hujjat"

# Fayl/rasm bo'limi
B_PDF = "📄 Rasm → PDF"
B_MERGE = "🔗 PDF birlashtirish"
B_SPLIT = "✂️ PDF bo'lish"
B_COMPRESS = "🗜 Rasm siqish"
B_RESIZE = "📐 Rasm kichraytirish"

# Buxgalter bo'limi
B_NUM2WORD = "💵 Son → so'zda"
B_VAT = "🧾 QQS hisoblash"
B_CONVERT = "🔄 Valyuta konvertor"

B_DONE = "✅ Tayyor"
B_CANCEL = "❌ Bekor qilish"

# Telegram bot API orqali yuklab olish chegarasi: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024

MAIN_KB = ReplyKeyboardMarkup(
    [[B_TEXT2DOC], [B_FILES], [B_ACCT], [B_QR, B_RATES], [B_PREMIUM]],
    resize_keyboard=True,
)
TEXT2DOC_KB = ReplyKeyboardMarkup(
    [[B_MK_WORD, B_MK_PDF], [B_CANCEL]], resize_keyboard=True
)
FILES_KB = ReplyKeyboardMarkup(
    [[B_PDF, B_MERGE], [B_SPLIT, B_COMPRESS], [B_RESIZE], [B_BACK]],
    resize_keyboard=True,
)
ACCT_KB = ReplyKeyboardMarkup(
    [[B_NUM2WORD], [B_VAT, B_CONVERT], [B_BACK]],
    resize_keyboard=True,
)
DONE_KB = ReplyKeyboardMarkup(
    [[B_DONE], [B_CANCEL]], resize_keyboard=True
)


def reset(context):
    context.user_data["mode"] = None
    context.user_data["images"] = []
    context.user_data["pdfs"] = []
    context.user_data["text_buf"] = []


# ---------- Buyruqlar ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.add_user(u.id, u.username or "", u.first_name or "")
    reset(context)
    text = (
        f"Assalomu alaykum, {u.first_name}! 👋\n\n"
        "Men *Foydali Bot*man — ishingizni yengillashtiraman:\n\n"
        "📝 *Matn → Word/PDF*\n"
        "   • Insho, ma'ruza, referatingizni yozing —\n"
        "     men chiroyli Word yoki PDF qilib beraman\n\n"
        "📂 *Fayl & Rasm*\n"
        "   • Rasm → PDF, PDF birlashtirish/bo'lish\n"
        "   • Rasm siqish/kichraytirish\n\n"
        "🧮 *Buxgalter*\n"
        "   • 💵 Son → so'zda (hujjatlar uchun)\n"
        "   • 🧾 QQS (12%) hisoblash\n"
        "   • 🔄 Valyuta konvertor\n\n"
        "⚡ *QR-kod*  •  💱 *Valyuta kursi*\n\n"
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


async def kurs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tezkor valyuta kursi — /kurs buyrug'i."""
    reset(context)
    try:
        msg = await utils.get_rates()
    except Exception:
        msg = "❌ Kurs olishda xatolik. Birozdan keyin urinib ko'ring."
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=MAIN_KB)


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

    # --- Navigatsiya ---
    if text in (B_CANCEL, B_BACK):
        reset(context)
        await update.message.reply_text("Asosiy menyu 👇", reply_markup=MAIN_KB)
        return

    if text == B_FILES:
        reset(context)
        await update.message.reply_text(
            "📂 *Fayl & Rasm* — kerakli amalni tanlang:", parse_mode="Markdown",
            reply_markup=FILES_KB,
        )
        return

    if text == B_ACCT:
        reset(context)
        await update.message.reply_text(
            "🧮 *Buxgalter* — kerakli amalni tanlang:", parse_mode="Markdown",
            reply_markup=ACCT_KB,
        )
        return

    if text == B_TEXT2DOC:
        reset(context); context.user_data["mode"] = "text2doc"
        await update.message.reply_text(
            "📝 *Matn → Word/PDF*\n\n"
            "Matningizni yuboring (insho, ma'ruza, referat...). "
            "Uzun bo'lsa bir nechta xabarda yuboravering.\n\n"
            "✍️ *Tuzilma uchun belgilar:*\n"
            "`# Sarlavha` — asosiy mavzu\n"
            "`## Bo'lim` — bo'lim sarlavhasi\n"
            "`### Kichik bo'lim`\n"
            "`- punkt` — belgili ro'yxat\n"
            "`1. punkt` — raqamli ro'yxat\n"
            "oddiy matn — xatboshi\n\n"
            "Tugagach 📄 *Word* yoki 📑 *PDF* tugmasini bosing.",
            parse_mode="Markdown", reply_markup=TEXT2DOC_KB)
        return

    if text in (B_MK_WORD, B_MK_PDF):
        await _make_document(update, context, "word" if text == B_MK_WORD else "pdf")
        return

    # --- Fayl/rasm amallari (rejimni o'rnatadi) ---
    if text == B_PDF:
        reset(context); context.user_data["mode"] = "pdf"
        await update.message.reply_text(
            "📄 Rasmlarni yuboring (bittadan yoki bir nechta). "
            "Tugagach *✅ Tayyor* bosing.", parse_mode="Markdown", reply_markup=DONE_KB)
        return
    if text == B_MERGE:
        reset(context); context.user_data["mode"] = "merge"
        await update.message.reply_text(
            "🔗 PDF fayllarni yuboring (fayl sifatida). "
            "Tugagach *✅ Tayyor* bosing.", parse_mode="Markdown", reply_markup=DONE_KB)
        return
    if text == B_SPLIT:
        reset(context); context.user_data["mode"] = "split"
        await update.message.reply_text(
            "✂️ Bo'linadigan PDF faylni yuboring (fayl sifatida). "
            "Har bir sahifa alohida PDF bo'lib, ZIP ichida qaytariladi.",
            reply_markup=DONE_KB)
        return
    if text == B_COMPRESS:
        reset(context); context.user_data["mode"] = "compress"
        await update.message.reply_text(
            "🗜 Siqiladigan rasmni yuboring — hajmini kichraytirib beraman.",
            reply_markup=DONE_KB)
        return
    if text == B_RESIZE:
        reset(context); context.user_data["mode"] = "resize"
        await update.message.reply_text(
            "📐 Rasmni yuboring — eng uzun tomonini 1024px ga kichraytiraman.",
            reply_markup=DONE_KB)
        return

    # --- Buxgalter amallari ---
    if text == B_NUM2WORD:
        reset(context); context.user_data["mode"] = "num2word"
        await update.message.reply_text(
            "💵 Sonni yuboring (masalan `1250000`) — so'zda yozib beraman.",
            parse_mode="Markdown", reply_markup=ACCT_KB)
        return
    if text == B_VAT:
        reset(context); context.user_data["mode"] = "vat"
        await update.message.reply_text(
            "🧾 Summani yuboring (masalan `1000000`) — QQS (12%) hisoblab beraman.",
            parse_mode="Markdown", reply_markup=ACCT_KB)
        return
    if text == B_CONVERT:
        reset(context); context.user_data["mode"] = "convert"
        await update.message.reply_text(
            "🔄 Summani yuboring:\n"
            "• `100 USD` — dollarni so'mga\n"
            "• `1000000` — so'mni valyutalarga",
            parse_mode="Markdown", reply_markup=ACCT_KB)
        return

    if text == B_QR:
        reset(context); context.user_data["mode"] = "qr"
        await update.message.reply_text(
            "⚡ QR-kodga aylantirmoqchi bo'lgan matn yoki havolani yuboring:",
            reply_markup=DONE_KB)
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
        await update.message.reply_text(
            "Bu amal uchun rasm/fayl yoki son yuboring 🙂", reply_markup=MAIN_KB)
        reset(context)
        return

    # --- Rejimga qarab matnni qayta ishlash ---
    mode = context.user_data.get("mode")
    if mode == "text2doc":
        context.user_data.setdefault("text_buf", []).append(text)
        n = sum(len(p) for p in context.user_data["text_buf"])
        await update.message.reply_text(
            f"✅ Qabul qilindi ({n} belgi). Yana matn yuboring yoki "
            "📄 Word / 📑 PDF tugmasini bosing.", reply_markup=TEXT2DOC_KB)
        return
    if mode == "qr":
        png = utils.make_qr(text)
        await update.message.reply_photo(
            photo=InputFile(png, filename="qr.png"),
            caption="✅ Tayyor! QR-kodingiz.", reply_markup=MAIN_KB)
        reset(context)
        return
    if mode == "num2word":
        await _handle_num2word(update, text)
        return
    if mode == "vat":
        await _handle_vat(update, text)
        return
    if mode == "convert":
        await _handle_convert(update, text)
        return

    await update.message.reply_text(
        "Tugmalardan birini tanlang 👇", reply_markup=MAIN_KB)


# ---------- Buxgalter hisoblash yordamchilari ----------

def _parse_number(text: str):
    """Matndan butun sonni ajratadi (bo'sh joy, vergul, nuqtani tashlab)."""
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


async def _handle_num2word(update: Update, text: str):
    n = _parse_number(text)
    if n is None:
        await update.message.reply_text("❌ Son topilmadi. Masalan: 1250000", reply_markup=ACCT_KB)
        return
    words = utils.number_to_uzbek_words(n)
    await update.message.reply_text(
        f"🔢 *{n:,}*".replace(",", " ") + f"\n\n💵 *{words} so'm*",
        parse_mode="Markdown", reply_markup=ACCT_KB)


async def _handle_vat(update: Update, text: str):
    n = _parse_number(text)
    if n is None:
        await update.message.reply_text("❌ Summa topilmadi. Masalan: 1000000", reply_markup=ACCT_KB)
        return
    def f(x):
        return f"{x:,.0f}".replace(",", " ")
    vat_add = n * 0.12
    vat_extract = n * 12 / 112
    await update.message.reply_text(
        f"🧾 *QQS hisobi (12%)* — summa: {f(n)} so'm\n\n"
        f"➕ *QQS qo'shilsa:*\n"
        f"   QQS: {f(vat_add)} so'm\n"
        f"   Jami: {f(n + vat_add)} so'm\n\n"
        f"➖ *QQS ajratilsa* (summa ichida):\n"
        f"   QQS: {f(vat_extract)} so'm\n"
        f"   QQSsiz: {f(n - vat_extract)} so'm",
        parse_mode="Markdown", reply_markup=ACCT_KB)


async def _handle_convert(update: Update, text: str):
    m = re.match(r"^\s*([\d\s.,]+)\s*([a-zA-Z]{3})?\s*$", text)
    if not m:
        await update.message.reply_text(
            "❌ Tushunmadim. Masalan: `100 USD` yoki `1000000`",
            parse_mode="Markdown", reply_markup=ACCT_KB)
        return
    amount = _parse_number(m.group(1))
    code = (m.group(2) or "").upper()
    if amount is None:
        await update.message.reply_text("❌ Summa topilmadi.", reply_markup=ACCT_KB)
        return
    try:
        rates, dt = await utils.get_rate_map()
    except Exception:
        await update.message.reply_text("❌ Kurs olishda xatolik.", reply_markup=ACCT_KB)
        return

    def f(x):
        return f"{x:,.2f}".replace(",", " ")

    if code:
        if code not in rates:
            await update.message.reply_text(
                f"❌ '{code}' valyutasi topilmadi. USD, EUR, RUB, KZT va h.k.",
                reply_markup=ACCT_KB)
            return
        som = amount * rates[code]
        await update.message.reply_text(
            f"🔄 *{amount:,} {code}* = *{f(som)} so'm*".replace(",", " ")
            + f"\n\n(1 {code} = {f(rates[code])} so'm, {dt})",
            parse_mode="Markdown", reply_markup=ACCT_KB)
    else:
        lines = [f"🔄 *{amount:,} so'm* =".replace(",", " "), ""]
        for c in ["USD", "EUR", "RUB", "KZT"]:
            if c in rates and rates[c]:
                lines.append(f"   *{f(amount / rates[c])}* {c}")
        lines.append(f"\n_(Markaziy bank kursi, {dt})_")
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown", reply_markup=ACCT_KB)


# ---------- Matn -> Word/PDF hujjat ----------

async def _make_document(update: Update, context: ContextTypes.DEFAULT_TYPE, fmt: str):
    user_id = update.effective_user.id
    parts = context.user_data.get("text_buf", [])
    full = "\n".join(parts).strip()
    if not full:
        await update.message.reply_text(
            "Avval matningizni yuboring 🙂", reply_markup=TEXT2DOC_KB)
        return
    if not db.consume_quota(user_id):
        await _limit_reached(update)
        return
    await update.message.chat.send_action("upload_document")
    try:
        if fmt == "word":
            data = utils.text_to_docx(full)
            fname = "hujjat.docx"
        else:
            data = utils.text_to_pdf(full)
            fname = "hujjat.pdf"
        await update.message.reply_document(
            document=InputFile(data, filename=fname),
            caption="✅ Hujjatingiz tayyor!\n\n" + _quota_caption(user_id),
            reply_markup=MAIN_KB)
    except Exception:
        log.exception("hujjat xatolik")
        await update.message.reply_text(
            "❌ Hujjat yaratishda xatolik. Qaytadan urinib ko'ring.",
            reply_markup=MAIN_KB)
    finally:
        reset(context)


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode not in ("pdf", "compress", "resize"):
        await update.message.reply_text(
            "Rasm bilan ishlash uchun avval 📂 *Fayl & Rasm* dan amalni tanlang.",
            parse_mode="Markdown", reply_markup=MAIN_KB)
        return
    photo = update.message.photo[-1]  # eng yuqori sifat
    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            "⚠️ Rasm juda katta (20 MB dan ortiq). Kichikroq rasm yuboring.")
        return
    file = await context.bot.get_file(photo.file_id)
    data = bytes(await file.download_as_bytearray())

    if mode == "pdf":
        context.user_data.setdefault("images", []).append(data)
        n = len(context.user_data["images"])
        await update.message.reply_text(
            f"✅ {n}-rasm qabul qilindi. Yana yuboring yoki *✅ Tayyor* bosing.",
            parse_mode="Markdown", reply_markup=DONE_KB)
        return

    # compress / resize — darhol qayta ishlash (kvota sarflanadi)
    await _process_single_image(update, context, mode, data)


async def _process_single_image(update, context, mode, data):
    user_id = update.effective_user.id
    if not db.consume_quota(user_id):
        await _limit_reached(update)
        return
    try:
        if mode == "compress":
            out = utils.compress_image(data)
            await update.message.reply_document(
                document=InputFile(out, filename="siqilgan.jpg"),
                caption=f"🗜 Siqildi: {len(data)//1024} KB → {len(out)//1024} KB\n\n"
                        + _quota_caption(user_id),
                reply_markup=FILES_KB)
        elif mode == "resize":
            out = utils.resize_image(data)
            await update.message.reply_document(
                document=InputFile(out, filename="kichraytirilgan.jpg"),
                caption="📐 Tayyor! (1024px)\n\n" + _quota_caption(user_id),
                reply_markup=FILES_KB)
    except Exception:
        log.exception(f"{mode} xatolik")
        await update.message.reply_text(
            "❌ Amalda xatolik yuz berdi. Boshqa fayl bilan urinib ko'ring.",
            reply_markup=FILES_KB)
    finally:
        reset(context)


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    mode = context.user_data.get("mode")
    if mode not in ("merge", "split"):
        await update.message.reply_text(
            "PDF bilan ishlash uchun avval 📂 *Fayl & Rasm* dan amalni tanlang.",
            parse_mode="Markdown", reply_markup=MAIN_KB)
        return
    if not (doc.mime_type == "application/pdf" or (doc.file_name or "").lower().endswith(".pdf")):
        await update.message.reply_text("❌ Bu PDF fayl emas. PDF yuboring.")
        return
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            "⚠️ Bu fayl juda katta (20 MB dan ortiq). Kichikroq PDF yuboring.")
        return
    file = await context.bot.get_file(doc.file_id)
    data = bytes(await file.download_as_bytearray())

    if mode == "merge":
        context.user_data.setdefault("pdfs", []).append(data)
        n = len(context.user_data["pdfs"])
        await update.message.reply_text(
            f"✅ {n}-PDF qabul qilindi. Yana yuboring yoki *✅ Tayyor* bosing.",
            parse_mode="Markdown", reply_markup=DONE_KB)
        return

    # split — darhol bo'lish (kvota sarflanadi)
    user_id = update.effective_user.id
    if not db.consume_quota(user_id):
        await _limit_reached(update)
        return
    try:
        zip_bytes, pages = utils.split_pdf(data)
        await update.message.reply_document(
            document=InputFile(zip_bytes, filename="sahifalar.zip"),
            caption=f"✂️ {pages} ta sahifaga bo'lindi.\n\n" + _quota_caption(user_id),
            reply_markup=FILES_KB)
    except Exception:
        log.exception("split xatolik")
        await update.message.reply_text(
            "❌ PDF bo'lishda xatolik.", reply_markup=FILES_KB)
    finally:
        reset(context)


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
    app.add_handler(CommandHandler("kurs", kurs_cmd))
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

"""Botning o'zi tarqalishi uchun mexanika: inline rejim, referal, ulashish.

Asosiy g'oya: foydalanuvchi botni guruhda ishlatganda Telegram xabar tepasida
"via @bot" deb ko'rsatadi — guruhdagi hamma ko'radi. Bu reklama emas, oddiy
foydalanish natijasi, va u hech qanday vaqt talab qilmaydi.
"""
import hashlib
import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InlineQueryResultsButton,
    InputTextMessageContent,
    Update,
)
from telegram.ext import ContextTypes

import config
import db
import growth_db
import utils

log = logging.getLogger("foydali-bot.growth")

# Bir marta yaratilgan QR rasmlarni qayta yuklamaslik uchun: matn -> file_id
_qr_cache: dict[str, str] = {}


def _uid(*parts: str) -> str:
    """Inline natija uchun barqaror id."""
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:32]


def bot_link(username: str) -> str:
    return f"https://t.me/{username}"


def ref_link(username: str, user_id: int) -> str:
    return f"https://t.me/{username}?start=ref_{user_id}"


def share_kb(username: str) -> InlineKeyboardMarkup:
    """Natija ostidagi tugmalar. `switch_inline_query` chat tanlash oynasini ochadi."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Do'stga yuborish", switch_inline_query=""),
        InlineKeyboardButton("🤖 Bot", url=bot_link(username)),
    ]])


def premium_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"💎 Premium olish — {config.PREMIUM_PRICE_STARS} ⭐", callback_data="buy_premium"
        )
    ]])


# ---------- Referal ----------

async def handle_start_payload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """/start dagi parametrni qayta ishlaydi. Manba nomini qaytaradi (statistika uchun)."""
    args = context.args or []
    payload = args[0] if args else ""
    user_id = update.effective_user.id

    if payload.startswith("ref_"):
        try:
            referrer_id = int(payload[4:])
        except ValueError:
            return payload
        if growth_db.set_referrer(user_id, referrer_id):
            log.info("Referal bog'landi: %s -> %s", referrer_id, user_id)
        return "referal"
    return payload


async def credit_referrer_if_due(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi haqiqiy amal bajargach, uni taklif qilgan odamga bonus beradi.

    /start bosishning o'zi yetarli emas — shu sababli soxta akkaunt yig'ish
    foydasiz bo'ladi.
    """
    user = update.effective_user
    referrer_id = growth_db.pending_referrer(user.id)
    if not referrer_id:
        return

    growth_db.mark_ref_credited(user.id)
    db.grant_premium(referrer_id, growth_db.REF_BONUS_DAYS)
    total = growth_db.referral_count(referrer_id)
    try:
        await context.bot.send_message(
            chat_id=referrer_id,
            text=(
                f"🎁 *{user.first_name}* siz yuborgan havola orqali botdan foydalandi.\n\n"
                f"Sizga *{growth_db.REF_BONUS_DAYS} kun Premium* qo'shildi.\n"
                f"Jami taklif qilganlaringiz: *{total}*"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        # Taklif qilgan odam botni bloklagan bo'lishi mumkin — bu xato emas.
        log.debug("Referal bonusi haqida xabar yuborilmadi: %s", referrer_id)


async def invite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/taklif — shaxsiy havola va statistika."""
    user_id = update.effective_user.id
    username = context.bot.username
    link = ref_link(username, user_id)
    count = growth_db.referral_count(user_id)

    text = (
        "🎁 *Do'stlaringizni taklif qiling*\n\n"
        f"Har bir do'stingiz shu havola orqali kelib botdan foydalansa, "
        f"sizga *{growth_db.REF_BONUS_DAYS} kun Premium* beriladi.\n\n"
        f"Sizning havolangiz:\n`{link}`\n\n"
        f"Hozirgacha taklif qilganingiz: *{count}* ta"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔗 Havolani yuborish",
                switch_inline_query="",
            )
        ]]),
    )


# ---------- Inline rejim ----------

async def _qr_file_id(context: ContextTypes.DEFAULT_TYPE, text: str) -> str | None:
    """QR rasmni bir marta yuklab, `file_id` sini keshlaydi.

    Inline natijalar tayyor `file_id` yoki ochiq URL talab qiladi — inline
    javob ichida fayl yuklab bo'lmaydi. Shuning uchun rasm avval saqlash
    chatiga yuboriladi.
    """
    if not config.STORAGE_CHAT_ID:
        return None
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if key in _qr_cache:
        return _qr_cache[key]
    try:
        png = utils.make_qr(text)
        msg = await context.bot.send_photo(chat_id=config.STORAGE_CHAT_ID, photo=png)
        file_id = msg.photo[-1].file_id
        _qr_cache[key] = file_id
        return file_id
    except Exception:
        log.exception("Inline QR yaratishda xatolik")
        return None


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Istalgan chatda `@bot ...` yozilganda ishlaydi."""
    query = (update.inline_query.query or "").strip()
    user = update.inline_query.from_user
    username = context.bot.username
    results = []

    # Bo'sh so'rov = "ulashish" tugmasi bosilgan. Bunda botni tanishtiramiz.
    if not query:
        results.append(
            InlineQueryResultArticle(
                id=_uid("about", username),
                title="🤖 Foydali Bot",
                description="PDF, QR, hujjat va buxgalter hisoblari — bepul",
                input_message_content=InputTextMessageContent(
                    "🤖 *Foydali Bot* — rasmni PDF qiladi, PDF birlashtiradi, "
                    "QR kod yaratadi, matnni Word/PDF hujjat qiladi.\n\n"
                    f"{bot_link(username)}",
                    parse_mode="Markdown",
                ),
                reply_markup=share_kb(username),
            )
        )

    # 2. Son -> so'z. Hujjat va shartnomalarda kerak bo'ladi.
    digits = query.replace(" ", "").replace("_", "")
    if digits.isdigit() and 0 < len(digits) <= 15:
        try:
            words = utils.number_to_uzbek_words(int(digits))
            results.append(
                InlineQueryResultArticle(
                    id=_uid("num", digits),
                    title="🔢 Son → so'z",
                    description=words[:80],
                    input_message_content=InputTextMessageContent(
                        f"*{int(digits):,}* — {words}".replace(",", " "),
                        parse_mode="Markdown",
                    ),
                    reply_markup=share_kb(username),
                )
            )
        except Exception:
            log.debug("Son so'zga aylantirilmadi: %s", digits)

    # 3. QR kod — saqlash chati sozlangan bo'lsa rasmni shu yerda qaytaramiz.
    if query and len(query) <= 500:
        file_id = await _qr_file_id(context, query)
        if file_id:
            results.append(
                InlineQueryResultCachedPhoto(
                    id=_uid("qr", query),
                    photo_file_id=file_id,
                    title="⚡ QR kod",
                    description=query[:60],
                    caption=f"⚡ QR: {query[:200]}",
                    reply_markup=share_kb(username),
                )
            )
        else:
            # Saqlash chati sozlanmagan. Bo'sh ro'yxat qaytarish "bot buzuq"
            # taassurotini beradi, shuning uchun botga yo'naltiramiz.
            results.append(
                InlineQueryResultArticle(
                    id=_uid("qr-link", query),
                    title="⚡ QR kod yaratish",
                    description="Botda ochiladi",
                    input_message_content=InputTextMessageContent(
                        f"⚡ QR kod, PDF va hujjat tayyorlash: {bot_link(username)}"
                    ),
                    reply_markup=share_kb(username),
                )
            )

    if results:
        growth_db.track(user.id, "inline", "inline")

    await update.inline_query.answer(
        results,
        cache_time=60,
        is_personal=False,
        button=InlineQueryResultsButton(
            text="🤖 Botni ochish — PDF, QR, hujjat",
            start_parameter="inline",
        ),
    )

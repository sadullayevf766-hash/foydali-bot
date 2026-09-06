"""IELTS Writing tekshiruvchi bot — handlerlar.

Holat (qaysi bosqichda ekani) `context.user_data` da saqlanadi: oqim qisqa
va tugmalar bilan boshqariladi, shuning uchun ConversationHandler ortiqcha
murakkablik bo'lardi.
"""
from __future__ import annotations

import html
import logging
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import config, db, grader
from .texts import btn, res, t

log = logging.getLogger("ielts.bot")

TELEGRAM_LIMIT = 4096


# ---------- Klaviaturalar ----------

def main_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(btn("check", lang))],
            [KeyboardButton(btn("balance", lang)), KeyboardButton(btn("buy", lang))],
            [KeyboardButton(btn("invite", lang)), KeyboardButton(btn("help", lang))],
            [KeyboardButton(btn("lang", lang))],
        ],
        resize_keyboard=True,
    )


def task_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(grader.TASKS["task2"][lang], callback_data="task:task2")],
        [InlineKeyboardButton(grader.TASKS["task1_academic"][lang],
                              callback_data="task:task1_academic")],
        [InlineKeyboardButton(grader.TASKS["task1_general"][lang],
                              callback_data="task:task1_general")],
    ])


def plans_kb(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for key, p in config.PLANS.items():
        title = p["title"] if lang == "uz" else p["title_en"]
        if p["checks"]:
            label = f"{title} — {p['checks']} ta — {p['price']:,} so'm"
        else:
            label = f"{title} — {p['price']:,} so'm"
        rows.append([InlineKeyboardButton(
            label.replace(",", " "), callback_data=f"plan:{key}")])
    return InlineKeyboardMarkup(rows)


def buy_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(btn("buy", lang), callback_data="open:buy")],
         [InlineKeyboardButton(btn("invite", lang), callback_data="open:invite")]]
    )


# ---------- Yordamchi ----------

def _lang(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    """Tilni user_data dan oladi (bazani har xabarda o'qimaslik uchun)."""
    lang = context.user_data.get("lang")
    if not lang:
        lang = db.lang_of(user_id)
        context.user_data["lang"] = lang
    return lang


def _admin_contact() -> str:
    return config.ADMIN_CONTACT or "@" + (config.BOT_USERNAME or "admin")


async def _send_long(message, text: str, **kw):
    """Uzun matnni Telegram chegarasiga sig'adigan bo'laklarga bo'lib yuboradi.

    Bo'linish xatboshi chegarasida bo'ladi — HTML tegi o'rtasidan kesilib
    qolmasligi uchun.
    """
    if len(text) <= TELEGRAM_LIMIT:
        await message.reply_text(text, **kw)
        return
    chunk = ""
    for para in text.split("\n\n"):
        if len(chunk) + len(para) + 2 > TELEGRAM_LIMIT - 100:
            if chunk:
                await message.reply_text(chunk, **kw)
            chunk = para
        else:
            chunk = f"{chunk}\n\n{para}" if chunk else para
    if chunk:
        await message.reply_text(chunk, **kw)


def _fmt_card() -> str:
    """Karta raqamini 4 talab bo'lib ko'rsatadi.

    Bazada raqamlar birga saqlanadi (nusxa olib bank ilovasiga qo'yish
    ishonchli bo'lsin), ekranda esa bo'shliq bilan — qo'lda kirituvchi
    odam adashmasligi uchun.
    """
    d = "".join(ch for ch in config.CARD_NUMBER if ch.isdigit())
    if len(d) != 16:
        return config.CARD_NUMBER
    return " ".join(d[i:i + 4] for i in range(0, 16, 4))


def _plan_label(key: str, lang: str) -> str:
    p = config.PLANS[key]
    return p["title"] if lang == "uz" else p["title_en"]


# ---------- /start ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    source = ""
    referrer = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref"):
            try:
                referrer = int(arg[3:])
                source = "referral"
            except ValueError:
                pass
        else:
            source = arg[:40]

    is_new = db.add_user(user.id, user.username or "", user.first_name or "", source)
    if is_new and referrer:
        db.set_referrer(user.id, referrer)
    db.track(user.id, "start", source)

    lang = _lang(context, user.id)
    context.user_data.pop("stage", None)
    bal = db.balance(user.id)
    await update.message.reply_text(
        t("welcome", lang, credits=bal["credits"], btn=btn("check", lang)),
        parse_mode="HTML",
        reply_markup=main_kb(lang),
    )


# ---------- Tekshirish oqimi ----------

async def begin_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = _lang(context, user.id)
    db.add_user(user.id, user.username or "", user.first_name or "")

    if not db.can_check(user.id):
        db.track(user.id, "limit_hit")
        await update.message.reply_text(
            t("no_credits", lang, bonus=config.REFERRAL_BONUS),
            parse_mode="HTML",
            reply_markup=buy_kb(lang),
        )
        return

    context.user_data["stage"] = "task"
    await update.message.reply_text(
        t("choose_task", lang), reply_markup=task_kb(lang)
    )


async def on_task_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = _lang(context, q.from_user.id)
    task = q.data.split(":", 1)[1]
    context.user_data["task"] = task
    context.user_data["stage"] = "question"
    await q.edit_message_text(
        t("ask_question", lang),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(t("skip_question", lang), callback_data="skipq")]]
        ),
    )


async def on_skip_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = _lang(context, q.from_user.id)
    context.user_data["question"] = ""
    context.user_data["stage"] = "essay"
    await q.edit_message_text(t("ask_essay", lang), parse_mode="HTML")


async def _run_grading(update, context, essay: str = "", image: bytes | None = None):
    """Baholaydi, natijani yuboradi va kreditni FAQAT muvaffaqiyatda yechadi."""
    user = update.effective_user
    lang = _lang(context, user.id)
    task = context.user_data.get("task", "task2")
    question = context.user_data.get("question", "")

    if context.user_data.get("busy"):
        return
    if not db.can_check(user.id):
        await update.message.reply_text(
            t("no_credits", lang, bonus=config.REFERRAL_BONUS),
            parse_mode="HTML", reply_markup=buy_kb(lang),
        )
        return

    context.user_data["busy"] = True
    wait = await update.message.reply_text(
        t("reading_photo" if image else "working", lang)
    )
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        result = await grader.grade(task, question, essay, image, lang)
    except Exception as e:
        log.warning("Baholash muvaffaqiyatsiz (user %s): %s", user.id, e)
        db.track(user.id, "grade_failed")
        await wait.edit_text(t("grader_failed", lang), parse_mode="HTML")
        return
    finally:
        context.user_data["busy"] = False

    db.consume(user.id)
    db.record_check(user.id, task, result["overall"], result["words"])
    db.track(user.id, "graded", task)

    context.user_data.pop("stage", None)
    try:
        await wait.delete()
    except Exception:
        pass

    left = db.balance(user.id)
    await _send_long(
        update.message,
        format_result(result, lang, left),
        parse_mode="HTML",
        reply_markup=main_kb(lang),
    )

    # Taklif qilgan odamga bonus — faqat haqiqiy tekshiruvdan keyin.
    ref = db.credit_referrer(user.id)
    if ref:
        try:
            await context.bot.send_message(
                ref, t("ref_bonus", db.lang_of(ref), n=config.REFERRAL_BONUS)
            )
        except Exception:
            pass

    # Kreditlar tugagan bo'lsa — darhol tarifni ko'rsatamiz.
    if not left["unlimited"] and left["credits"] == 0:
        await update.message.reply_text(
            t("no_credits", lang, bonus=config.REFERRAL_BONUS),
            parse_mode="HTML", reply_markup=buy_kb(lang),
        )


def format_result(r: dict, lang: str, left: dict) -> str:
    """Natijani Telegram HTML ko'rinishiga keltiradi."""
    e = html.escape
    out = [f"🎯 <b>{res('score', lang)}: {r['overall']}</b>"]

    short = r["words"] < r["min_words"]
    words_line = f"📝 {res('words', lang)}: {r['words']} / {r['min_words']}"
    if short:
        words_line += f" — <b>{res('short', lang)}</b>"
    out.append(words_line)

    if r["off_topic"]:
        out.append(res("off_topic", lang))
    if r["memorised"]:
        out.append(res("memorised", lang))

    out.append("")
    out.append(f"<b>{res('criteria', lang)}</b>")
    for c in r["criteria"]:
        out.append(f"• <b>{c['name']} — {c['band']}</b>\n{e(c['comment'])}")

    if r["summary"]:
        out.append("")
        out.append(f"<b>{res('summary', lang)}</b>\n{e(r['summary'])}")

    if r["errors"]:
        out.append("")
        out.append(f"<b>{res('errors', lang)}</b>")
        for i, err in enumerate(r["errors"], 1):
            line = f"{i}. ❌ <i>{e(err['quote'])}</i>\n   ✅ <b>{e(err['fix'])}</b>"
            if err["why"]:
                line += f"\n   <i>{e(err['why'])}</i>"
            out.append(line)

    if r["upgrades"]:
        out.append("")
        out.append(f"<b>{res('upgrades', lang)}</b>")
        for i, u in enumerate(r["upgrades"], 1):
            out.append(f"{i}. {e(u)}")

    imp = r["improved"]
    if imp["improved"]:
        out.append("")
        out.append(f"<b>{res('rewrite', lang)}</b>")
        if imp["original"]:
            out.append(f"<i>{res('your', lang)}:</i>\n{e(imp['original'])}")
        out.append(f"<i>{res('better', lang)}:</i>\n{e(imp['improved'])}")

    if r["transcript"]:
        out.append("")
        out.append(f"<b>{res('transcript', lang)}</b>\n{e(r['transcript'])}")

    out.append("")
    if left["unlimited"]:
        out.append(f"♾ {res('left', lang)}: {left['today_left']}")
    else:
        out.append(f"🎫 {res('left', lang)}: <b>{left['credits']}</b>")
    out.append(t("disclaimer", lang))
    return "\n".join(out)


# ---------- Balans, taklif, yordam ----------

async def send_balance(message, user, context):
    lang = _lang(context, user.id)
    b = db.balance(user.id)
    if b["unlimited"]:
        until = datetime.fromisoformat(b["until"]).strftime("%d.%m.%Y")
        text = t("balance_unlimited", lang, until=until,
                 today=b["today_left"], total=b["checks_total"])
    else:
        text = t("balance", lang, credits=b["credits"], total=b["checks_total"],
                 invited=db.invited_count(user.id))
    await message.reply_text(text, parse_mode="HTML", reply_markup=main_kb(lang))


async def send_invite(message, user, context):
    lang = _lang(context, user.id)
    username = config.BOT_USERNAME or (await context.bot.get_me()).username
    link = f"https://t.me/{username}?start=ref{user.id}"
    await message.reply_text(
        t("invite", lang, link=link, bonus=config.REFERRAL_BONUS,
          free=config.FREE_CHECKS, invited=db.invited_count(user.id)),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_kb(lang),
    )


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_balance(update.message, update.effective_user, context)


async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_invite(update.message, update.effective_user, context)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _lang(context, update.effective_user.id)
    await update.message.reply_text(
        t("help", lang, admin=_admin_contact()),
        parse_mode="HTML", reply_markup=main_kb(lang),
    )


async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    new = "en" if _lang(context, user.id) == "uz" else "uz"
    db.set_lang(user.id, new)
    context.user_data["lang"] = new
    bal = db.balance(user.id)
    await update.message.reply_text(
        t("welcome", new, credits=bal["credits"], btn=btn("check", new)),
        parse_mode="HTML", reply_markup=main_kb(new),
    )


# ---------- To'lov ----------

async def send_plans(message, user, context):
    lang = _lang(context, user.id)
    db.track(user.id, "open_plans")
    if not config.CARD_NUMBER:
        await message.reply_text(
            t("no_card", lang, admin=_admin_contact()), reply_markup=main_kb(lang)
        )
        return
    await message.reply_text(
        t("buy_intro", lang), parse_mode="HTML", reply_markup=plans_kb(lang)
    )


async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_plans(update.message, update.effective_user, context)


async def on_plan_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    lang = _lang(context, user.id)
    key = q.data.split(":", 1)[1]
    plan = config.PLANS.get(key)
    if not plan:
        return
    pid = db.create_payment(user.id, key, plan["price"])
    context.user_data["stage"] = "receipt"
    context.user_data["payment_id"] = pid
    db.track(user.id, "plan_chosen", key)
    holder = f"👤 {config.CARD_HOLDER}" if config.CARD_HOLDER else ""
    await q.edit_message_text(
        t("pay_instructions", lang, pid=pid, plan=_plan_label(key, lang),
          amount=f"{plan['price']:,}".replace(",", " "),
          card=_fmt_card(), holder=holder),
        parse_mode="HTML",
    )


async def on_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chek skrinshotini adminga yuboradi va tugmalar bilan tasdiqlatadi."""
    user = update.effective_user
    lang = _lang(context, user.id)
    pid = context.user_data.get("payment_id")
    pay = db.get_payment(pid) if pid else None
    if not pay:
        await update.message.reply_text(t("cancelled", lang),
                                        reply_markup=main_kb(lang))
        context.user_data.pop("stage", None)
        return

    context.user_data.pop("stage", None)
    db.track(user.id, "receipt_sent", pay["plan"])
    await update.message.reply_text(
        t("receipt_got", lang, pid=pid), parse_mode="HTML",
        reply_markup=main_kb(lang),
    )

    if not config.ADMIN_ID:
        log.error("ADMIN_ID sozlanmagan — to'lov #%s tasdiqlanmay qoladi", pid)
        return
    uname = f"@{user.username}" if user.username else "—"
    amount = f"{pay['amount']:,}".replace(",", " ")
    caption = (
        f"🧾 <b>To'lov #{pid}</b>\n"
        f"👤 {html.escape(user.first_name or '')} {uname}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"💳 {_plan_label(pay['plan'], 'uz')} — <b>{amount} so'm</b>"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay:ok:{pid}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"pay:no:{pid}"),
    ]])
    try:
        await context.bot.send_photo(
            config.ADMIN_ID, update.message.photo[-1].file_id,
            caption=caption, parse_mode="HTML", reply_markup=kb,
        )
    except Exception:
        log.exception("Chekni adminga yuborib bo'lmadi")


async def on_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != config.ADMIN_ID:
        await q.answer("Ruxsat yo'q", show_alert=True)
        return
    _, verdict, pid_s = q.data.split(":")
    pid = int(pid_s)
    pay = db.get_payment(pid)
    if not pay:
        await q.answer("Topilmadi", show_alert=True)
        return

    status = "tasdiqlandi" if verdict == "ok" else "rad etildi"
    if not db.set_payment_status(pid, status):
        await q.answer("Bu to'lov allaqachon hal qilingan", show_alert=True)
        return
    await q.answer("Bajarildi")

    uid = pay["user_id"]
    ulang = db.lang_of(uid)
    if verdict == "ok":
        plan = config.PLANS.get(pay["plan"], {})
        if plan.get("checks"):
            db.add_credits(uid, plan["checks"])
            granted = t("granted_credits", ulang, n=plan["checks"])
        else:
            db.grant_days(uid, plan.get("days", 30))
            granted = t("granted_days", ulang, n=plan.get("days", 30),
                        cap=config.UNLIMITED_DAILY_CAP)
        db.track(uid, "paid", pay["plan"])
        text = t("payment_ok", ulang, granted=granted, btn=btn("check", ulang))
    else:
        text = t("payment_no", ulang, pid=pid, admin=_admin_contact())

    try:
        await context.bot.send_message(uid, text, parse_mode="HTML")
    except Exception:
        log.warning("Foydalanuvchiga (%s) xabar yetkazilmadi", uid)

    mark = "✅ TASDIQLANDI" if verdict == "ok" else "❌ RAD ETILDI"
    try:
        await q.edit_message_caption(
            caption=(q.message.caption or "") + f"\n\n{mark}", parse_mode="HTML"
        )
    except Exception:
        pass


# ---------- Admin ----------

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        return
    s = db.stats()
    revenue = f"{s['revenue']:,}".replace(",", " ")
    # $30 maqsadigacha qancha qolgani (1 $ ≈ 12 900 so'm, taxminiy).
    goal = 390000
    left = max(0, goal - (s["revenue"] or 0))
    await update.message.reply_text(
        f"📊 <b>IELTS bot</b>\n\n"
        f"Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"Tekshiruvlar: {s['checks']} (bugun {s['checks_today']})\n"
        f"Sotuvlar: <b>{s['sales']}</b> ({s['buyers']} xaridor)\n"
        f"Tushum: <b>{revenue} so'm</b>\n"
        f"Maqsadgacha ($30): {left:,} so'm\n".replace(",", " ") +
        f"Kutayotgan to'lovlar: {s['pending']}",
        parse_mode="HTML",
    )


async def pending_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        return
    rows = db.pending_payments()
    if not rows:
        await update.message.reply_text("Kutayotgan to'lov yo'q ✅")
        return
    for p in rows:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅", callback_data=f"pay:ok:{p['id']}"),
            InlineKeyboardButton("❌", callback_data=f"pay:no:{p['id']}"),
        ]])
        await update.message.reply_text(
            f"#{p['id']} — {p['plan']} — {p['amount']} so'm — user {p['user_id']}",
            reply_markup=kb,
        )


async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bering <user_id> <soni> — qo'lda kredit qo'shish (sinov va uzr uchun)."""
    if update.effective_user.id != config.ADMIN_ID:
        return
    try:
        uid, n = int(context.args[0]), int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Ishlatish: /bering <user_id> <soni>")
        return
    db.add_credits(uid, n)
    await update.message.reply_text(f"✅ {uid} ga {n} ta tekshiruv qo'shildi")
    try:
        await context.bot.send_message(
            uid, t("granted_credits", db.lang_of(uid), n=n), parse_mode="HTML"
        )
    except Exception:
        pass


# ---------- Umumiy xabar yo'naltirgichi ----------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = _lang(context, user.id)
    text = (update.message.text or "").strip()

    # Menyu tugmalari — ikkala tilda ham tanilsin (til almashgan bo'lishi mumkin).
    for key, handler in (
        ("check", begin_check), ("balance", show_balance), ("buy", show_plans),
        ("invite", show_invite), ("help", show_help), ("lang", toggle_lang),
    ):
        if text in (btn(key, "uz"), btn(key, "en")):
            await handler(update, context)
            return

    stage = context.user_data.get("stage")
    if stage == "question":
        context.user_data["question"] = text[:2000]
        context.user_data["stage"] = "essay"
        await update.message.reply_text(t("ask_essay", lang), parse_mode="HTML")
        return

    if stage == "essay":
        if len(text) > config.MAX_CHARS:
            await update.message.reply_text(t("too_long", lang))
            return
        words = grader.count_words(text)
        if words < config.MIN_WORDS:
            await update.message.reply_text(
                t("too_short", lang, n=words, min=config.MIN_WORDS),
                parse_mode="HTML",
            )
            return
        await _run_grading(update, context, essay=text)
        return

    if stage == "receipt":
        await update.message.reply_text(
            t("receipt_expected", lang, btn=btn("check", lang)),
            reply_markup=main_kb(lang),
        )
        return

    # Hech qanday bosqichda emas: uzun matn kelsa — bu insho, darhol qabul
    # qilamiz. Bu eng ko'p uchraydigan xatti-harakat: odam avval matn tashlaydi.
    if grader.count_words(text) >= config.MIN_WORDS:
        db.add_user(user.id, user.username or "", user.first_name or "")
        context.user_data["task"] = "task2"
        context.user_data["question"] = ""
        context.user_data["stage"] = "essay"
        if not db.can_check(user.id):
            await update.message.reply_text(
                t("no_credits", lang, bonus=config.REFERRAL_BONUS),
                parse_mode="HTML", reply_markup=buy_kb(lang),
            )
            return
        await _run_grading(update, context, essay=text[:config.MAX_CHARS])
        return

    await begin_check(update, context)


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = _lang(context, user.id)
    stage = context.user_data.get("stage")

    if stage == "receipt":
        await on_receipt(update, context)
        return

    db.add_user(user.id, user.username or "", user.first_name or "")
    if not db.can_check(user.id):
        await update.message.reply_text(
            t("no_credits", lang, bonus=config.REFERRAL_BONUS),
            parse_mode="HTML", reply_markup=buy_kb(lang),
        )
        return

    context.user_data.setdefault("task", "task2")
    context.user_data.setdefault("question", "")
    photo = await update.message.photo[-1].get_file()
    data = bytes(await photo.download_as_bytearray())
    await _run_grading(update, context, image=data)


async def on_open_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline «Tarif olish» / «Taklif qilish» tugmalari."""
    q = update.callback_query
    await q.answer()
    what = q.data.split(":", 1)[1]
    # q.message.from_user — bot, shuning uchun foydalanuvchi alohida uzatiladi.
    if what == "buy":
        await send_plans(q.message, q.from_user, context)
    else:
        await send_invite(q.message, q.from_user, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("IELTS bot xatosi:", exc_info=context.error)


def build_app() -> Application:
    db.migrate()
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("balans", show_balance))
    app.add_handler(CommandHandler("tarif", show_plans))
    app.add_handler(CommandHandler("taklif", show_invite))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("pending", pending_cmd))
    app.add_handler(CommandHandler("bering", give_cmd))

    app.add_handler(CallbackQueryHandler(on_task_chosen, pattern=r"^task:"))
    app.add_handler(CallbackQueryHandler(on_skip_question, pattern=r"^skipq$"))
    app.add_handler(CallbackQueryHandler(on_plan_chosen, pattern=r"^plan:"))
    app.add_handler(CallbackQueryHandler(on_admin_decision, pattern=r"^pay:"))
    app.add_handler(CallbackQueryHandler(on_open_button, pattern=r"^open:"))

    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(error_handler)
    return app

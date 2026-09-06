"""Bot matnlari — o'zbekcha va inglizcha.

Bir joyda saqlanadi: matnni tuzatish uchun handler kodini ochish shart
emas, va ikkala til bir qatorda turgani uchun biri yangilanib, ikkinchisi
eskirib qolmaydi.
"""

BTN = {
    "check": {"uz": "✍️ Insho tekshirish", "en": "✍️ Check my essay"},
    "balance": {"uz": "📊 Balansim", "en": "📊 My balance"},
    "buy": {"uz": "💳 Tarif olish", "en": "💳 Buy credits"},
    "invite": {"uz": "🎁 Do'st taklif qilish", "en": "🎁 Invite a friend"},
    "help": {"uz": "ℹ️ Yordam", "en": "ℹ️ Help"},
    "lang": {"uz": "🌐 English", "en": "🌐 O'zbekcha"},
}

T = {
    "welcome": {
        "uz": (
            "<b>IELTS Writing tekshiruvchi</b>\n\n"
            "Inshoingizni yuboring — 4 ta rasmiy mezon bo'yicha taxminiy band "
            "ball, xatolaringiz ro'yxati va keyingi yarim ballga chiqish uchun "
            "aniq 3 ta qadam olasiz.\n\n"
            "📸 Qo'lda yozgan bo'lsangiz — shunchaki <b>rasmini</b> yuboring, "
            "o'qib beradi. Bir necha varaq bo'lsa, albom qilib yuboring.\n\n"
            "🎁 Sizda <b>{credits} ta bepul tekshiruv</b> bor.\n\n"
            "Boshlash uchun «{btn}» tugmasini bosing."
        ),
        "en": (
            "<b>IELTS Writing checker</b>\n\n"
            "Send your essay and get an estimated band score against the four "
            "official criteria, a list of your actual mistakes, and three "
            "concrete steps to the next half band.\n\n"
            "📸 Handwritten? Just send a <b>photo</b> — it will be read for you.\n\n"
            "🎁 You have <b>{credits} free checks</b>.\n\n"
            "Press «{btn}» to start."
        ),
    },
    "choose_task": {
        "uz": "Qaysi vazifa? Buni to'g'ri tanlash muhim — mezonlar har xil.",
        "en": "Which task? This matters — the criteria differ.",
    },
    "ask_question": {
        "uz": (
            "📋 Endi <b>savolni (task)</b> yuboring — insho topshirig'i matnini.\n\n"
            "Savolsiz bot inshoning mavzuga javob berganini bilolmaydi, "
            "ya'ni eng og'ir mezon (Task Response) baholanmay qoladi."
        ),
        "en": (
            "📋 Now send the <b>task prompt</b> — the question you were answering.\n\n"
            "Without it the bot cannot tell whether you answered the question, "
            "so the heaviest criterion (Task Response) stays unassessed."
        ),
    },
    "ask_question_visual": {
        "uz": (
            "📊 Task 1 Academic'da savol — bu <b>grafik, jadval, xarita yoki "
            "sxema</b>.\n\n"
            "Uning <b>rasmini yuboring</b> (matni ham bo'lsa, matn ko'rinishida "
            "yuborsangiz ham bo'ladi).\n\n"
            "Bu muhim: grafikni ko'rmasa, bot siz keltirgan raqamlar to'g'ri "
            "yoki noto'g'ri ekanini bilolmaydi — bu esa Task Achievement "
            "bahosining yarmi."
        ),
        "en": (
            "📊 In Task 1 Academic the question is a <b>chart, table, map or "
            "diagram</b>.\n\n"
            "Send a <b>photo of it</b> (you may send the wording as text too).\n\n"
            "This matters: without seeing the visual the bot cannot tell "
            "whether your figures are right or wrong — and that is half of "
            "Task Achievement."
        ),
    },
    "has_task_image": {
        "uz": "📊 Savolda grafik/rasm ham bor",
        "en": "📊 The question has a chart/image",
    },
    "send_task_image": {
        "uz": (
            "📊 Topshiriq rasmini (grafik, jadval, xarita) yuboring.\n\n"
            "Keyin inshoingizni yuborasiz."
        ),
        "en": (
            "📊 Send the task image (chart, table, map).\n\n"
            "You will send your essay after that."
        ),
    },
    "question_photo_ok": {
        "uz": (
            "✅ Topshiriq rasmi qabul qilindi ({n} ta).\n\n"
            "✍️ Endi <b>inshoingizni</b> yuboring — matn yoki qo'lyozma "
            "rasmi. Bir necha varaq bo'lsa, albom qilib yuboring."
        ),
        "en": (
            "✅ Task image received ({n}).\n\n"
            "✍️ Now send your <b>essay</b> — text or a photo of your "
            "handwriting. Several pages: send them as one album."
        ),
    },
    "skip_question": {"uz": "Savolsiz davom etish", "en": "Continue without it"},
    "skipped_warn": {
        "uz": ("⚠️ Savolsiz davom etyapmiz. Task mezoni baholanmaydi va "
               "umumiy ballga qo'shilmaydi — natija faqat <b>til</b> "
               "bo'yicha bo'ladi."),
        "en": ("⚠️ Continuing without the question. The Task criterion will "
               "not be assessed and is excluded from the band — the result "
               "covers <b>language</b> only."),
    },
    "ask_essay": {
        "uz": (
            "✍️ Endi <b>inshoingizni</b> yuboring.\n\n"
            "Matn ko'rinishida yozing yoki qo'lyozmangizning <b>rasmini</b> "
            "yuboring.\n\n"
            "📄 Insho bir necha varaqda bo'lsa — hammasini <b>bitta albom "
            "qilib</b> (birdan tanlab) yuboring. Ular bitta insho sifatida "
            "o'qiladi va bitta tekshiruv hisoblanadi."
        ),
        "en": (
            "✍️ Now send your <b>essay</b>.\n\n"
            "Type it, or send a <b>photo</b> of your handwriting.\n\n"
            "📄 If it spans several pages, send them as <b>one album</b> "
            "(select them all at once). They are read as a single essay and "
            "count as one check."
        ),
    },
    "working": {
        "uz": "⏳ Tekshirilmoqda… bu 20-40 soniya oladi.",
        "en": "⏳ Grading… this takes 20-40 seconds.",
    },
    "reading_photo": {
        "uz": "📖 Qo'lyozma o'qilmoqda va tekshirilmoqda… 30-60 soniya.",
        "en": "📖 Reading the handwriting and grading… 30-60 seconds.",
    },
    "reading_pages": {
        "uz": ("📖 {n} ta varaq bitta insho sifatida o'qilmoqda… "
               "30-60 soniya. Bitta tekshiruv hisoblanadi."),
        "en": ("📖 Reading {n} pages as one essay… 30-60 seconds. "
               "This counts as a single check."),
    },
    "too_short": {
        "uz": (
            "Bu juda qisqa ({n} ta so'z). Baholash uchun kamida {min} ta so'z "
            "kerak.\n\nTekshiruv hisobingizdan <b>yechilmadi</b> — to'liq "
            "inshoni yuboring."
        ),
        "en": (
            "That is too short ({n} words). At least {min} words are needed.\n\n"
            "Nothing was deducted from your balance — send the full essay."
        ),
    },
    "too_long": {
        "uz": "Bu juda uzun. Bitta IELTS inshosini yuboring (400 so'zgacha).",
        "en": "That is too long. Send a single IELTS response (up to 400 words).",
    },
    "no_credits": {
        "uz": (
            "Bepul tekshiruvlaringiz tugadi.\n\n"
            "Davom etish uchun tarif oling yoki do'stingizni taklif qiling — "
            "u birinchi tekshiruvdan o'tkazsa, sizga <b>+{bonus}</b> tekshiruv "
            "qo'shiladi."
        ),
        "en": (
            "You have used your free checks.\n\n"
            "Buy credits to continue, or invite a friend — when they complete "
            "their first check you get <b>+{bonus}</b> check."
        ),
    },
    "balance": {
        "uz": (
            "📊 <b>Balansingiz</b>\n\n"
            "Qolgan tekshiruv: <b>{credits}</b>\n"
            "Jami tekshirilgan: {total}\n"
            "Taklif qilingan do'stlar: {invited}"
        ),
        "en": (
            "📊 <b>Your balance</b>\n\n"
            "Checks left: <b>{credits}</b>\n"
            "Checked so far: {total}\n"
            "Friends invited: {invited}"
        ),
    },
    "balance_unlimited": {
        "uz": (
            "📊 <b>Balansingiz</b>\n\n"
            "Tarif: <b>cheksiz</b>, {until} gacha\n"
            "Bugun qoldi: {today} ta\n"
            "Jami tekshirilgan: {total}"
        ),
        "en": (
            "📊 <b>Your balance</b>\n\n"
            "Plan: <b>unlimited</b>, until {until}\n"
            "Left today: {today}\n"
            "Checked so far: {total}"
        ),
    },
    "buy_intro": {
        "uz": (
            "💳 <b>Tarif tanlang</b>\n\n"
            "Bitta insho repetitorda 50 000 - 100 000 so'm turadi va javobi "
            "bir necha kunda keladi. Bu yerda javob bir daqiqada.\n\n"
            "To'lov: kartaga o'tkazma, chekni botga yuborasiz."
        ),
        "en": (
            "💳 <b>Choose a plan</b>\n\n"
            "A tutor charges 50,000-100,000 so'm per essay and replies in days. "
            "Here the answer comes in a minute.\n\n"
            "Payment: card transfer, then send the receipt to the bot."
        ),
    },
    "pay_instructions": {
        "uz": (
            "🧾 <b>To'lov #{pid}</b> — {plan}\n"
            "Summa: <b>{amount} so'm</b>\n\n"
            "1️⃣ Shu kartaga o'tkazing:\n"
            "<code>{card}</code>\n"
            "{holder}\n\n"
            "2️⃣ To'lov chekining <b>skrinshotini shu chatga yuboring</b>.\n\n"
            "Tasdiqlangach tekshiruvlar avtomatik qo'shiladi. Odatda bir "
            "necha soat ichida, ba'zan darhol."
        ),
        "en": (
            "🧾 <b>Payment #{pid}</b> — {plan}\n"
            "Amount: <b>{amount} so'm</b>\n\n"
            "1️⃣ Transfer to this card:\n"
            "<code>{card}</code>\n"
            "{holder}\n\n"
            "2️⃣ Send a <b>screenshot of the receipt to this chat</b>.\n\n"
            "Credits are added automatically once confirmed — usually within "
            "a few hours, often immediately."
        ),
    },
    "no_card": {
        "uz": (
            "To'lov hozircha sozlanmagan. Iltimos, admin bilan bog'laning: "
            "{admin}"
        ),
        "en": "Payments are not configured yet. Please contact the admin: {admin}",
    },
    "receipt_got": {
        "uz": (
            "✅ Chek qabul qilindi (to'lov #{pid}).\n\n"
            "Tekshirilgach xabar beramiz va tekshiruvlar avtomatik qo'shiladi."
        ),
        "en": (
            "✅ Receipt received (payment #{pid}).\n\n"
            "You will be notified once it is confirmed and credits are added."
        ),
    },
    "receipt_expected": {
        "uz": (
            "Chekni kutyapman. Agar fikringizdan qaytgan bo'lsangiz, "
            "«{btn}» tugmasini bosing."
        ),
        "en": "I am waiting for the receipt. Changed your mind? Press «{btn}».",
    },
    "payment_ok": {
        "uz": (
            "🎉 To'lovingiz tasdiqlandi!\n\n{granted}\n\n"
            "Rahmat. «{btn}» tugmasi bilan davom eting."
        ),
        "en": "🎉 Your payment is confirmed!\n\n{granted}\n\nThank you. Press «{btn}» to continue.",
    },
    "payment_no": {
        "uz": (
            "❌ To'lov #{pid} tasdiqlanmadi.\n\n"
            "Agar to'lov qilgan bo'lsangiz, chekni qaytadan yuboring yoki "
            "admin bilan bog'laning: {admin}"
        ),
        "en": (
            "❌ Payment #{pid} was not confirmed.\n\n"
            "If you did pay, send the receipt again or contact the admin: {admin}"
        ),
    },
    "granted_credits": {
        "uz": "Hisobingizga <b>{n} ta tekshiruv</b> qo'shildi.",
        "en": "<b>{n} checks</b> have been added to your account.",
    },
    "granted_days": {
        "uz": "<b>{n} kunlik cheksiz</b> tarif ochildi (kuniga {cap} tagacha).",
        "en": "<b>{n} days unlimited</b> is now active (up to {cap} per day).",
    },
    "invite": {
        "uz": (
            "🎁 <b>Do'st taklif qiling</b>\n\n"
            "Havolangiz:\n{link}\n\n"
            "Do'stingiz shu havola orqali kirib, birinchi inshosini "
            "tekshirtirsa, sizga <b>+{bonus} tekshiruv</b> qo'shiladi. "
            "Unga ham {free} ta bepul tekshiruv beriladi.\n\n"
            "Hozircha taklif qilganlaringiz: <b>{invited}</b>"
        ),
        "en": (
            "🎁 <b>Invite a friend</b>\n\n"
            "Your link:\n{link}\n\n"
            "When your friend joins through it and completes their first check, "
            "you get <b>+{bonus} check</b>. They get {free} free checks too.\n\n"
            "Invited so far: <b>{invited}</b>"
        ),
    },
    "ref_bonus": {
        "uz": "🎁 Taklif qilgan do'stingiz tekshiruvdan o'tkazdi — sizga +{n} tekshiruv qo'shildi!",
        "en": "🎁 Your invited friend completed a check — +{n} check added to your balance!",
    },
    "help": {
        "uz": (
            "ℹ️ <b>Qanday ishlaydi</b>\n\n"
            "1. «Insho tekshirish» → vazifa turini tanlaysiz\n"
            "2. Savol matnini yuborasiz\n"
            "3. Inshoni matn yoki rasm ko'rinishida yuborasiz\n"
            "4. Bir daqiqada to'liq tahlil olasiz\n\n"
            "<b>Nima olasiz:</b> har mezon bo'yicha band ball va sababi, "
            "eng qimmatga tushayotgan 6 tagacha xato (aynan sizning "
            "gapingizdan iqtibos bilan), keyingi yarim ballga chiqish uchun "
            "3 ta aniq qadam, va bitta xatboshingizning band 8 darajasidagi "
            "qayta yozilgan varianti.\n\n"
            "<b>Halol ogohlantirish:</b> bu <i>taxminiy</i> baho. Rasmiy "
            "IELTS bahosi emas va uni almashtira olmaydi. Amaliyot uchun "
            "mo'ljallangan.\n\n"
            "Savol/taklif: {admin}"
        ),
        "en": (
            "ℹ️ <b>How it works</b>\n\n"
            "1. «Check my essay» → pick the task type\n"
            "2. Send the question prompt\n"
            "3. Send the essay as text or a photo\n"
            "4. Get the full analysis in a minute\n\n"
            "<b>What you get:</b> a band for each criterion with the reason, "
            "up to 6 mistakes that cost you the most marks (quoted from your "
            "own sentences), 3 concrete steps to the next half band, and one "
            "of your paragraphs rewritten at band 8.\n\n"
            "<b>Honest warning:</b> this is an <i>estimate</i>. It is not an "
            "official IELTS score and cannot replace one. It is for practice.\n\n"
            "Questions: {admin}"
        ),
    },
    "disclaimer": {
        "uz": "⚠️ Taxminiy baho — rasmiy IELTS natijasi emas.",
        "en": "⚠️ Estimated score — not an official IELTS result.",
    },
    "grader_failed": {
        "uz": (
            "😔 Tekshirib bo'lmadi — modelda vaqtinchalik nosozlik.\n\n"
            "Hisobingizdan hech narsa yechilmadi. Bir-ikki daqiqadan keyin "
            "qayta urinib ko'ring."
        ),
        "en": (
            "😔 The check failed — a temporary model error.\n\n"
            "Nothing was deducted. Please try again in a minute or two."
        ),
    },
    "from_cache": {
        "uz": ("♻️ Bu insho avval tekshirilgan — <b>aynan o'sha natija</b> "
               "qaytarildi va tekshiruv hisobingizdan yechilmadi.\n\n"
               "Bir xil insho har doim bir xil ball olishi kerak, aks holda "
               "baholarga ishonib bo'lmaydi.\n\n"
               "Ikkinchi fikr olmoqchi bo'lsangiz, quyidagi tugmani bosing "
               "(bitta tekshiruv yechiladi)."),
        "en": ("♻️ This essay was checked before — the <b>exact same result</b> "
               "was returned and no check was deducted.\n\n"
               "The same essay must always get the same band, otherwise the "
               "scores cannot be trusted.\n\n"
               "Want a second opinion? Press the button below (one check will "
               "be used)."),
    },
    "regrade": {"uz": "🔄 Qayta baholash", "en": "🔄 Grade again"},
    "nothing_to_regrade": {
        "uz": "Qayta baholash uchun insho topilmadi. Yangisini yuboring.",
        "en": "No essay found to grade again. Send a new one.",
    },
    "cancelled": {"uz": "Bekor qilindi.", "en": "Cancelled."},
    "send_text_or_photo": {
        "uz": "Insho matnini yoki qo'lyozma rasmini yuboring.",
        "en": "Send the essay text or a photo of your handwriting.",
    },
}

# Natija sarlavhalari
RES = {
    "score": {"uz": "Umumiy taxminiy ball", "en": "Estimated overall band"},
    "score_lang_only": {
        "uz": "Til bo'yicha taxminiy ball",
        "en": "Estimated band — language only",
    },
    "no_question_warn": {
        "uz": ("⚠️ Savol (yoki grafik) yuborilmagani uchun <b>Task</b> mezoni "
               "baholanmadi va yuqoridagi ballga <b>qo'shilmadi</b>. Haqiqiy "
               "umumiy ball bundan past bo'lishi mumkin — javob mavzuga to'liq "
               "mos kelmasa, Task mezoni butun ballni tushiradi.\n"
               "To'liq baho uchun savolni ham yuboring."),
        "en": ("⚠️ Without the question (or the chart) the <b>Task</b> "
               "criterion could not be assessed and is <b>excluded</b> from the "
               "band above. Your real overall band may be lower — if the "
               "response does not fully address the question, that criterion "
               "pulls the whole score down.\nSend the question for a full "
               "assessment."),
    },
    "not_assessed": {"uz": "baholanmadi", "en": "not assessed"},
    "words": {"uz": "So'z soni", "en": "Word count"},
    "short": {"uz": "kam — bu Task ballini pasaytiradi", "en": "under length — this lowers the task score"},
    "criteria": {"uz": "Mezonlar", "en": "Criteria"},
    "errors": {"uz": "Eng qimmatga tushgan xatolar", "en": "Mistakes that cost you most"},
    "instead": {"uz": "kerak", "en": "should be"},
    "upgrades": {"uz": "Keyingi yarim ballga chiqish uchun", "en": "To reach the next half band"},
    "rewrite": {"uz": "Bitta xatboshingiz band 8 darajasida", "en": "One of your paragraphs at band 8"},
    "your": {"uz": "Sizniki", "en": "Yours"},
    "better": {"uz": "Yaxshilangan", "en": "Improved"},
    "summary": {"uz": "Xulosa", "en": "Summary"},
    "transcript": {"uz": "O'qilgan matn", "en": "Transcribed text"},
    "off_topic": {
        "uz": "❗ Javob savolga to'liq mos kelmayapti — bu Task ballini keskin tushiradi.",
        "en": "❗ The response does not fully address the question — this sharply lowers the task score.",
    },
    "memorised": {
        "uz": "❗ Yodlab olingan shablon iboralar sezildi — imtihonda bu ball tushiradi.",
        "en": "❗ Memorised template language detected — this lowers the score in the real exam.",
    },
    "left": {"uz": "Qolgan tekshiruv", "en": "Checks left"},
}


def t(key: str, lang: str = "uz", **kw) -> str:
    s = T[key].get(lang, T[key]["uz"])
    return s.format(**kw) if kw else s


def btn(key: str, lang: str = "uz") -> str:
    return BTN[key].get(lang, BTN[key]["uz"])


def res(key: str, lang: str = "uz") -> str:
    return RES[key].get(lang, RES[key]["uz"])

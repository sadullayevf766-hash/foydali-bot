# IELTS Writing tekshiruvchi bot

Foydali Bot bilan **bir jarayonda** ishlaydigan ikkinchi bot. Alohida token,
alohida jadvallar (`ielts_*`), alohida mantiq — lekin bitta Render xizmati.

## Nega bir jarayonda

Render bepul tarifi oyiga 750 instance-soat beradi, oyda esa 744 soat bor.
Ya'ni 24/7 ishlaydigan **bitta** xizmat butun kvotani yeydi va ikkinchi bepul
xizmat ochib bo'lmaydi. Ikkala bot bir jarayonda yashasa qo'shimcha soat
sarflanmaydi.

Kirish nuqtasi o'zgarmadi: `python bot.py` hamon ishlaydi, lekin endi u
`run_all.py` ga o'tadi va ikkala botni ko'taradi. IELTS tokeni bo'lmasa,
IELTS bot jim o'tkazib yuboriladi — Foydali Bot baribir ishlaydi.

## Ishga tushirish uchun kerak bo'lgan qadamlar

### 1. Yangi bot yarating (2 daqiqa)

@BotFather → `/newbot` → nom va username bering. Tokenni saqlab qo'ying.

Keyin o'sha yerda:

```
/setdescription
IELTS Writing inshoyingizni tekshiradi: 4 ta rasmiy mezon bo'yicha taxminiy band ball, xatolaringiz ro'yxati va keyingi yarim ballga chiqish uchun 3 ta aniq qadam. Qo'lyozmani rasmdan o'qiydi.

/setabouttext
IELTS Writing tekshiruvchi — band ball, xatolar va tuzatish. Task 1 va Task 2.

/setcommands
start - Boshlash
balans - Balansim
tarif - Tarif olish
taklif - Do'st taklif qilish
help - Yordam
```

### 2. Gemini kaliti (2 daqiqa)

https://aistudio.google.com/apikey → **Create API key**. Bepul, karta
so'ramaydi. Bu kalit inshoni baholaydi va qo'lyozmani o'qiydi.

### 3. Render'ga o'zgaruvchilarni qo'shing (3 daqiqa)

Render → `foydali-bot` xizmati → **Environment** → quyidagilarni qo'shing:

| Kalit | Qiymat |
|---|---|
| `IELTS_BOT_TOKEN` | BotFather bergan token |
| `IELTS_BOT_USERNAME` | bot username'i, `@` siz |
| `GEMINI_API_KEY` | AI Studio kaliti |
| `CARD_NUMBER` | to'lov keladigan karta raqami |
| `CARD_HOLDER` | karta egasining ismi |
| `ADMIN_CONTACT` | sizning `@username` |

Saqlagach Render o'zi qayta deploy qiladi.

### 4. Botga `/start` yozing

Admin xabarlari (to'lov cheklari) sizga yetib borishi uchun **siz botga
kamida bir marta `/start` yozgan bo'lishingiz shart**. Aks holda Telegram
botga sizga yozishga ruxsat bermaydi.

## Pul qanday keladi

1. Foydalanuvchining bepul tekshiruvlari tugaydi → bot tarif ko'rsatadi
2. U tarifni tanlaydi → bot karta raqami va summani beradi
3. U o'tkazadi va **chek skrinshotini botga yuboradi**
4. Sizga chek rasmi ✅/❌ tugmalari bilan keladi
5. ✅ bosasiz → tekshiruvlar avtomatik qo'shiladi, foydalanuvchiga xabar ketadi

Sizning ishingiz: **bitta tugma bosish**.

`/stats` — foydalanuvchilar, tekshiruvlar, sotuvlar, tushum va $30 maqsadigacha
qancha qolgani. `/pending` — hal qilinmagan to'lovlar. `/bering <id> <soni>` —
qo'lda kredit qo'shish.

## Tariflar

| Tarif | Nima beradi | Narx |
|---|---|---|
| Boshlang'ich | 5 ta tekshiruv | 19 000 so'm |
| Pro | 20 ta tekshiruv | 49 000 so'm |
| 30 kun cheksiz | kuniga 5 tagacha | 79 000 so'm |

Narxlar `ielts/config.py` dagi `PLANS` da. $30 ≈ 390 000 so'm — bu 8 ta "Pro"
yoki 5 ta "cheksiz" sotuvi.

## Xavfsizlik va halollik qoidalari

- Ball **taxminiy** ekani har javobda va yordam matnida yozilgan. Rasmiy
  IELTS natijasi sifatida ko'rsatilmaydi.
- Model xato bersa foydalanuvchi krediti **yechilmaydi** (`_run_grading`
  faqat muvaffaqiyatdan keyin `consume` qiladi).
- Admin tugmani ikki marta bossa tarif ikki marta berilmaydi
  (`set_payment_status` faqat `kutilmoqda` holatidan o'tkazadi).
- Referal bonusi taklif qilingan odam **haqiqiy tekshiruvdan** o'tkazgandan
  keyin beriladi — soxta akkaunt ochib bonus yig'ib bo'lmaydi.
- Foydalanuvchi matni HTML'ga qochiriladi (`html.escape`).

## Sinov

```
python test_ielts.py
```

Tarmoqqa chiqmaydi, vaqtinchalik bazada ishlaydi. Postgres'da tekshirish
uchun `DATABASE_URL` bilan ishga tushiring.

## Uyqu muammosi

Render bepul web service 15 daqiqa harakatsizlikdan keyin uxlaydi — uxlagan
bot Telegram'dan xabar olmaydi. `.github/workflows/keepalive.yml` har 10
daqiqada xizmatni turtib uyg'oq saqlaydi (ommaviy repoda GitHub Actions
bepul). Boshqa URL kerak bo'lsa repo Settings → Variables → `KEEPALIVE_URL`.

# 🤖 Foydali Bot

Telegram uchun foydali utility bot. Kundalik kerakli 4 ta vosita bitta joyda:

- 📄 **Rasm → PDF** — rasmlarni bitta PDF fayl qiladi
- 🔗 **PDF birlashtirish** — bir nechta PDF'ni bittaga qo'shadi
- ⚡ **QR-kod** — istalgan matn/havoladan QR-kod
- 💱 **Valyuta kursi** — O'zbekiston Markaziy banki kursi

💎 **Monetizatsiya:** bepul foydalanuvchiga kunlik limit, **Premium** esa cheksiz —
to'lov **Telegram Stars** orqali (bank yoki Click/Payme kerak emas).

---

## 🚀 Ishga tushirish (5 daqiqa)

### 1. Bot yarating
1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring
2. `/newbot` yuboring → bot nomi va username bering
3. Sizga **token** beradi (masalan `7123456789:AAH...`) — saqlang

### 2. To'lovni yoqing (Telegram Stars)
BotFather'da: bot → **Payments** → Telegram Stars allaqachon yoqilgan.
Qo'shimcha provayder kerak emas.

### 3. O'rnatish (Windows)
```powershell
cd D:\foydali-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Sozlash
```powershell
copy .env.example .env
notepad .env
```
`.env` faylga yozing:
```
BOT_TOKEN=7123456789:AAH...     # BotFather tokeni
ADMIN_ID=123456789              # @userinfobot dan oling
```

### 5. Ishga tushirish
```powershell
python bot.py
```
Botingizga `/start` yuboring — ishlaydi! ✅

---

## 💰 Daromad qanday keladi

| Manba | Izoh |
|-------|------|
| **Premium obuna** | Bepul limit tugagach foydalanuvchi 💎 Premium oladi (Stars) |
| **Telegram Stars → pul** | Telegram Stars'ni real pulga aylantirib olasiz |

**Statistika:** botga `/stats` yuboring (faqat admin) — foydalanuvchilar soni,
bugun faollar, premium soni va jami daromadni ko'rasiz.

### Narxni o'zgartirish
`.env` faylda:
```
PREMIUM_PRICE_STARS=25    # 30 kunlik narx (Stars, ~6000 so'm)
FREE_DAILY_LIMIT=5        # bepul kunlik amallar
PREMIUM_DAYS=30
```

---

## 📈 Kuniga ~1 soatlik ish rejasi

1. **Reklama (20 daq):** botni Telegram kanallar/guruhlarga tarqating
2. **Qo'llab-quvvatlash (20 daq):** foydalanuvchi savollariga javob
3. **Yangi funksiya (vaqti-vaqti):** word→pdf, rasm siqish, tarjima qo'shing

Bot 24/7 ishlashi uchun uni serverga (VPS) yoki doimiy yoqilgan
kompyuterga joylashtiring.

---

## 🚀 24/7 ishlash va boshqarish

Bot **avtomatik ishga tushadi** — kompyuter yoqilib, siz tizimga kirganingizda
o'zi yashirin (oynasiz) ishga tushadi va to'xtab qolsa o'zi qayta yonadi.

- **Avtoyuklash:** `launcher.vbs` nusxasi Startup papkasida (`FoydaliBot.vbs`)
- **Loglar:** `bot.log` faylida (xatolarni shu yerdan ko'rasiz)
- **Qo'lda yoqish (loglar ko'rinadigan oyna bilan):** `start_bot.bat` ni 2 marta bosing
- **To'xtatish:** Task Manager → `python.exe` (bot.py) jarayonini tugating,
  yoki PowerShell:
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  ```

⚠️ **Muhim cheklov:** Startup faqat siz kompyuterga **kirganingizda** ishlaydi.
Kompyuter o'chsa yoki siz chiqib ketsangiz — bot to'xtaydi. Haqiqiy uzluksiz
(24/7) ishlash uchun botni **VPS serverga** (oyiga ~$4-5) joylashtirish kerak.

## 🔧 Texnik

- Python 3.10+ (bu mashinada 3.14)
- `python-telegram-bot` (async)
- SQLite (`bot.db` — avtomatik yaratiladi)
- Bitta-nusxa qulfi (socket 127.0.0.1:47654) — ikki marta ishlamaydi
- Tashqi pullik API yo'q (valyuta — bepul cbu.uz)

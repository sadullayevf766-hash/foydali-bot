# Bepul 24/7 deploy — Neon Postgres + Render

Maqsad: noutbuk o'chganda ham bot ishlasin, ma'lumot yo'qolmasin, pul
to'lanmasin.

---

## Nega shunday qilinmoqda

Render bepul tarifida **fayl tizimi vaqtinchalik**: xizmat uyquga ketganda
yoki qayta deploy qilinganda `bot.db` fayli o'chadi
([Render hujjati](https://render.com/docs/free)). Bepul tarifda disk ulab
bo'lmaydi.

Bu bot Premium sotgani uchun bu yo'l qo'yib bo'lmaydigan xato: kimdir 150 ⭐
to'lab yillik obuna olsa, keyingi uyqudan keyin obunasi yo'qolardi.

Yechim: ma'lumot Render'da emas, **Neon**'dagi bepul Postgres'da saqlanadi.
Neon bepul tarifi muddatsiz va karta talab qilmaydi. (Render'ning o'z bepul
Postgres'i yaramaydi — u 30 kundan keyin tugaydi.)

Kod ikkala bazani ham qo'llab-quvvatlaydi: `DATABASE_URL` bo'lsa Postgres,
bo'lmasa SQLite. Shuning uchun lokal ishlash va testlar o'zgarishsiz qoladi.

---

## 1. Neon'da bepul baza yarating (~3 daqiqa)

1. [neon.com](https://neon.com) → GitHub akkaunti bilan kiring (karta kerak emas)
2. **Create project** → nomi `foydali-bot`, region: Europe (eng yaqini)
3. Ochilgan sahifada **Connection string** ni nusxalang. Ko'rinishi:

```
postgresql://foydali_owner:AbC123@ep-xxx.eu-central-1.aws.neon.tech/foydali?sslmode=require
```

Bu parol — uni hech kimga bermang va GitHub'ga yuklamang.

---

## 2. Postgres yo'lini tekshiring va ma'lumotni ko'chiring

PowerShell'da, `D:\foydali-bot` papkasida:

```powershell
$env:DATABASE_URL="<Neon'dan nusxalagan connection string>"
venv\Scripts\python.exe test_growth.py
```

Bu butun mantiqni haqiqiy Postgres'da sinaydi va o'z sinov yozuvlarini
tozalab ketadi. `HAMMA TEST O'TDI ✅` chiqishi kerak.

Keyin mavjud foydalanuvchilarni ko'chiring:

```powershell
venv\Scripts\python.exe migrate_to_postgres.py
```

Skript jadvallarni yaratadi, `bot.db` dagi hamma yozuvni ko'chiradi va
oxirida sonlarni tekshiradi. Qayta ishga tushirish xavfsiz — yozuvlar
takrorlanmaydi.

---

## 3. Render'da sozlang

Render dashboard → `foydali-bot` xizmati → **Environment**:

| Nomi | Qiymati |
| --- | --- |
| `BOT_TOKEN` | (allaqachon bor) |
| `ADMIN_ID` | (allaqachon bor) |
| `DATABASE_URL` | Neon connection string |
| `STORAGE_CHAT_ID` | inline QR uchun kanal ID (SETUP.md) |

⚠️ `DATABASE_URL` qo'yilmasa bot yana SQLite'ga tushadi va ma'lumot yo'qoladi.
Deploy'dan keyin Render loglarida shu qatorni tekshiring:

```
Baza: Postgres
```

Agar `Baza: SQLite (...)` deb yozsa — `DATABASE_URL` o'rnatilmagan.

---

## 4. Noutbukdagi avtoyuklashni o'chiring ⚠️ MAJBURIY

Hozir bot **ikki joyda** ishlayapti va logda `409 Conflict` xatosi bor:
Telegram bir vaqtda faqat bitta nusxaga ruxsat beradi, qolganlari uziladi va
xabarlar yo'qoladi.

1. `Win + R` → `shell:startup` → Enter
2. Ochilgan papkadan `FoydaliBot.vbs` ni **o'chiring**
3. Ishlab turgan jarayonlarni to'xtating:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*bot.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

---

## 5. Uyquga ketmasligi uchun ping

Render bepul xizmati 15 daqiqa tinchlikdan keyin uxlaydi va uyg'onish ~1
daqiqa oladi. Bot uchun bu yomon: yangi odam javob kutib ketib qoladi.

[cron-job.org](https://cron-job.org) (bepul) da:

- URL: `https://foydali-bot-6dza.onrender.com`
- Interval: har **10 daqiqada**

### Diqqat: 750 soat chegarasi

Render bepul tarifi oyiga **750 instance-soat** beradi, oyda esa 744 soat bor.
24/7 uyg'oq tursa chegaraga tiq to'g'ri keladi — **ortiqcha bepul xizmat
ochmang**, aks holda ikkalasi ham o'chadi.

Xavfsizroq variant: ping'ni faqat 06:00–24:00 oralig'ida ishlating
(cron-job.org buni qo'llab-quvvatlaydi). Kechasi bot uxlaydi, oyiga ~540
soat sarflanadi va zaxira qoladi.

---

## 6. Deploy

```bash
git push
```

Render avtomatik deploy qiladi. Loglarda `Baza: Postgres` va
`Bot ishga tushdi ✅` ko'rinishi kerak.

Keyin Telegram'da `/stats` yuboring — foydalanuvchilar soni ko'chirilgan
ma'lumotga mos kelishi kerak.

---

## Tekshiruv ro'yxati

- [ ] Neon bazasi yaratildi
- [ ] `test_growth.py` Postgres'da o'tdi
- [ ] `migrate_to_postgres.py` ma'lumotni ko'chirdi
- [ ] Render'da `DATABASE_URL` o'rnatildi
- [ ] Noutbukdagi `FoydaliBot.vbs` o'chirildi, jarayonlar to'xtatildi
- [ ] cron-job.org ping sozlandi
- [ ] BotFather'da `/setinline` yoqildi (SETUP.md)
- [ ] Render logida `Baza: Postgres` yozuvi bor
- [ ] `/stats` to'g'ri sonlarni ko'rsatyapti

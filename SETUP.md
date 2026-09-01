# Sozlash — bir martalik, ~5 daqiqa

Kod tayyor, lekin ikkita narsa **BotFather'da** yoqilishi kerak. Usiz inline
rejim (botning o'zi tarqalishining asosiy yo'li) umuman ishlamaydi.

---

## 1. Inline rejimni yoqing ⚠️ ENG MUHIMI

[@BotFather](https://t.me/BotFather) ga kiring:

```
/setinline
```

→ botingizni tanlang → placeholder matnini yuboring:

```
kurs, QR yoki son yozing...
```

**Nega muhim:** shundan keyin har qanday guruhda `@botingiz` deb yozib kurs
yoki QR yuborish mumkin bo'ladi. Telegram bunday xabar tepasiga avtomatik
**"via @botingiz"** deb yozadi — guruhdagi hamma ko'radi va bosishi mumkin.
Bu reklama emas, oddiy foydalanishning yon ta'siri. Sizdan hech narsa talab
qilmaydi.

---

## 2. QR uchun saqlash chati (ixtiyoriy, lekin tavsiya)

Inline javob ichida fayl yuklab bo'lmaydi — Telegram tayyor `file_id` talab
qiladi. Shuning uchun QR rasmi avval biror chatga yuborilib, keyin ishlatiladi.

1. Telegramda **yangi yopiq kanal** yarating (nomi ixtiyoriy, masalan "Bot fayllari")
2. Botingizni o'sha kanalga **admin** qilib qo'shing
3. Kanal ID sini oling: kanalga biror xabar yuboring va
   [@userinfobot](https://t.me/userinfobot) ga forward qiling → `-100...` ko'rinishidagi raqam
4. `.env` fayliga qo'shing:

```
STORAGE_CHAT_ID=-1001234567890
```

Agar bu qadamni o'tkazib yuborsangiz: inline'da kurs va son→so'z ishlaydi,
QR o'rniga botga havola chiqadi. Bot buzilmaydi.

---

## 3. Buyruqlar ro'yxati

BotFather'da `/setcommands` → botni tanlang → shuni yuboring:

```
start - Boshlash
kurs - Valyuta kursi
taklif - Do'stni taklif qilish (bepul Premium)
premium - Premium obuna
```

---

## 4. Telegram qidiruvida topilish

Bu sizning yagona bepul trafik manbangiz. Telegram bot qidiruvi **nom** va
**tavsif** bo'yicha ishlaydi, shuning uchun kalit so'zlar muhim.

`/setdescription` → botni tanlang → shuni yuboring:

```
Rasmni PDF qiladi, PDF birlashtiradi va bo'ladi, QR kod yaratadi, matnni Word/PDF hujjat qiladi, valyuta kursini ko'rsatadi, sonni so'z bilan yozadi. Talabalar va buxgalterlar uchun. Bepul.
```

`/setabouttext` → botni tanlang:

```
PDF, QR, valyuta kursi va hujjat tayyorlash — bitta botda. Bepul.
```

**Bot nomi** (`/setname`) ham qidiruvga ta'sir qiladi. Hozirgi "Foydali Bot"
degan nom hech narsa aytmaydi. Kalit so'z qo'shing, masalan:

```
PDF va QR — Foydali Bot
```

---

## 5. Botni qayta ishga tushiring

⚠️ Hozir **ikkita** bot jarayoni ishlab turibdi (18044 va 17096). Bu xato —
ikkalasi ham `getUpdates` chaqiradi va xabarlar yo'qolishi mumkin.

PowerShell'da:

```powershell
Get-Process python | Where-Object { $_.Path -like "*foydali-bot*" } | Stop-Process -Force
```

Keyin odatdagidek ishga tushiring (`start_bot.bat` yoki `launcher.vbs`).

Ishga tushgach `/stats` yuboring — yangi voronka statistikasi ko'rinishi kerak.

---

## Nima o'zgardi (kod tomoni)

| O'zgarish | Nima beradi |
| --- | --- |
| Inline rejim (`@bot kurs`, `@bot 5000`, `@bot matn`) | Guruhlarda "via @bot" — asosiy tarqalish yo'li |
| Referal: `/taklif` | Taklif qilgan 3 kun Premium oladi. Bonus faqat taklif qilingan odam **haqiqatan foydalangandan** keyin — soxta akkaunt yig'ish foydasiz |
| Limit xabari | Avval "tugmani bosing" der edi. Endi to'lov tugmalari darhol chiqadi |
| Ikki tarif: 30 kun 25 ⭐ / 1 yil 150 ⭐ | Qimmatrog'i oqilona ko'rinadi, o'rtacha tushum oshadi |
| `/stats` voronkasi | Odam qaysi bosqichda yo'qolayotgani ko'rinadi |
| Manba kuzatuvi | `?start=xxx` havolalari qaysi joydan odam kelganini ko'rsatadi |

## Testlar

```powershell
venv\Scripts\python.exe test_growth.py
```

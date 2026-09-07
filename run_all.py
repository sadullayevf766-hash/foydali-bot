"""Ikkala botni BITTA jarayonda ishga tushiradi.

Nega bitta jarayon: Render bepul tarifida oyiga 750 instance-soat bor, oyda
esa 744 soat — ya'ni 24/7 ishlaydigan bitta xizmat butun kvotani yeydi va
ikkinchi bepul xizmat ochib bo'lmaydi. Ikkala bot bir jarayonda yashasa
qo'shimcha soat sarflanmaydi.

Botlar bir-biridan mustaqil: biri ishga tushmasa (masalan tokeni yo'q yoki
Telegram javob bermasa), ikkinchisi baribir ishlaydi.
"""
import asyncio
import logging
import os

from telegram import Update

import bot as foydali
import storage
from ielts import bot as ielts_bot
from ielts import config as ielts_config

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("run_all")

# Render 15 daqiqada uxlaydi — 10 daqiqa xavfsiz chegara qoldiradi.
PING_MINUTES = 10


async def _self_ping():
    """Render bepul xizmati 15 daqiqa harakatsizlikdan keyin uxlaydi.

    Uxlagan bot Telegram'dan yangilanish olmaydi — ya'ni o'lik bo'ladi.
    GitHub Actions cron bunga yaramadi: `*/10` deb yozilgan bo'lsa ham
    bepul runnerlarda amalda ~2 soatda bir marta ishga tushdi (o'lchandi,
    2026-09-06). Shuning uchun xizmat o'zini o'zi turtadi: so'rov tashqi
    URL orqali ketib qaytadi, ya'ni Render uchun bu haqiqiy kiruvchi
    trafik.

    `RENDER_EXTERNAL_URL` ni Render o'zi beradi — sozlash shart emas.
    Lokalda bu o'zgaruvchi yo'q, shuning uchun ping umuman ishlamaydi.
    """
    url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("KEEPALIVE_URL")
    if not url:
        return
    import httpx

    log.info("O'z-o'zini ping: %s (har %s daqiqada)", url, PING_MINUTES)
    while True:
        await asyncio.sleep(PING_MINUTES * 60)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.get(url)
        except Exception as e:
            # Ping muvaffaqiyatsiz bo'lsa bot ishlashda davom etadi.
            log.debug("Ping o'tmadi: %s", e)


async def _start(app, name: str):
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        # Uzoq uzilishdan keyin to'plangan eski xabarlarga javob bermaymiz:
        # foydalanuvchi allaqachon ketgan bo'ladi, javob esa chalkashtiradi.
        drop_pending_updates=True,
    )
    foydali.RUNNING.append(name)
    log.info("%s ishga tushdi ✅", name)


async def _stop(app, name: str):
    try:
        if app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        log.info("%s to'xtatildi", name)
    except Exception:
        log.exception("%s ni to'xtatishda xatolik", name)


async def amain():
    started: list[tuple] = []
    # RUN_ONLY=ielts — lokalda faqat IELTS botni sinash uchun. Foydali Bot
    # Render'da ishlab turgani uchun uni ikkinchi marta ko'tarish 409
    # Conflict beradi va xabarlar yo'qoladi.
    only = os.getenv("RUN_ONLY", "").strip().lower()

    if only in ("", "foydali", "all"):
        try:
            app = foydali.build_app()
            await _start(app, "Foydali Bot")
            started.append((app, "Foydali Bot"))
        except Exception:
            log.exception("Foydali Bot ishga tushmadi")

    if only in ("", "ielts", "all"):
        gaps = ielts_config.missing()
        if gaps:
            log.warning("IELTS bot o'chiq — yetishmayapti: %s", ", ".join(gaps))
        else:
            try:
                app = ielts_bot.build_app()
                await _start(app, "IELTS Bot")
                started.append((app, "IELTS Bot"))
            except Exception:
                log.exception("IELTS bot ishga tushmadi")

    if not started:
        raise SystemExit("Hech qaysi bot ishga tushmadi — loglarni tekshiring")

    log.info("Baza: %s", storage.label())
    ping = asyncio.create_task(_self_ping())
    try:
        await asyncio.Event().wait()  # cheksiz kutish
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        ping.cancel()
        for app, name in started:
            await _stop(app, name)


def main():
    foydali._ensure_single_instance()
    foydali._start_health_server()  # Render $PORT ni talab qiladi
    if os.getenv("PORT"):
        log.info("Health-server %s portda", os.getenv("PORT"))
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        log.info("To'xtatildi")


if __name__ == "__main__":
    main()

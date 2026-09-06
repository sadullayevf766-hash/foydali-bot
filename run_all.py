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

    try:
        app = foydali.build_app()
        await _start(app, "Foydali Bot")
        started.append((app, "Foydali Bot"))
    except Exception:
        log.exception("Foydali Bot ishga tushmadi")

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
    try:
        await asyncio.Event().wait()  # cheksiz kutish
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
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

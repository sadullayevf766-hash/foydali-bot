"""Render'dagi xizmatga o'zgaruvchilarni qo'yadi va deploy qiladi.

    python render_setup.py           # ko'rsatadi, o'zgartirmaydi
    python render_setup.py --apply   # haqiqatan qo'yadi va deploy qiladi

`RENDER_API_KEY` .env dan yoki muhitdan o'qiladi.

MUHIM xavfsizlik nuqtasi: Render'ning `PUT /v1/services/{id}/env-vars`
uslubi ro'yxatni TO'LIQ ALMASHTIRADI. Ya'ni faqat yangi qiymatlarni
yuborsak, mavjud BOT_TOKEN va ADMIN_ID o'chib ketadi va ishlab turgan
Foydali Bot darhol qulaydi. Shuning uchun bu yerda avval mavjud ro'yxat
O'QILADI, ustiga yangilari QO'SHILADI va butun ro'yxat qaytariladi.
"""
import json
import os
import sys
import time

import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API = "https://api.render.com/v1"
KEY = os.getenv("RENDER_API_KEY", "").strip()
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "foydali-bot").strip()
ENV_FILE = os.path.join(BASE_DIR, "render-env.txt")


def head(k: str, v: str) -> str:
    """Maxfiy qiymatni logda ko'rsatish uchun qisqartiradi."""
    if not v:
        return "(bo'sh)"
    if k in ("CARD_HOLDER", "ADMIN_CONTACT", "IELTS_BOT_USERNAME"):
        return v
    return f"{v[:4]}…({len(v)} belgi)"


def client() -> httpx.Client:
    return httpx.Client(
        base_url=API,
        headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
        timeout=60,
    )


def read_wanted() -> dict:
    if not os.path.exists(ENV_FILE):
        sys.exit(f"❌ {ENV_FILE} topilmadi")
    out = {}
    for line in open(ENV_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if v.strip():
            out[k.strip()] = v.strip()
    return out


def find_service(c: httpx.Client) -> dict:
    r = c.get("/services", params={"limit": 100})
    r.raise_for_status()
    items = r.json()
    services = [i.get("service", i) for i in items]
    for s in services:
        if s.get("name") == SERVICE_NAME:
            return s
    names = ", ".join(s.get("name", "?") for s in services) or "(hech narsa)"
    sys.exit(f"❌ '{SERVICE_NAME}' topilmadi. Mavjud xizmatlar: {names}")


def get_env(c: httpx.Client, sid: str) -> dict:
    r = c.get(f"/services/{sid}/env-vars", params={"limit": 100})
    r.raise_for_status()
    out = {}
    for item in r.json():
        ev = item.get("envVar", item)
        # Fayl turidagi yozuvlarda `key` bo'lmaydi — ularni chetlab o'tamiz.
        if "key" in ev:
            out[ev["key"]] = ev.get("value", "")
    return out


def main() -> int:
    if not KEY:
        print("❌ RENDER_API_KEY yo'q.\n"
              "   Render → Account Settings → API Keys → Create API Key\n"
              "   Keyin .env ga: RENDER_API_KEY=...")
        return 1

    apply = "--apply" in sys.argv
    wanted = read_wanted()

    with client() as c:
        svc = find_service(c)
        sid = svc["id"]
        print(f"Xizmat: {svc['name']}  ({sid})")
        print(f"URL   : {svc.get('serviceDetails', {}).get('url', '?')}\n")

        current = get_env(c, sid)
        print(f"Hozirgi o'zgaruvchilar ({len(current)} ta):")
        for k in sorted(current):
            print(f"   {k:22} = {head(k, current[k])}")

        new_keys = [k for k in wanted if k not in current]
        changed = [k for k in wanted if k in current and current[k] != wanted[k]]
        print(f"\nQo'shiladi ({len(new_keys)}): {', '.join(new_keys) or '—'}")
        print(f"Yangilanadi ({len(changed)}): {', '.join(changed) or '—'}")

        if not new_keys and not changed:
            print("\n✅ Hammasi allaqachon joyida.")
            return 0

        if not apply:
            print("\n(Sinov rejimi. Haqiqatan qo'yish uchun: "
                  "python render_setup.py --apply)")
            return 0

        # Mavjudlarni SAQLAB, ustiga yangilarini qo'yamiz — aks holda
        # PUT butun ro'yxatni almashtirib, BOT_TOKEN ni o'chirib yuboradi.
        merged = dict(current)
        merged.update(wanted)
        payload = [{"key": k, "value": v} for k, v in merged.items()]

        r = c.put(f"/services/{sid}/env-vars", json=payload)
        if r.status_code >= 300:
            print(f"❌ O'zgaruvchilarni qo'yib bo'lmadi: {r.status_code} {r.text[:300]}")
            return 1
        print(f"\n✅ {len(payload)} ta o'zgaruvchi saqlandi")

        r = c.post(f"/services/{sid}/deploys", json={"clearCache": "do_not_clear"})
        if r.status_code >= 300:
            print(f"⚠️ Deploy so'rovi o'tmadi: {r.status_code} {r.text[:200]}")
            print("   (O'zgaruvchilar saqlandi — Render odatda o'zi qayta deploy qiladi)")
            return 0
        dep = r.json()
        did = dep.get("id", "?")
        print(f"🚀 Deploy boshlandi: {did}")

        for _ in range(60):
            time.sleep(10)
            d = c.get(f"/services/{sid}/deploys/{did}").json()
            status = d.get("status", "?")
            print(f"   {status}")
            if status in ("live", "build_failed", "update_failed", "canceled",
                          "deactivated", "pre_deploy_failed"):
                break
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

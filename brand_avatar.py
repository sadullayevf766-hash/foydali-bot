"""Bot uchun profil rasmini yasaydi va Telegram'ga qo'yadi.

    python brand_avatar.py           # faqat yasaydi (assets/avatar.png)
    python brand_avatar.py --upload  # yasab, botga o'rnatadi

Dizayn mantig'i: Telegram avatarni ro'yxatda ~40px qilib ko'rsatadi.
Shu o'lchamda MATN o'qilmaydi, shuning uchun "IELTS" deb yozilmagan —
bot nomi baribir avatar yonida turadi. O'qiladigan narsa faqat shakl va
rang: ko'k fonda oq varaq va yashil belgi. Bu bir qarashda "insho
tekshirildi" degan ma'noni beradi.

Qo'lyozma chiziqlari ataylab qo'yilgan — mahsulotning asosiy ustunligi
aynan qo'lda yozilgan inshoni o'qishi.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "assets")
SIZE = 512
SS = 4                      # supersampling: 4x chizib, keyin kichraytiramiz
S = SIZE * SS

# Ranglar. Ko'k — IELTS sohasida tanish, lekin to'q siyohrang variant
# raqiblarning och ko'kidan ajralib turadi. Yashil belgi — "to'g'ri".
BG_TOP = (26, 30, 68)
BG_BOTTOM = (44, 52, 112)
PAPER = (252, 252, 250)
RULE = (198, 210, 226)
INK = (120, 134, 156)
CHECK = (34, 197, 94)
CHECK_DARK = (22, 163, 74)


def _gradient() -> Image.Image:
    img = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(img)
    for y in range(S):
        k = y / S
        d.line(
            [(0, y), (S, y)],
            fill=tuple(
                int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * k) for i in range(3)
            ),
        )
    return img


def _paper() -> Image.Image:
    """Chiziqli varaq — ustida qo'lyozmaga o'xshash izlar bilan.

    O'lcham ataylab kichik: Telegram avatarni DOIRAGA kesadi, ya'ni
    kvadratning burchaklari yo'qoladi. Butun kompozitsiya markazdan
    ~0.80 radius ichida turishi kerak, aks holda varaqning burchagi
    kesilib, rasm buzilgandek ko'rinadi.
    """
    w, h = int(S * 0.46), int(S * 0.54)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = int(S * 0.022)
    d.rounded_rectangle([0, 0, w, h], radius=r, fill=PAPER + (255,))

    # Chiziqlar va ular ustidagi "yozuv" izlari.
    top, gap = int(h * 0.16), int(h * 0.135)
    pad = int(w * 0.12)
    # Har qatorning uzunligi har xil — bir xil bo'lsa jadvalga o'xshab qoladi.
    fill_ratio = (0.92, 0.78, 0.95, 0.62, 0.85)
    for i, ratio in enumerate(fill_ratio):
        y = top + i * gap
        if y > h - int(h * 0.12):
            break
        d.line([(pad, y), (w - pad, y)], fill=RULE + (255,), width=max(2, SS))
        # Yozuv izi: chiziq ustida ingichka to'lqin.
        x0, x1 = pad + int(w * 0.02), pad + int((w - 2 * pad) * ratio)
        pts = []
        for x in range(x0, x1, max(1, SS)):
            k = (x - x0) / max(1, (x1 - x0))
            wobble = math.sin(k * 26) * (h * 0.011) + math.sin(k * 61) * (h * 0.005)
            pts.append((x, y - int(h * 0.026) + wobble))
        if len(pts) > 1:
            d.line(pts, fill=INK + (255,), width=max(2, int(SS * 1.6)), joint="curve")
    return layer


def _check(img: Image.Image):
    """Katta yashil belgi — varaqdan biroz chiqib turadi (chuqurlik beradi)."""
    d = ImageDraw.Draw(img)
    cx, cy = S * 0.585, S * 0.605
    scale = S * 0.245
    pts = [
        (cx - scale * 0.72, cy - scale * 0.06),
        (cx - scale * 0.22, cy + scale * 0.46),
        (cx + scale * 0.78, cy - scale * 0.72),
    ]
    width = int(S * 0.072)
    # Soya — belgi varaqdan ajralib tursin.
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    off = int(S * 0.012)
    sd.line([(x + off, y + off) for x, y in pts], fill=(10, 14, 40, 110),
            width=width, joint="curve")
    for x, y in pts:
        sd.ellipse([x + off - width // 2, y + off - width // 2,
                    x + off + width // 2, y + off + width // 2],
                   fill=(10, 14, 40, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.012))
    img.alpha_composite(shadow)

    d = ImageDraw.Draw(img)
    d.line(pts, fill=CHECK + (255,), width=width, joint="curve")
    # Uchlarini yumaloqlaymiz — PIL joint="curve" faqat burchakni yumshatadi.
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - width // 2, y - width // 2, x + width // 2, y + width // 2],
                  fill=CHECK + (255,))
    # Pastki qirrada to'qroq chiziq — hajm hissi.
    d.line([(pts[1][0], pts[1][1]), (pts[2][0], pts[2][1])],
           fill=CHECK_DARK + (60,), width=int(width * 0.22))


def build() -> str:
    img = _gradient().convert("RGBA")

    paper = _paper().rotate(7, expand=True, resample=Image.BICUBIC)
    # Varaq soyasi.
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    px = int((S - paper.width) / 2 - S * 0.035)
    py = int((S - paper.height) / 2 - S * 0.025)
    sh.alpha_composite(paper, (px + int(S * 0.014), py + int(S * 0.018)))
    sh = sh.filter(ImageFilter.GaussianBlur(S * 0.018))
    sh.putalpha(sh.getchannel("A").point(lambda a: int(a * 0.45)))
    img.alpha_composite(sh)
    img.alpha_composite(paper, (px, py))

    _check(img)

    img = img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "avatar.png")
    img.save(path, quality=95)

    # Katta nusxa — YouTube/Instagram profillari uchun keyin asqotadi.
    big = _gradient().convert("RGB")
    img.resize((1024, 1024), Image.LANCZOS).save(
        os.path.join(OUT_DIR, "avatar_1024.png")
    )
    # Telegram doiraga kesadi — aynan shunday ko'rinishini ham saqlaymiz.
    mask = Image.new("L", (SIZE * 4, SIZE * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, SIZE * 4, SIZE * 4], fill=255)
    circ = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    circ.paste(img, (0, 0), mask.resize((SIZE, SIZE), Image.LANCZOS))
    circ.save(os.path.join(OUT_DIR, "avatar_circle.png"))

    # Kichik ko'rinish: Telegram ro'yxatida shunday ko'rinadi.
    circ.resize((48, 48), Image.LANCZOS).resize((192, 192), Image.NEAREST).save(
        os.path.join(OUT_DIR, "avatar_preview_48.png")
    )
    return path


def upload(path: str) -> bool:
    """Rasmni bot profiliga qo'yadi.

    Ikki nozik joy (ikkalasi ham sinovda "photo isn't specified" xatosini
    bergan edi):
      - `photo` oddiy fayl emas, JSON obyekt: {"type": "static",
        "photo": "attach://<nom>"}, faylning o'zi esa o'sha nom bilan
        multipart ichida yuboriladi;
      - format PNG emas, JPG bo'lishi shart.
    """
    import json

    import httpx

    from ielts import config

    jpg = os.path.splitext(path)[0] + ".jpg"
    Image.open(path).convert("RGB").save(jpg, "JPEG", quality=94)

    with open(jpg, "rb") as f:
        r = httpx.post(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/setMyProfilePhoto",
            data={"photo": json.dumps({"type": "static", "photo": "attach://pic"})},
            files={"pic": ("avatar.jpg", f, "image/jpeg")},
            timeout=90,
        )
    d = r.json()
    if d.get("ok"):
        print("✅ Profil rasmi o'rnatildi")
        return True
    print(f"❌ O'rnatilmadi: {r.status_code} — {d.get('description')}")
    return False


if __name__ == "__main__":
    p = build()
    print(f"Yaratildi: {p}")
    if "--upload" in sys.argv:
        raise SystemExit(0 if upload(p) else 1)

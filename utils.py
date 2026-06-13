"""Foydali amallar: Rasm->PDF, PDF birlashtirish, QR, valyuta."""
import io
from datetime import date, timedelta
import httpx
import qrcode
from PIL import Image
from pypdf import PdfReader, PdfWriter
from config import CBU_URL


def images_to_pdf(image_bytes_list: list[bytes]) -> bytes:
    """Bir nechta rasm baytlarini bitta PDF'ga aylantiradi."""
    images = []
    for b in image_bytes_list:
        img = Image.open(io.BytesIO(b))
        if img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)
    if not images:
        raise ValueError("Rasm yo'q")
    out = io.BytesIO()
    images[0].save(out, format="PDF", save_all=True, append_images=images[1:])
    return out.getvalue()


def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    """Bir nechta PDF faylni bitta PDF'ga birlashtiradi."""
    writer = PdfWriter()
    for b in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(b))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def make_qr(text: str) -> bytes:
    """Matn yoki havoladan QR-kod rasmi (PNG) yasaydi."""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


async def _fetch_latest_rates(client: httpx.AsyncClient) -> list:
    """CBU dan eng so'nggi e'lon qilingan kursni oladi (cbu.uz bosh sahifasi bilan bir xil).

    CBU kurslarni bir necha kun oldindan e'lon qiladi. Shu sababli bugundan
    bir necha kun keyingi sana bo'yicha so'rov yuboramiz — endpoint o'sha
    sanadan oldingi eng so'nggi mavjud kursni qaytaradi."""
    target = (date.today() + timedelta(days=7)).isoformat()
    url = f"https://cbu.uz/uz/arkhiv-kursov-valyut/json/all/{target}/"
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()
    if data:
        return data
    # Zaxira: oddiy (joriy) manzil
    resp = await client.get(CBU_URL)
    resp.raise_for_status()
    return resp.json()


async def get_rates(codes: list[str] | None = None) -> str:
    """Markaziy bank kurslarini matn ko'rinishida qaytaradi."""
    codes = codes or ["USD", "EUR", "RUB", "KZT"]
    async with httpx.AsyncClient(timeout=15) as client:
        data = await _fetch_latest_rates(client)
    by_code = {item["Ccy"]: item for item in data}
    lines = ["💱 *Markaziy bank rasmiy kursi*\n_(1 birlik = O'zbek so'mi)_\n"]
    for code in codes:
        item = by_code.get(code)
        if not item:
            continue
        rate = _fmt_som(item.get("Rate", "—"))
        diff = item.get("Diff") or "0"
        try:
            d = float(diff)
            arrow = "🔺" if d > 0 else ("🔻" if d < 0 else "▪️")
        except (ValueError, TypeError):
            arrow = "▪️"
        lines.append(f"{arrow} *{code}* — {rate} so'm  ({diff})")
    lines.append(f"\n📅 Sana: {data[0]['Date']}")
    lines.append("ℹ️ Bu — rasmiy kurs. Bank yoki shoxobchada narx biroz farq qilishi mumkin.")
    return "\n".join(lines)


def _fmt_som(rate_str: str) -> str:
    """Raqamni o'qishga qulay formatga keltiradi: 12014.48 -> '12 014'."""
    try:
        v = float(rate_str)
    except (ValueError, TypeError):
        return str(rate_str)
    if v >= 100:
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:.2f}"

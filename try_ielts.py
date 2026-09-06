"""Baholash sifatini Telegram'siz sinash.

    python try_ielts.py                 # ichki namuna insho (band ~6)
    python try_ielts.py essay.txt       # o'z faylingiz
    python try_ielts.py photo.jpg       # qo'lyozma rasmi

Nima uchun kerak: modelning qattiqqo'lligini botni ishga tushirmasdan
o'lchash. Agar bu namunaga 7.5+ bersa — model yumshoq, promptni
qattiqlashtirish kerak. Haqiqiy imtihonda bu insho 5.5-6.5 oladi.
"""
import asyncio
import os
import sys

from ielts import config, grader

# Haqiqiy nomzod darajasidagi namuna: fikri bor, lekin lug'at takrorlanadi,
# gap tuzilishi bir xil va bir nechta grammatik xato bor.
SAMPLE_QUESTION = (
    "Some people think that all university students should study whatever "
    "they like. Others believe that they should only be allowed to study "
    "subjects that will be useful in the future, such as those related to "
    "science and technology. Discuss both views and give your own opinion."
)

SAMPLE_ESSAY = """Nowadays, education is very important topic in our society. Some peoples \
think that students must study what they want, but other peoples think they \
should study only useful subjects like science. In this essay I will discuss \
both views and give my opinion.

On the one hand, students should study what they like. If a student like \
history or art, and he study it, he will be more happy and more motivated. \
When people do what they love, they work harder and they get better results. \
For example, my friend studied music because he love it, and now he is \
successful musician. Also, art and history are important for culture of \
country.

On the other hand, some people say that only science and technology is \
useful. They think that country need engineers and doctors, not artists. \
It is true that these jobs give more money and more job opportunities. \
Government spend a lot of money for universities, so it is logical that \
they want useful specialists. If everybody study art, who will build \
bridges and who will make medicine?

In my opinion, students must have freedom to choose. But government can \
give more scholarships for important subjects. In this way, students are \
free but also country get specialists which it need.

In conclusion, both views have strong arguments, but I think freedom of \
choice is more important, because motivated student is always better than \
unmotivated one."""


async def main():
    gaps = [g for g in config.missing() if g != "IELTS_BOT_TOKEN"]
    if gaps:
        print(f"❌ Yetishmayapti: {', '.join(gaps)} — .env ga yozing")
        return 1

    image = None
    essay = SAMPLE_ESSAY
    question = SAMPLE_QUESTION

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.exists(path):
            print(f"❌ Fayl topilmadi: {path}")
            return 1
        if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            image = open(path, "rb").read()
            essay, question = "", ""
            print(f"📸 Rasm: {path} ({len(image) // 1024} KB)")
        else:
            essay = open(path, encoding="utf-8").read()
            question = ""
            print(f"📄 Fayl: {path} ({grader.count_words(essay)} so'z)")
    else:
        print(f"📄 Namuna insho ({grader.count_words(essay)} so'z)")
        print("   Kutilgan baho: 5.5 - 6.5. Agar 7+ bersa model yumshoq.")

    print(f"🤖 Model: {config.GEMINI_MODEL}\n")

    import time
    t0 = time.time()
    try:
        r = await grader.grade("task2", question, essay, image, "uz")
    except Exception as e:
        print(f"❌ Xato: {e}")
        return 1
    took = time.time() - t0

    print(f"🎯 UMUMIY: {r['overall']}   ({took:.1f} soniya, {r['words']} so'z)\n")
    for c in r["criteria"]:
        print(f"  {c['key']:4} {c['band']:<4} {c['name']}")
        print(f"       {c['comment']}\n")

    if r["off_topic"]:
        print("❗ Mavzudan chetda\n")
    if r["memorised"]:
        print("❗ Yodlangan shablon\n")

    print(f"XULOSA: {r['summary']}\n")

    print(f"XATOLAR ({len(r['errors'])} ta):")
    for i, e in enumerate(r["errors"], 1):
        print(f"  {i}. ❌ {e['quote']}")
        print(f"     ✅ {e['fix']}")
        print(f"     ℹ️  {e['why']}")

    print(f"\nQADAMLAR ({len(r['upgrades'])} ta):")
    for i, u in enumerate(r["upgrades"], 1):
        print(f"  {i}. {u}")

    if r["improved"]["improved"]:
        print("\nQAYTA YOZILGAN XATBOSHI:")
        print(f"  Sizniki : {r['improved']['original'][:200]}")
        print(f"  Band 8  : {r['improved']['improved'][:400]}")

    if r["transcript"]:
        print(f"\nO'QILGAN MATN:\n{r['transcript'][:1200]}")

    # Sifat nazorati: xato iqtiboslari haqiqatan inshoda bormi?
    if essay:
        missing = [e["quote"] for e in r["errors"] if e["quote"] not in essay]
        if missing:
            print(f"\n⚠️ {len(missing)} ta iqtibos inshoda topilmadi "
                  f"(model o'zi to'qigan): {missing}")
        else:
            print("\n✅ Barcha iqtiboslar inshodan aynan olingan")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

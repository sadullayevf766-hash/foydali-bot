"""IELTS Writing inshosini baholovchi qatlam.

Asosiy yo'l — Google AI Studio (Gemini): bepul tarifi bor, karta so'ramaydi
va rasm (qo'lyozma) ni ham o'qiy oladi. Zaxira yo'l — OpenRouter bepul
modellari: Gemini biror mintaqada ishlamay qolsa mahsulot to'xtamasin.

Umumiy ball MODELDAN emas, SHU YERDA hisoblanadi: to'rt mezonning
o'rtachasi IELTS qoidasi bo'yicha yaxlitlanadi. Sabab — model o'rtachani
tez-tez noto'g'ri yaxlitlaydi, arifmetikani esa kodga ishonib bo'ladi.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re

import httpx

from . import config, db

log = logging.getLogger("ielts.grader")

# Prompt yoki baholash mantiqi o'zgarsa BU RAQAMNI OSHIRING — aks holda
# eski keshdagi natijalar yangi qoidalar bilan hisoblanganday ko'rinadi.
PROMPT_VERSION = "2026-09-06.3"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TASKS = {
    "task2": {
        "uz": "Task 2 (essay)",
        "en": "Task 2 (essay)",
        "min_words": 250,
        "brief": "Writing Task 2 — a discursive essay responding to a prompt.",
    },
    "task1_academic": {
        "uz": "Task 1 Academic (grafik/jadval)",
        "en": "Task 1 Academic (chart/table)",
        "min_words": 150,
        "brief": (
            "Writing Task 1 Academic — a factual summary of visual data "
            "(chart, graph, table, map or process)."
        ),
    },
    "task1_general": {
        "uz": "Task 1 General (xat)",
        "en": "Task 1 General (letter)",
        "min_words": 150,
        "brief": "Writing Task 1 General Training — a letter.",
    },
}

CRITERIA = {
    "task2": [
        ("TR", "Task Response"),
        ("CC", "Coherence & Cohesion"),
        ("LR", "Lexical Resource"),
        ("GRA", "Grammatical Range & Accuracy"),
    ],
    "task1": [
        ("TA", "Task Achievement"),
        ("CC", "Coherence & Cohesion"),
        ("LR", "Lexical Resource"),
        ("GRA", "Grammatical Range & Accuracy"),
    ],
}

SYSTEM = """You are a senior IELTS Writing examiner with 15 years of experience \
and full command of the official public band descriptors.

Grade the candidate's response against the four official criteria for the \
given task. Be STRICT and realistic. Real examiners are far harsher than \
untrained readers: the global mean for IELTS Writing is about 5.7, and most \
responses you see will fall between 5.0 and 6.5. Never inflate a score to be \
encouraging.

But use the FULL scale, per criterion, exactly as the descriptors say. Bands \
8 and 9 exist and must be awarded when they are earned. Do not cluster every \
strong response at 7.0-7.5 — that is as wrong as inflating a weak one:
- Band 8 for Lexical Resource means a wide resource used fluently and \
precisely, with only occasional slips in word choice or collocation.
- Band 9 means full flexibility and precision, with errors appearing only as \
rare slips.
- The same logic applies to Grammatical Range: band 8 is a wide range of \
structures with the majority of sentences error-free.
A response that is genuinely near-native in vocabulary and grammar must not \
be capped at 7.5 merely because it is not perfect. Judge each criterion \
independently — a weak Task score must not drag down the language criteria, \
and strong language must not lift a weak Task score.

Apply these rules:
- Under-length responses are penalised on the task criterion (Task Response / \
Task Achievement). Task 2 requires 250 words, Task 1 requires 150.
- Memorised or template language that does not fit the prompt lowers the score.
- An off-topic response cannot score above band 4 on the task criterion.
- Errors that impede communication weigh far more than minor slips.
- Judge range as well as accuracy: a response with no errors but only simple \
sentences cannot pass band 6 for Grammatical Range.

Quote errors EXACTLY as the candidate wrote them, word for word, so they can \
find them in their own text. Give at most 6 errors, chosen as the ones that \
cost the most marks.

Write every comment, explanation and suggestion in {feedback_language}. \
Keep the English quotations and corrections in English."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "transcript": {"type": "STRING"},
        "word_count": {"type": "INTEGER"},
        "off_topic": {"type": "BOOLEAN"},
        "memorised": {"type": "BOOLEAN"},
        "criteria": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "key": {"type": "STRING"},
                    "band": {"type": "NUMBER"},
                    "comment": {"type": "STRING"},
                },
                "required": ["key", "band", "comment"],
            },
        },
        "errors": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "quote": {"type": "STRING"},
                    "fix": {"type": "STRING"},
                    "why": {"type": "STRING"},
                },
                "required": ["quote", "fix", "why"],
            },
        },
        "upgrades": {"type": "ARRAY", "items": {"type": "STRING"}},
        "improved_paragraph": {
            "type": "OBJECT",
            "properties": {
                "original": {"type": "STRING"},
                "improved": {"type": "STRING"},
            },
            "required": ["original", "improved"],
        },
        "summary": {"type": "STRING"},
    },
    # `transcript` ham majburiy: aks holda model uni tashlab ketadi va
    # qo'lyozma yuborgan odam nima o'qilganini ko'ra olmaydi — bu esa
    # noto'g'ri o'qilgan so'zni aniqlashning yagona yo'li.
    "required": [
        "transcript", "word_count", "off_topic", "memorised", "criteria",
        "errors", "upgrades", "improved_paragraph", "summary",
    ],
}


class GraderError(Exception):
    """Baholash amalga oshmadi — foydalanuvchi kreditini yechmaymiz."""


def _cache_key(task: str, question: str, essay: str, images: list[bytes],
               question_images: list[bytes], lang: str) -> str:
    """Kirish ma'lumotlarining barmoq izi.

    Rasm baytlari ham hisobga olinadi: Telegram bir xil rasmni qayta
    yuborilganda ham bir xil baytlarni beradi, shuning uchun bir xil
    surat bir xil kalitga tushadi. Til ham kiradi — izohlar tilga
    bog'liq. Prompt versiyasi ham kiradi, aks holda prompt yaxshilangach
    eski (yomonroq) natijalar keshdan chiqib qolaverardi.
    """
    h = hashlib.sha256()
    h.update(PROMPT_VERSION.encode())
    for part in (task, lang, question.strip(), essay.strip()):
        h.update(b"\x00")
        h.update(part.encode("utf-8", "replace"))
    for group, blobs in (("q", question_images), ("a", images)):
        h.update(group.encode())
        for b in blobs:
            h.update(hashlib.sha256(b).digest())
    return h.hexdigest()


def count_words(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def round_band(x: float) -> float:
    """IELTS yaxlitlash: .25 -> .5 ga, .75 -> keyingi butunga ko'tariladi."""
    whole = int(x)
    frac = x - whole
    if frac < 0.25:
        return float(whole)
    if frac < 0.75:
        return whole + 0.5
    return float(whole + 1)


def _build_prompt(task: str, question: str, essay: str, lang: str,
                  n_images: int, n_task_images: int = 0) -> str:
    spec = TASKS[task]
    keys = CRITERIA["task2" if task == "task2" else "task1"]
    keys_line = ", ".join(f'"{k}" ({name})' for k, name in keys)

    if question.strip():
        q_block = question.strip()
    elif n_task_images:
        q_block = "(See the TASK IMAGE below — the question is in the picture.)"
    else:
        q_block = ("(The candidate did not provide the question. Judge the "
                   "response on its own terms and say in the summary that the "
                   "task criterion could not be assessed reliably without the "
                   "prompt.)")

    parts = [
        f"TASK TYPE: {spec['brief']}",
        f"REQUIRED LENGTH: at least {spec['min_words']} words.",
        "",
        "THE QUESTION THE CANDIDATE WAS ANSWERING:",
        q_block,
        "",
    ]
    if n_task_images:
        parts += [
            f"IMPORTANT: {n_task_images} image(s) below are labelled TASK "
            "IMAGE. Those are the QUESTION — a chart, table, map, diagram or "
            "printed prompt. They are NOT the candidate's answer. Never grade "
            "them, never transcribe them into `transcript`, and never quote "
            "them as the candidate's mistakes.",
            "Because you can see the visual, check the candidate's FACTS "
            "against it: every figure, trend, comparison and superlative they "
            "state must actually be true of the data shown. Invented numbers, "
            "wrong trends, or a missing overview are serious Task Achievement "
            "failures — say so explicitly and list any wrong figure among the "
            "errors, quoting the candidate's own words.",
            "",
        ]
    if n_images:
        pages = (
            "The candidate's response is the image labelled CANDIDATE RESPONSE "
            "(handwriting)."
            if n_images == 1 else
            f"The candidate's response is spread across the {n_images} images "
            "labelled CANDIDATE RESPONSE, which are consecutive PAGES of ONE "
            "single essay, in order. Join them into one continuous text — do "
            "not treat them as separate essays, and do not count the same "
            "sentence twice where a page break falls mid-sentence."
        )
        parts += [
            pages,
            "First transcribe it EXACTLY as written, preserving their spelling "
            "and grammar mistakes — do not silently correct anything. Put that "
            "transcription in the `transcript` field. Then grade the "
            "transcription.",
            "If the handwriting is unreadable, say so in `summary` and set all "
            "bands to 0.",
        ]
    else:
        parts += [
            "THE CANDIDATE'S RESPONSE:",
            "---",
            essay.strip(),
            "---",
            "Set `transcript` to an empty string.",
        ]
    parts += [
        "",
        f"Use exactly these four criterion keys, in this order: {keys_line}.",
        "Give each criterion a band from 0 to 9 in steps of 0.5, and a comment "
        "of two or three sentences that names the specific feature of THIS "
        "response that put it at that band.",
        "`upgrades` must contain exactly three concrete, actionable changes "
        "that would move this candidate up half a band — not generic advice.",
        "`improved_paragraph` must take one real paragraph from the response "
        "(copied verbatim into `original`) and rewrite it at band 8 level.",
        f"`summary` is one short paragraph in {lang_name(lang)}.",
    ]
    return "\n".join(parts)


def lang_name(lang: str) -> str:
    return "Uzbek (o'zbek tilida)" if lang == "uz" else "English"


def _mime(image: bytes) -> str:
    """Rasm turini boshidagi baytlardan aniqlaydi.

    Telegram suratlarni JPEG ga aylantiradi, lekin sinovda va kelajakda
    boshqa format kelishi mumkin — noto'g'ri mime bilan model rasmni
    umuman ko'rmaydi.
    """
    if image.startswith(b"\x89PNG"):
        return "image/png"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


# Vaqtinchalik nosozliklar: bularda qayta urinish MA'NOLI.
# 429 — kvota/tezlik chegarasi, 5xx — model band yoki serverda nosozlik.
RETRY_CODES = {429, 500, 502, 503, 504}
# Har urinish orasidagi kutish (soniya). Oxirgi urinishdan keyin kutilmaydi.
BACKOFF = [3, 8]


def _model_chain() -> list[str]:
    """Sinab ko'riladigan modellar: asosiysi, keyin zaxirasi.

    Bepul tarifda `gemini-2.5-flash` vaqti-vaqti bilan 503 beradi
    (2026-09-06 da amalda uchradi). Eskiroq va kamroq yuklangan model
    sifat jihatidan biroz pastroq, lekin foydalanuvchi uchun "xato"
    dan ancha yaxshi.
    """
    chain = [config.GEMINI_MODEL]
    for fallback in ("gemini-2.0-flash",):
        if fallback not in chain:
            chain.append(fallback)
    return chain


class _Transient(Exception):
    """Vaqtinchalik nosozlik — qayta urinsa o'tishi mumkin."""


async def _gemini_once(model: str, body: dict) -> dict:
    url = GEMINI_URL.format(model=model)
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            url, json=body, headers={"x-goog-api-key": config.GEMINI_API_KEY}
        )
    if r.status_code in RETRY_CODES:
        raise _Transient(f"Gemini {r.status_code} ({model})")
    if r.status_code != 200:
        # 400/403 kabi xatolar qayta urinishdan tuzalmaydi — darhol to'xtaymiz.
        raise GraderError(f"Gemini {r.status_code}: {r.text[:300]}")
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # Xavfsizlik filtri yoki bo'sh javob.
        raise GraderError(f"Gemini bo'sh javob qaytardi: {str(data)[:300]}")
    return _parse_json(text)


async def _call_gemini(prompt: str, system: str,
                       images: list[tuple[str, bytes]]) -> dict:
    user_parts: list[dict] = [{"text": prompt}]
    for label, img in images:
        # Har rasmdan OLDIN uning nomi yuboriladi. Aks holda model
        # topshiriq grafigi bilan javob varag'ini farqlay olmaydi va
        # grafikni insho deb baholab yuboradi.
        user_parts.append({"text": f"[{label}]"})
        user_parts.append({
            "inline_data": {
                "mime_type": _mime(img),
                "data": base64.b64encode(img).decode(),
            }
        })
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": user_parts}],
        "generationConfig": {
            # 0 — bir xil insho bir xil ball olishi uchun. 0.2 da ham
            # mezonlar 0.5 band tebranardi va bu foydalanuvchiga darhol
            # sezildi. `seed` tebranishni yanada kamaytiradi, lekin
            # Gemini to'liq determinizmni kafolatlamaydi — shuning uchun
            # asosiy kafolat quyidagi kesh.
            "temperature": 0,
            "seed": 42,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }

    last = None
    for model in _model_chain():
        for attempt in range(len(BACKOFF) + 1):
            try:
                return await _gemini_once(model, body)
            except _Transient as e:
                last = e
                log.warning("%s — qayta urinish %s", e, attempt + 1)
                if attempt < len(BACKOFF):
                    await asyncio.sleep(BACKOFF[attempt])
            except httpx.RequestError as e:
                # Tarmoq uzildi — bu ham vaqtinchalik.
                last = e
                log.warning("Tarmoq xatosi: %s", e)
                if attempt < len(BACKOFF):
                    await asyncio.sleep(BACKOFF[attempt])
        log.warning("%s modeli javob bermadi, zaxiraga o'tamiz", model)
    raise GraderError(f"Gemini javob bermadi: {last}")


async def _call_openrouter(prompt: str, system: str,
                           images: list[tuple[str, bytes]]) -> dict:
    content: list | str
    if images:
        content = [{"type": "text", "text": prompt}]
        for label, img in images:
            b64 = base64.b64encode(img).decode()
            content.append({"type": "text", "text": f"[{label}]"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{_mime(img)};base64,{b64}"},
            })
    else:
        content = prompt
    body = {
        "model": config.OPENROUTER_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system + "\n\nReply with JSON only."},
            {"role": "user", "content": content},
        ],
    }
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            OPENROUTER_URL,
            json=body,
            headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
        )
    if r.status_code != 200:
        raise GraderError(f"OpenRouter {r.status_code}: {r.text[:300]}")
    return _parse_json(r.json()["choices"][0]["message"]["content"])


def _parse_json(text: str) -> dict:
    """Modeldan kelgan matnni JSON ga aylantiradi.

    `responseMimeType` so'ralgan bo'lsa ham ba'zi modellar javobni ```json
    blokiga o'raydi — shuning uchun oldin tozalanadi.
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise GraderError(f"Javobni JSON sifatida o'qib bo'lmadi: {text[:200]}")


async def grade(
    task: str,
    question: str,
    essay: str = "",
    images: list[bytes] | None = None,
    lang: str = "uz",
    question_images: list[bytes] | None = None,
    force: bool = False,
) -> dict:
    """Inshoni baholaydi va tayyor natijani qaytaradi.

    `images` — bitta inshoning varaqlari (ketma-ketlikda). Qo'lda yozilgan
    250 so'zlik insho ko'pincha ikki varaqqa sig'adi, shuning uchun ular
    BITTA insho sifatida, bitta so'rovda baholanadi.

    `question_images` — TOPSHIRIQ rasmlari (Task 1 Academic grafigi,
    jadvali yoki xaritasi). Ular javob emas: modelga alohida nom bilan
    yuboriladi, aks holda grafikni insho deb baholaydi.

    Xato bo'lsa `GraderError` ko'taradi — chaqiruvchi shunda kredit
    yechmaydi.
    """
    images = images or []
    question_images = question_images or []

    key = _cache_key(task, question, essay, images, question_images, lang)
    if not force:
        hit = db.cache_get(key)
        if hit:
            try:
                cached = json.loads(hit)
                cached["cached"] = True
                return cached
            except json.JSONDecodeError:
                pass

    system = SYSTEM.format(feedback_language=lang_name(lang))
    prompt = _build_prompt(task, question, essay, lang,
                           len(images), len(question_images))

    labelled: list[tuple[str, bytes]] = []
    for i, img in enumerate(question_images, 1):
        labelled.append((f"TASK IMAGE {i} — this is the question, NOT the answer", img))
    for i, img in enumerate(images, 1):
        labelled.append((f"CANDIDATE RESPONSE, PAGE {i} of {len(images)}", img))

    errors: list[str] = []
    result = None
    if config.GEMINI_API_KEY:
        try:
            result = await _call_gemini(prompt, system, labelled)
        except Exception as e:
            errors.append(str(e))
            log.warning("Gemini ishlamadi: %s", e)
    if result is None and config.OPENROUTER_API_KEY:
        try:
            result = await _call_openrouter(prompt, system, labelled)
        except Exception as e:
            errors.append(str(e))
            log.warning("OpenRouter ishlamadi: %s", e)
    if result is None:
        raise GraderError(" | ".join(errors) or "Model sozlanmagan")

    has_question = bool(question.strip() or question_images)
    out = _normalise(result, task, essay, bool(images), has_question)
    db.cache_put(key, json.dumps(out, ensure_ascii=False))
    out["cached"] = False
    return out


def _normalise(raw: dict, task: str, essay: str, from_image: bool,
               has_question: bool = True) -> dict:
    """Model javobini ishonchli shaklga keltiradi.

    Model ba'zan mezonlarni chala qaytaradi yoki o'rtachani noto'g'ri
    yaxlitlaydi; umumiy ball shu yerda qaytadan hisoblanadi.

    `has_question=False` bo'lsa (savol matni ham, grafigi ham yo'q) —
    Task mezoni O'RTACHAGA QO'SHILMAYDI. Sabab: model bunday holda
    "tekshirib bo'lmadi" deb Task ballini pasaytiradi va foydalanuvchi
    YO'Q MA'LUMOT uchun jazolanadi. Amalda kuzatildi: band 9 darajasidagi
    Task 1 inshosi LR 8.0 va GRA 8.0 olgani holda, faqat diagramma
    yuborilmagani uchun umumiy 7.5 ga tushdi. Bunday holda ball "til
    bo'yicha" deb belgilanadi va foydalanuvchiga aytiladi.
    """
    wanted = CRITERIA["task2" if task == "task2" else "task1"]
    by_key = {}
    for item in raw.get("criteria") or []:
        key = str(item.get("key", "")).upper().strip()
        try:
            band = float(item.get("band"))
        except (TypeError, ValueError):
            continue
        by_key[key] = {
            "band": max(0.0, min(9.0, band)),
            "comment": (item.get("comment") or "").strip(),
        }

    criteria = []
    for key, name in wanted:
        got = by_key.get(key)
        if got is None:
            raise GraderError(f"Model '{key}' mezonini qaytarmadi")
        criteria.append({"key": key, "name": name, **got})

    # Task mezoni har doim birinchi (CRITERIA tartibi shunday).
    task_key = wanted[0][0]
    scored = criteria if has_question else [
        c for c in criteria if c["key"] != task_key
    ]
    overall = round_band(sum(c["band"] for c in scored) / len(scored))

    transcript = (raw.get("transcript") or "").strip()
    text = transcript if from_image else essay
    words = count_words(text) if text else int(raw.get("word_count") or 0)

    improved = raw.get("improved_paragraph") or {}
    return {
        "task": task,
        "overall": overall,
        "task_unassessed": not has_question,
        "task_key": task_key,
        "criteria": criteria,
        "words": words,
        "min_words": TASKS[task]["min_words"],
        "transcript": transcript,
        "off_topic": bool(raw.get("off_topic")),
        "memorised": bool(raw.get("memorised")),
        "errors": [
            {
                "quote": (e.get("quote") or "").strip(),
                "fix": (e.get("fix") or "").strip(),
                "why": (e.get("why") or "").strip(),
            }
            for e in (raw.get("errors") or [])[:6]
            if (e.get("quote") or "").strip()
        ],
        "upgrades": [u.strip() for u in (raw.get("upgrades") or [])[:3] if u.strip()],
        "improved": {
            "original": (improved.get("original") or "").strip(),
            "improved": (improved.get("improved") or "").strip(),
        },
        "summary": (raw.get("summary") or "").strip(),
    }

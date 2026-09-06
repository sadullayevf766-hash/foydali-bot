"""IELTS Writing inshosini baholovchi qatlam.

Asosiy yo'l — Google AI Studio (Gemini): bepul tarifi bor, karta so'ramaydi
va rasm (qo'lyozma) ni ham o'qiy oladi. Zaxira yo'l — OpenRouter bepul
modellari: Gemini biror mintaqada ishlamay qolsa mahsulot to'xtamasin.

Umumiy ball MODELDAN emas, SHU YERDA hisoblanadi: to'rt mezonning
o'rtachasi IELTS qoidasi bo'yicha yaxlitlanadi. Sabab — model o'rtachani
tez-tez noto'g'ri yaxlitlaydi, arifmetikani esa kodga ishonib bo'ladi.
"""
from __future__ import annotations

import base64
import json
import logging
import re

import httpx

from . import config

log = logging.getLogger("ielts.grader")

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
responses you see will fall between 5.0 and 6.5. Award 7.0+ only when the \
descriptors are genuinely met, and 8.0+ only for a response that is close to \
flawless. Never inflate a score to be encouraging.

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
    "required": [
        "word_count", "off_topic", "memorised", "criteria",
        "errors", "upgrades", "improved_paragraph", "summary",
    ],
}


class GraderError(Exception):
    """Baholash amalga oshmadi — foydalanuvchi kreditini yechmaymiz."""


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


def _build_prompt(task: str, question: str, essay: str, lang: str, is_image: bool) -> str:
    spec = TASKS[task]
    keys = CRITERIA["task2" if task == "task2" else "task1"]
    keys_line = ", ".join(f'"{k}" ({name})' for k, name in keys)
    parts = [
        f"TASK TYPE: {spec['brief']}",
        f"REQUIRED LENGTH: at least {spec['min_words']} words.",
        "",
        "THE QUESTION THE CANDIDATE WAS ANSWERING:",
        question.strip() or "(The candidate did not provide the question. "
        "Judge the response on its own terms and say in the summary that the "
        "task criterion could not be assessed reliably without the prompt.)",
        "",
    ]
    if is_image:
        parts += [
            "The candidate's response is in the attached image (handwriting).",
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
            "Leave `transcript` empty.",
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


async def _call_gemini(prompt: str, system: str, image: bytes | None) -> dict:
    user_parts: list[dict] = [{"text": prompt}]
    if image:
        user_parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image).decode(),
            }
        })
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": user_parts}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }
    url = GEMINI_URL.format(model=config.GEMINI_MODEL)
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            url, json=body, headers={"x-goog-api-key": config.GEMINI_API_KEY}
        )
    if r.status_code != 200:
        raise GraderError(f"Gemini {r.status_code}: {r.text[:300]}")
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # Xavfsizlik filtri yoki bo'sh javob.
        raise GraderError(f"Gemini bo'sh javob qaytardi: {str(data)[:300]}")
    return _parse_json(text)


async def _call_openrouter(prompt: str, system: str, image: bytes | None) -> dict:
    content: list | str
    if image:
        b64 = base64.b64encode(image).decode()
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]
    else:
        content = prompt
    body = {
        "model": config.OPENROUTER_MODEL,
        "temperature": 0.2,
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
    image: bytes | None = None,
    lang: str = "uz",
) -> dict:
    """Inshoni baholaydi va tayyor natijani qaytaradi.

    Xato bo'lsa `GraderError` ko'taradi — chaqiruvchi shunda kredit
    yechmaydi.
    """
    system = SYSTEM.format(feedback_language=lang_name(lang))
    prompt = _build_prompt(task, question, essay, lang, image is not None)

    errors: list[str] = []
    result = None
    if config.GEMINI_API_KEY:
        try:
            result = await _call_gemini(prompt, system, image)
        except Exception as e:
            errors.append(str(e))
            log.warning("Gemini ishlamadi: %s", e)
    if result is None and config.OPENROUTER_API_KEY:
        try:
            result = await _call_openrouter(prompt, system, image)
        except Exception as e:
            errors.append(str(e))
            log.warning("OpenRouter ishlamadi: %s", e)
    if result is None:
        raise GraderError(" | ".join(errors) or "Model sozlanmagan")

    return _normalise(result, task, essay, image is not None)


def _normalise(raw: dict, task: str, essay: str, from_image: bool) -> dict:
    """Model javobini ishonchli shaklga keltiradi.

    Model ba'zan mezonlarni chala qaytaradi yoki o'rtachani noto'g'ri
    yaxlitlaydi; umumiy ball shu yerda qaytadan hisoblanadi.
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

    overall = round_band(sum(c["band"] for c in criteria) / len(criteria))

    transcript = (raw.get("transcript") or "").strip()
    text = transcript if from_image else essay
    words = count_words(text) if text else int(raw.get("word_count") or 0)

    improved = raw.get("improved_paragraph") or {}
    return {
        "task": task,
        "overall": overall,
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

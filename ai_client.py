import json
import logging
from pathlib import Path

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

_FALLBACK_CANDIDATE = (
    "Junior/Middle C# Backend разработчик, 1 год опыта. "
    "Стек: .NET, C#, PostgreSQL, Redis, Entity Framework Core, Docker, "
    "GitHub Actions, Clean Architecture, CQRS."
)

_MODEL_NAME = "gemini-1.5-flash"

_resume_text: str | None = None
_model: genai.GenerativeModel | None = None


def load_resume(path: str | Path) -> None:
    """Read resume.txt into module state. Call once on startup."""
    global _resume_text
    p = Path(path)
    if not p.is_file():
        logger.warning(
            "Файл резюме не найден или не является файлом: %s — "
            "используется краткое описание кандидата по умолчанию.",
            p,
        )
        _resume_text = None
        return
    try:
        text = p.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.error("Не удалось прочитать резюме %s: %s — fallback на краткое описание.", p, exc)
        _resume_text = None
        return
    if not text:
        logger.warning("Файл резюме %s пустой — fallback на краткое описание.", p)
        _resume_text = None
        return
    _resume_text = text
    logger.info("Резюме загружено из %s (%d символов)", p, len(text))


def _get_model() -> genai.GenerativeModel:
    """Lazy-initialise the Gemini client on first use."""
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(_MODEL_NAME)
        logger.info("Gemini-клиент инициализирован (%s)", _MODEL_NAME)
    return _model


def _build_prompt(title: str, company: str, description: str) -> str:
    if _resume_text:
        candidate_section = f"Резюме кандидата:\n{_resume_text}"
    else:
        candidate_section = f"Кандидат: {_FALLBACK_CANDIDATE}"

    desc = description[:3000] if description else "не указано"

    return f"""Ты помогаешь писать сопроводительные письма для отклика на вакансии.

{candidate_section}

Вакансия: {title}
Компания: {company}
Описание: {desc}

Задачи:
1. Оцени соответствие вакансии кандидату по шкале 1-10 и дай краткое обоснование (1-2 предложения), ссылаясь на конкретные пункты резюме.
2. Напиши персонализированное сопроводительное письмо на русском языке (150–250 слов), которое подчёркивает релевантный опыт кандидата.

Отвечай строго в формате JSON без markdown блоков:
{{
  "score": <целое число 1-10>,
  "reasoning": "<краткое обоснование>",
  "cover_letter": "<текст сопроводительного письма>"
}}"""


_FALLBACK = {
    "fit_score": 5,
    "fit_reasoning": "Автоматическая оценка недоступна.",
    "cover_letter": (
        "Здравствуйте!\n\n"
        "Меня заинтересовала данная вакансия. Готов рассказать подробнее "
        "о своём опыте и навыках на собеседовании.\n\n"
        "С уважением."
    ),
}


def _strip_fences(raw: str) -> str:
    """Drop ```json ... ``` wrapping if Gemini ignored the no-markdown rule."""
    s = raw.strip()
    if not s.startswith("```"):
        return s
    nl = s.find("\n")
    if nl == -1:
        return s
    s = s[nl + 1:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


async def analyze_vacancy(title: str, company: str, description: str) -> dict:
    prompt = _build_prompt(title, company, description)
    try:
        model = _get_model()
        response = await model.generate_content_async(prompt)
        cleaned = _strip_fences(response.text)
        parsed = json.loads(cleaned)
        return {
            "fit_score":     max(1, min(10, int(parsed.get("score", 5)))),
            "fit_reasoning": str(parsed.get("reasoning", _FALLBACK["fit_reasoning"])),
            "cover_letter":  str(parsed.get("cover_letter", _FALLBACK["cover_letter"])),
        }
    except json.JSONDecodeError as exc:
        logger.error("Не удалось распарсить ответ Gemini: %s", exc)
    except Exception as exc:
        logger.exception("Ошибка при вызове Gemini: %s", exc)
    return _FALLBACK.copy()

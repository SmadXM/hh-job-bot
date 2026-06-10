import json
import logging
from pathlib import Path
from typing import Optional

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_FALLBACK_CANDIDATE = (
    "Junior/Middle C# Backend разработчик, 1 год опыта. "
    "Стек: .NET, C#, PostgreSQL, Redis, Entity Framework Core, Docker, "
    "GitHub Actions, Clean Architecture, CQRS."
)

_resume_text: Optional[str] = None


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


def _build_system_prompt() -> str:
    if _resume_text:
        candidate_block = f"Полное резюме кандидата:\n\n{_resume_text}"
    else:
        candidate_block = f"Кандидат: {_FALLBACK_CANDIDATE}"

    return f"""Ты — карьерный помощник.

{candidate_block}

Получив описание вакансии, ты должен:
1. Оценить соответствие вакансии профилю кандидата (от 1 до 10), опираясь на конкретные пункты резюме.
2. Написать персонализированное сопроводительное письмо на русском языке (150–250 слов), которое подчёркивает релевантный опыт кандидата из резюме.

Отвечай СТРОГО в формате JSON без каких-либо других символов:
{{
  "fit_score": <целое число 1-10>,
  "fit_reasoning": "<1-2 предложения с обоснованием оценки, ссылающиеся на конкретные навыки/опыт из резюме>",
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


async def analyze_vacancy(title: str, company: str, description: str) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_msg = (
        f"Вакансия: {title}\n"
        f"Компания: {company}\n\n"
        f"Описание:\n{description[:3000]}"
    )
    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["fit_score"] = max(1, min(10, int(result.get("fit_score", 5))))
        return result
    except json.JSONDecodeError as exc:
        logger.error("Не удалось распарсить ответ Claude: %s", exc)
    except anthropic.APIError as exc:
        logger.error("Ошибка Anthropic API: %s", exc)
    except Exception as exc:
        logger.exception("Неожиданная ошибка при вызове Claude: %s", exc)
    return _FALLBACK.copy()

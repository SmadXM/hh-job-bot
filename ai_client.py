import json
import logging

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_CANDIDATE = (
    "Junior/Middle C# Backend разработчик, 1 год опыта. "
    "Стек: .NET, C#, PostgreSQL, Redis, Entity Framework Core, Docker, "
    "GitHub Actions, Clean Architecture, CQRS."
)

_SYSTEM = f"""Ты — карьерный помощник. Кандидат: {_CANDIDATE}

Получив описание вакансии, ты должен:
1. Оценить соответствие вакансии профилю кандидата (от 1 до 10).
2. Написать персонализированное сопроводительное письмо на русском языке (150–250 слов).

Отвечай СТРОГО в формате JSON без каких-либо других символов:
{{
  "fit_score": <целое число 1-10>,
  "fit_reasoning": "<1-2 предложения с обоснованием оценки>",
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
            system=_SYSTEM,
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

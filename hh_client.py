import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

_API_BASE = "https://api.hh.ru"
# hh.ru requires a meaningful User-Agent even on public endpoints
_USER_AGENT = "HHJobBot/2.0 (public-monitor)"


class HHClient:
    """Read-only client for the public hh.ru API.

    Since 2025-12-15, hh.ru has removed all job-seeker OAuth endpoints, so this
    client only performs unauthenticated GETs against /vacancies and
    /vacancies/{id}. No tokens, no applications.
    """

    def __init__(self) -> None:
        self._headers = {"User-Agent": _USER_AGENT}

    async def _get(self, path: str, **params) -> Optional[dict]:
        url = f"{_API_BASE}{path}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=self._headers, params=params)
        except httpx.HTTPError as exc:
            logger.error("HTTP-ошибка при GET %s: %s", path, exc)
            return None
        if resp.status_code != 200:
            logger.error("GET %s вернул %s: %s", path, resp.status_code, resp.text[:300])
            return None
        return resp.json()

    async def search_vacancies(self, page: int = 0) -> list[dict]:
        data = await self._get(
            "/vacancies",
            text=settings.search_query,
            area=settings.search_city_id,
            salary=settings.search_salary_from,
            schedule=settings.search_schedule,
            only_with_salary="false",
            per_page=20,
            page=page,
            order_by="publication_time",
        )
        if data is None:
            return []
        return data.get("items", [])

    async def get_vacancy_details(self, vacancy_id: str) -> Optional[dict]:
        return await self._get(f"/vacancies/{vacancy_id}")


hh_client = HHClient()

import logging
from typing import Optional

import httpx

from config import settings
from database import get_tokens, save_tokens

logger = logging.getLogger(__name__)

_API_BASE = "https://api.hh.ru"
_TOKEN_URL = "https://hh.ru/oauth/token"
_USER_AGENT = "HHJobBot/1.0"


class HHClient:
    def __init__(self) -> None:
        self._access_token = settings.hh_access_token
        self._refresh_token = settings.hh_refresh_token
        self._resume_id: Optional[str] = None

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": _USER_AGENT,
        }

    def update_tokens(self, access_token: str, refresh_token: str) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def _refresh_tokens(self) -> bool:
        logger.info("Обновление токенов hh.ru...")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id":     settings.hh_client_id,
                    "client_secret": settings.hh_client_secret,
                },
            )
        if resp.status_code != 200:
            logger.error("Не удалось обновить токены: %s %s", resp.status_code, resp.text)
            return False
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        await save_tokens(settings.db_path, self._access_token, self._refresh_token)
        logger.info("Токены обновлены и сохранены в БД")
        return True

    async def _get(self, path: str, **params) -> Optional[dict]:
        url = f"{_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers, params=params)
            if resp.status_code == 401:
                logger.warning("Получен 401 для GET %s — пробуем обновить токены", path)
                if await self._refresh_tokens():
                    resp = await client.get(url, headers=self._headers, params=params)
        if resp.status_code != 200:
            logger.error("GET %s вернул %s: %s", path, resp.status_code, resp.text[:300])
            return None
        return resp.json()

    async def _post(self, path: str, data: dict) -> tuple[bool, dict]:
        url = f"{_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._headers, data=data)
            if resp.status_code == 401:
                logger.warning("Получен 401 для POST %s — пробуем обновить токены", path)
                if await self._refresh_tokens():
                    resp = await client.post(url, headers=self._headers, data=data)
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass
        ok = resp.status_code in (200, 201)
        if not ok:
            logger.error("POST %s вернул %s: %s", path, resp.status_code, resp.text[:300])
        return ok, body

    async def get_resume_id(self) -> Optional[str]:
        if self._resume_id:
            return self._resume_id
        data = await self._get("/resumes/mine")
        if not data:
            return None
        items = data.get("items", [])
        if not items:
            logger.error("На hh.ru нет ни одного резюме")
            return None
        self._resume_id = items[0]["id"]
        logger.info("Используется резюме: %s (%s)", items[0].get("title", ""), self._resume_id)
        return self._resume_id

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

    async def apply_to_vacancy(self, vacancy_id: str, cover_letter: str) -> bool:
        resume_id = await self.get_resume_id()
        if not resume_id:
            logger.error("Нет резюме — не могу подать отклик на %s", vacancy_id)
            return False
        ok, body = await self._post(
            "/negotiations",
            data={
                "vacancy_id": vacancy_id,
                "resume_id":  resume_id,
                "message":    cover_letter,
            },
        )
        if ok:
            logger.info("Отклик на вакансию %s отправлен", vacancy_id)
        return ok


hh_client = HHClient()

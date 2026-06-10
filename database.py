import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_VACANCIES = """
CREATE TABLE IF NOT EXISTS vacancies (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id          TEXT    UNIQUE NOT NULL,
    title               TEXT    NOT NULL,
    company             TEXT    NOT NULL,
    salary_from         INTEGER,
    salary_to           INTEGER,
    currency            TEXT,
    city                TEXT,
    schedule            TEXT,
    url                 TEXT,
    fit_score           INTEGER,
    fit_reasoning       TEXT,
    cover_letter        TEXT,
    status              TEXT    NOT NULL DEFAULT 'pending',
    telegram_message_id INTEGER,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at          TIMESTAMP
)
"""

_CREATE_TOKENS = """
CREATE TABLE IF NOT EXISTS tokens (
    id            INTEGER PRIMARY KEY,
    access_token  TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_VACANCIES)
        await db.execute(_CREATE_TOKENS)
        await db.commit()
    logger.info("База данных инициализирована: %s", db_path)


async def is_vacancy_seen(db_path: str, vacancy_id: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "SELECT 1 FROM vacancies WHERE vacancy_id = ?", (vacancy_id,)
        )
        return await cur.fetchone() is not None


async def save_vacancy(
    db_path: str,
    *,
    vacancy_id: str,
    title: str,
    company: str,
    salary_from: Optional[int],
    salary_to: Optional[int],
    currency: Optional[str],
    city: str,
    schedule: str,
    url: str,
    fit_score: int,
    fit_reasoning: str,
    cover_letter: str,
    telegram_message_id: Optional[int] = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO vacancies
                (vacancy_id, title, company, salary_from, salary_to, currency,
                 city, schedule, url, fit_score, fit_reasoning, cover_letter,
                 telegram_message_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                vacancy_id, title, company, salary_from, salary_to, currency,
                city, schedule, url, fit_score, fit_reasoning, cover_letter,
                telegram_message_id,
            ),
        )
        await db.commit()


async def update_vacancy_status(db_path: str, vacancy_id: str, status: str) -> None:
    applied_at = (
        datetime.now(timezone.utc).isoformat() if status == "applied" else None
    )
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE vacancies SET status = ?, applied_at = ? WHERE vacancy_id = ?",
            (status, applied_at, vacancy_id),
        )
        await db.commit()


async def update_cover_letter(db_path: str, vacancy_id: str, cover_letter: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE vacancies SET cover_letter = ? WHERE vacancy_id = ?",
            (cover_letter, vacancy_id),
        )
        await db.commit()


async def get_vacancy(db_path: str, vacancy_id: str) -> Optional[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM vacancies WHERE vacancy_id = ?", (vacancy_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_stats_today(db_path: str) -> dict:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) AS applied,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) AS skipped
            FROM vacancies
            WHERE DATE(created_at) = DATE('now')
            """
        )
        row = await cur.fetchone()
        return {
            "total":   row[0] or 0,
            "applied": row[1] or 0,
            "pending": row[2] or 0,
            "skipped": row[3] or 0,
        }


async def save_tokens(db_path: str, access_token: str, refresh_token: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO tokens (id, access_token, refresh_token, updated_at)
            VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                access_token  = excluded.access_token,
                refresh_token = excluded.refresh_token,
                updated_at    = excluded.updated_at
            """,
            (access_token, refresh_token),
        )
        await db.commit()


async def get_tokens(db_path: str) -> Optional[tuple[str, str]]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "SELECT access_token, refresh_token FROM tokens WHERE id = 1"
        )
        row = await cur.fetchone()
        return (row[0], row[1]) if row else None

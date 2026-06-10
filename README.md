# HH.ru Job Bot

Telegram bot that monitors fresh C# developer vacancies on hh.ru, rates each with Google Gemini, and generates a ready-to-copy Russian cover letter.

> **Note (2025-12-15):** hh.ru shut down the job-seeker OAuth API. Automatic submission of applications is no longer possible. This bot now uses **only the public, no-auth `GET /vacancies` endpoint** and acts as a curated feed with AI-generated cover letters you can paste manually on the site.

## Features

- Periodic vacancy search via APScheduler (configurable interval)
- Duplicate detection — each vacancy is sent only once
- Gemini (`gemini-1.5-flash`, free tier) rates each vacancy (1–10) and drafts a cover letter tailored to your profile
- Inline buttons: 👍 **Интересно** / 👎 **Не подходит** — saved to SQLite, no external calls
- `/interesting` command lists everything you bookmarked
- SQLite persistence in a Docker named volume

## Stack

Python 3.12 · aiogram 3 · httpx · google-generativeai · APScheduler · aiosqlite · pydantic-settings

---

## Setup

### 1. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Copy the token — this is your `TELEGRAM_BOT_TOKEN`.

### 2. Find your Telegram Chat ID

Start a conversation with your new bot, then open:

```
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```

Send any message to the bot and refresh the URL. Look for `"chat": {"id": 123456789}` — that number is your `TELEGRAM_CHAT_ID`.

Alternatively, forward a message to [@userinfobot](https://t.me/userinfobot).

### 3. Get a Gemini API key

Create a key at <https://aistudio.google.com/app/apikey> and copy it. The free tier is more than enough for this bot's request volume.

### 4. Create `resume.txt`

Drop your full CV into a plain-text file named `resume.txt` in the project root. The whole content is inlined into the prompt of every fit-score and cover-letter call, so Gemini can reason about your actual experience instead of a stub.

```bash
# Recommended format: free-form plain text, Russian or English
nano resume.txt
```

Add it to `.gitignore` if you plan to push the repo — it contains personal data.

If `resume.txt` is missing, the bot still runs but falls back to a hard-coded one-line candidate description (logged at warning level).

### 5. Configure .env

```bash
cp .env.example .env
# Fill in the three required values + tune search filters
```

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal chat ID |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `SEARCH_INTERVAL_HOURS` | How often to search (default: `3`) |
| `SEARCH_QUERY` | Search text (default: `C# developer`) |
| `SEARCH_CITY_ID` | hh.ru area ID (default: `1202` = Novosibirsk) |
| `SEARCH_SALARY_FROM` | Minimum salary filter (default: `80000`) |
| `SEARCH_SCHEDULE` | `remote` / `fullDay` / `shift` / `flexible` (default: `remote`) |

Common hh.ru area IDs: `1` Moscow · `2` Saint-Petersburg · `1202` Novosibirsk · `88` Yekaterinburg.

---

## Running

`resume.txt` is mounted into the container read-only at `/app/resume.txt`, so you can edit it on the host and restart the container without rebuilding.

```bash
docker compose up -d --build      # build and start
docker compose logs -f            # tail logs
docker compose down               # stop
```

The bot runs the first vacancy search immediately on startup, then repeats every `SEARCH_INTERVAL_HOURS`.

---

## Bot commands

| Command | Description |
|---|---|
| `/start` | Welcome message and help |
| `/status` | Vacancies found / interesting / pending / skipped today |
| `/interesting` | List up to 20 vacancies you marked 👍 |
| `/filters` | Current search filters |
| `/pause` | Pause the scheduler |
| `/resume` | Resume the scheduler |

---

## Vacancy card format

```
🏢 Company Name
💼 Job Title  (clickable link)
💰 от 100,000 ₽
📍 Новосибирск  ·  Удалённая работа

🟢 Оценка: 8/10
Вакансия хорошо совпадает со стеком .NET/C#…

📝 Сопроводительное письмо (для копирования):
> Здравствуйте! Меня заинтересовала позиция…

[ 👍 Интересно ] [ 👎 Не подходит ]
```

Tap **👍 Интересно** to bookmark; the vacancy then shows up in `/interesting`. The cover letter is shown in an expandable quote so it's easy to long-press → copy on mobile.

---

## Data

SQLite database is stored in a Docker named volume (`bot_data`) at `/data/bot.db`. To back it up:

```bash
docker run --rm -v hh-job-bot_bot_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/bot_data_backup.tar.gz /data
```

# HH.ru Job Bot

Telegram bot that automatically searches for C# developer vacancies on hh.ru, rates each one with Claude AI, and generates a personalized Russian cover letter for instant applications.

## Features

- Periodic vacancy search via APScheduler (configurable interval)
- Duplicate detection — each vacancy is sent only once
- Claude AI rates each vacancy (1–10) and writes a cover letter tailored to your profile
- Inline buttons: **Apply**, **Skip**, **Edit cover letter**
- One-click application via hh.ru API
- Token auto-refresh — no manual token renewal needed
- SQLite persistence in a Docker named volume

## Stack

Python 3.12 · aiogram 3 · httpx · anthropic SDK · APScheduler · aiosqlite · pydantic-settings

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

### 3. Register an hh.ru application

1. Go to <https://dev.hh.ru/admin> and create a new application.
2. Set **Redirect URI** to `https://localhost` (or any URL you control).
3. Copy `Client ID` and `Client Secret`.

### 4. Obtain OAuth tokens

**Step A — get an authorization code**

Open this URL in your browser (replace values):

```
https://hh.ru/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost
```

Log in with your hh.ru account and allow access. You will be redirected to a URL like:

```
https://localhost/?code=AUTHORIZATION_CODE
```

Copy the `code` value.

**Step B — exchange for tokens**

```bash
curl -X POST https://hh.ru/oauth/token \
  -d "grant_type=authorization_code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=https://localhost"
```

The response contains `access_token` and `refresh_token`. The bot will automatically refresh them when they expire and store fresh values in SQLite.

### 5. Get an Anthropic API key

Create a key at <https://console.anthropic.com/settings/keys> and copy it.

### 6. Configure .env

```bash
cp .env.example .env
# Fill in all values
```

Key settings:

| Variable | Description |
|---|---|
| `HH_CLIENT_ID` | hh.ru app client ID |
| `HH_CLIENT_SECRET` | hh.ru app client secret |
| `HH_ACCESS_TOKEN` | Initial access token (step 4B) |
| `HH_REFRESH_TOKEN` | Initial refresh token (step 4B) |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal chat ID |
| `ANTHROPIC_API_KEY` | Claude API key |
| `SEARCH_INTERVAL_HOURS` | How often to search (default: `3`) |
| `SEARCH_QUERY` | Search text (default: `C# developer`) |
| `SEARCH_CITY_ID` | hh.ru area ID (default: `1202` = Novosibirsk) |
| `SEARCH_SALARY_FROM` | Minimum salary filter (default: `80000`) |
| `SEARCH_SCHEDULE` | `remote` / `fullDay` / `hybrid` (default: `remote`) |

Common hh.ru area IDs: `1` Moscow · `2` Saint-Petersburg · `1202` Novosibirsk · `88` Yekaterinburg.

---

## Running

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

The bot runs the first vacancy search immediately on startup, then repeats every `SEARCH_INTERVAL_HOURS`.

---

## Bot commands

| Command | Description |
|---|---|
| `/start` | Welcome message and help |
| `/status` | Vacancies found / applied / pending today |
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

📝 Сопроводительное письмо:
Здравствуйте! Меня заинтересовала позиция…

[ ✅ Откликнуться ] [ ❌ Пропустить ]
[    ✏️ Редактировать письмо          ]
```

Pressing **✏️ Редактировать письмо** starts an inline edit flow: the bot asks for your text, shows a preview with a confirm button, then submits the application.

---

## Data

SQLite database is stored in a Docker named volume (`bot_data`) at `/data/bot.db`. To back it up:

```bash
docker run --rm -v hh-job-bot_bot_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/bot_data_backup.tar.gz /data
```

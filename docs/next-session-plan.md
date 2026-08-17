# Novel CRM — Next Session Plan

> Updated: 2026-05-29
> Goal: Telegram bot, bulk actions, client timezone

## Current State

### Fully implemented ✅
- **Auth**: JWT access+refresh, login, register (admin via API), roles (admin/lead/manager)
- **Companies API**: CRUD, search (text + fuzzy name match), filters (region/status/assigned/activity/org_form), pagination, sorting (multi-column), soft delete, call logging, comments
- **Excel import**: Upload xlsx, auto-mapping, preview, background import, templates, dedup by INN + fuzzy match
- **Company table**: Virtualized (TanStack), search, filters, sort, inline status `<select>` (admin/lead), inline manager assign `<select>`, localStorage persistence for filters
- **Company card**: Slide-in right panel, inline field editing (click to edit, debounced save), call log form, comments with call log, meeting section, calendar booking button
- **Dashboard**: Basic metrics cards (tasks today, overdue, calls today, unprocessed, archived, total)
- **Calendar/Meetings**: Availability slots per user (admin/lead set schedule), week calendar grid, booking meetings, meeting notes, cancel meeting, `CalendarModal`, `CalendarPicker`
- **Statuses**: 8 statuses (new, not_reached, no_answer, callback, in_progress, interested, meeting, refused) with colored badges
- **Bulk actions**: Checkbox selection, bulk status change, CSV export ✅
- **Telegram bot**: TgToken model, `/auth/tg-link`, `/auth/tg-bind`, `/auth/tg-unbind`, webhook handlers (`/tasks`, `/stats`, `/unbind`, token-based `/start`), `ProfileModal` with bind/unbind UI, `TG_BOT_USERNAME` env var ✅
- **Scheduler**: APScheduler, morning brief (9:00 MSK), evening summary (18:00 MSK), meeting reminders (every 15 min), stale check (3-day interested), trigger notifications on assign & meeting status ✅
- **Company card fixes**: Status buttons no longer auto-save calls, all LPR fields always visible for editing ✅
- **Client timezone**: Region→UTC mapping, display in CompanyCard with working/border/off indicator ✅
- **Deploy**: Docker Compose, FastAPI serves static frontend, nginx on host, SSL via Let's Encrypt, port 3020

### Known issues
- **Telegram bot on polling**: Webhook blocked by Russian firewall → switched to `Bot.get_updates()` polling in background task. Works from VPS (outbound), but `docker logs` doesn't show polling logs — logger has no handler; needs `logging.basicConfig` or uvicorn logger integration
- **Telegram bot on webhook** (`/api/telegram/webhook` endpoint kept as fallback): `{"detail":"'date'"}` error — webhook endpoint receives requests but Telegram's `Connection timed out` means Telegram servers can't reach the VPS

### Partially implemented 🔶
- **Dashboard**: Only basic `/dashboard/me` metrics. No funnel, team dashboard, stale contacts, quick presets

### Not implemented ❌
- User management UI (not needed — only for current team)
- Manual company creation form
- Audit log frontend
- Mobile view (< 768px)

---

## ✅ Completed

### Bugfixes
- **Status buttons no longer auto-save calls**: clicking a status only sets `selectedStatus`; call is logged only on "Сохранить звонок"
- **All LPR fields always visible**: removed conditional rendering of "Руководство / ЛПР" section and individual fields; now all fields show (with `—` for empty), clickable for inline editing

### Step 1: Telegram Bot — Model & Bind Flow ✅
- `TgToken` model in `backend/app/models.py`
- `POST /api/auth/tg-link` (generates token, returns `t.me/bot?start={token}`)
- `POST /api/auth/tg-bind` (validates token, binds user, sends welcome)
- `POST /api/auth/tg-unbind` (clears tg data)
- Webhook handlers: `/tasks` (DB query), `/stats` (call stats), `/unbind`, `/start` with token arg
- `ProfileModal.tsx` — settings button in header, bind/unbind Telegram
- `TG_BOT_USERNAME` env var (default: `novelsales_bot`)

### Step 2: Scheduler for Briefs & Reminders ✅
- APScheduler in `backend/app/scheduler.py`, started on FastAPI startup
- Morning brief (6:00 UTC = 9:00 MSK): tasks today, yesterday's calls per manager + team summary
- Evening summary (15:00 UTC = 18:00 MSK): calls today with status breakdown per manager + team
- Meeting reminders (every 15 min): at meeting hour and hour+1
- Stale check (5:00 UTC): companies `interested` + 3d+ no activity → notify manager
- Trigger notifications: on assign (to manager) and on status → "meeting" (to admin/lead)

### Step 3: Bulk Actions ✅ (was already done)
- Checkbox column, selection toolbar, bulk status change, CSV export

### Step 4: Client Timezone ✅
- `frontend/src/utils/timezone.ts` — 40+ Russian regions mapped to UTC offsets
- `TimeZoneBlock` component in `CompanyCard.tsx` — shows `UTC+X · HH:MM (working/border/off)` with color indicator

### Step 5: Webhook → Polling Migration ✅
- Telegram webhook blocked: Telegram servers can't connect to VPS in Russia (`Connection timed out`)
- Rewrote `telegram_webhook.py`: removed `Application`/`Updater` from `python-telegram-bot`, replaced with direct `Bot.get_updates()` in `asyncio.create_task` background task
- `start_polling()` / `stop_polling()` in `main.py` startup/shutdown
- Command handlers kept as plain async functions, dispatched via `_handlers` dict
- `/api/telegram/webhook` kept as fallback
- Webhook deleted via `bot.delete_webhook(drop_pending_updates=True)` on startup

---

## Deployment

After all changes:
```bash
ssh novel-server
cd /opt/novel-crm
git pull
cd frontend && npm install && npm run build
cd ..
docker compose build --no-cache backend
docker compose up -d
```

---

## Files Changed

| File | What |
|------|------|
| `backend/app/models.py` | +TgToken model |
| `backend/app/routers/auth.py` | +tg-link, tg-bind, tg-unbind |
| `backend/app/telegram_webhook.py` | +/tasks, /stats, /unbind, token /start; then switched webhook→polling, removed Application/Updater |
| `backend/app/scheduler.py` | New: APScheduler, briefs, reminders, stale check |
| `backend/app/main.py` | +scheduler init on startup; +start_polling/stop_polling |
| `backend/app/routers/companies.py` | +notifications on assign & meeting status |
| `backend/app/schemas.py` | +tg fields in UserResponse |
| `backend/requirements.txt` | +apscheduler |
| `frontend/src/components/ProfileModal.tsx` | New: Telegram bind/unbind UI |
| `frontend/src/pages/Dashboard.tsx` | +"Настройки" button |
| `frontend/src/components/CompanyCard.tsx` | Fix: status buttons, LPR fields; +TimeZoneBlock |
| `frontend/src/utils/timezone.ts` | New: region to UTC mapping |

---

## 2026-08-17 — AI Search: ZVENO `perplexity/sonar-pro-search` (Tavily removed)

### Почему
- **Tavily API** отклоняет запросы из РФ: `403 Forbidden` (ключ валиден, блокировка по гео). Проверено напрямую.
- **DuckDuckGo** (`duckduckgo-search==8.1.1`) перестал работать: `DDGS().text()` устарел, таймаут на bing.com.
- Результат: AI-поиск возвращал мусор (`sources: 0`, skyscanner и т.п.).

### Что сделано
- **`backend/app/ai_search.py`** — переписан конвейер:
  - Удалены `_search_tavily`, `_search_duckduckgo`.
  - Добавлен `_search_zveno_perplexity(query)` → POST `{zveno_base_url}/chat/completions` с `model="perplexity/sonar-pro-search"` (константа `SONAR_MODEL`), timeout 90s.
  - `search_company_info`: sonar возвращает `answer` (JSON) + `annotations[].url_citation` → `sources` (наконец-то наполняется: 8 источников/компания).
  - Устойчивость: `_parse_json` (срез кода-обёртки и `{...}`), фолбэк-цепочка sonar→GPT (`_extract_with_gpt`, модель `settings.llm_model`=`openai/gpt-4o-mini`)→regex→scraping.
  - `_domain_of` выделен из URL-парсинга; `_is_company_domain` использует его.
  - Расширен `AGGREGATOR_DOMAINS`: +checko, companies.rbc, skyscanner, aviasales, tripadvisor, booking, airbnb, ostrovok, kinopoisk, wikipedia, соцсети, ozon, wildberries и др.
- **`backend/app/ai_qualify.py`** — квалификация (ВЭД) переведена с Tavily на `_search_zveno_perplexity`.
- **`backend/app/routers/ai_search.py`** — проверка ключа: `tavily_api_key` → `zveno_api_key`. API-контракт ответа не менялся: `suggestions`, `ai_summary`, `sources`, `company`, `has_pending`.
- **`backend/requirements.txt`** — удалены `tavily-python==0.5.1` и `duckduckgo-search>=8.0.0` (мертвы).
- **`frontend`** — не менялся; `sources` уже рендерились в `CompanyCard.tsx`.

### Проверено вживую (после деплоя)
- АТИС → `atis-auto.ru`, `+7 (495) 781-15-24`, `info@atis-auto.ru`, 8 sources, ~5s.
- ВИП-СИСТЕМЫ / ВИЛИТЕК → сайт/телефон/деятельность/описание, 8 sources.
- Квалификация ВИЛИТЕК → score 75, `has_ved: true`.

### Деплой
Локально → scp файлов на VPS (`/opt/novel-crm/backend/app/`) → `docker compose build backend && up -d`. ВНИМАНИЕ: `scp` с несколькими файлами срезает пути — копировать каждый файл отдельно. Запись об изменениях: этот файл. Graph коммитить **не** нужно (см. `.gitignore`).

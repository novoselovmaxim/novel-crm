# Novel CRM — Next Session Plan

> Created: 2026-05-26
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
- **Deploy**: Docker Compose, FastAPI serves static frontend, nginx on host, SSL via Let's Encrypt, port 3020

### Partially implemented 🔶
- **Telegram bot**: `telegram_webhook.py` (webhook handler, /start, /help, /status, /unbind commands), `notifications.py` (TelegramNotifier with send_message, notify_user_by_email), `POST /api/telegram/bind`, `POST /api/telegram/notify`, `GET /api/telegram/status/{email}`. Missing: TgToken model, /auth/tg-link endpoint, scheduler, proper bind flow, frontend profile, trigger notifications
- **Dashboard**: Only basic `/dashboard/me` metrics. No funnel, team dashboard, stale contacts, quick presets

### Not implemented ❌
- User management UI (not needed — only for current team)
- Manual company creation form
- Audit log frontend
- Mobile view (< 768px)

---

## Step 1: Telegram Bot — Model & Bind Flow

### 1.1 Add `TgToken` model

File: `backend/app/models.py`

Add model `TgToken`:
- `id` UUID PK
- `user_id` UUID FK users
- `token` TEXT UNIQUE
- `created_at` TIMESTAMPTZ
- `expires_at` TIMESTAMPTZ
- `used` BOOLEAN DEFAULT false

### 1.2 Add `/auth/tg-link` endpoint

File: `backend/app/routers/auth.py`

New endpoint `POST /api/auth/tg-link` (auth required):
- Generates `TgToken` with 15 min expiry
- Returns token + bot username
- URL format: `https://t.me/novelsales_bot?start={token}`

### 1.3 Add `/auth/tg-bind` endpoint

File: `backend/app/routers/auth.py`

New endpoint `POST /api/auth/tg-bind` (no auth — called by bot):
- Receives `{ token, chat_id, username }`
- Validates token (exists, not expired, not used)
- Marks token as used
- Sets `tg_chat_id` and `tg_username` on User
- Sends welcome message via `notifier`

### 1.4 Update bot webhook handlers

File: `backend/app/telegram_webhook.py`

- Update `/start` to handle `?start={token}` — call `/api/auth/tg-bind`
- Add `/unbind` — clear `tg_chat_id` on User
- Add `/tasks` — query today's tasks from DB
- Add `/stats` — query call stats from DB

### 1.5 Frontend: Profile button

New file: `frontend/src/components/ProfileModal.tsx`

Or add to header in `Dashboard.tsx`:
- "Настройки" button in header (visible for all users)
- Shows Telegram bind status
- "Привязать Telegram" button → fetches `/api/auth/tg-link` → opens `t.me/novelsales_bot?start={token}`
- "Отвязать" button → calls `/api/auth/tg-unbind`

---

## Step 2: Scheduler for Briefs & Reminders

### 2.1 Add APScheduler

New file: `backend/app/scheduler.py`

- Initialize `AsyncIOScheduler` on FastAPI startup
- Store reference in app state

### 2.2 Morning brief (9:00 MSK)

Function `morning_brief()`:
- For each manager: query companies where `next_call_date = today` and `assigned_to = user.id` → send tasks list
- For each manager: query `call_count` where `called_at = yesterday` → send stats
- For admin+lead: aggregate all managers' stats → send team summary

### 2.3 Evening summary (18:00 MSK)

Function `evening_summary()`:
- For each manager: count calls made today, status breakdown → send
- For admin+lead: team aggregate

### 2.4 Meeting reminders

Cron every 15 minutes:
- Query meetings where `date = today` and `hour = now+1` → send 60-min reminder to manager + lead
- Query meetings where `date = today` and `hour = now+0.25` → send 15-min reminder to manager

### 2.5 Trigger notifications

Hooks in `backend/app/routers/companies.py`:
- On assign: notify manager `notifier.notify_user_by_email(assignee_email, text)`
- On status change to "meeting": notify admin+lead
- On status change to "interested": schedule stale check

Stale check (daily in scheduler):
- Companies with `call_status = 'interested'` and `updated_at < now() - 3 days` → notify assigned manager

---

## Step 3: Bulk Actions (Checkboxes, Status, CSV)

### 3.1 Backend

File: `backend/app/routers/companies.py`

- `POST /api/companies/bulk-status` — body `{ company_ids: [...], status: string }` → update all
- `POST /api/companies/export` — body `{ company_ids: [...] }` → return CSV file with all company fields

### 3.2 Frontend

File: `frontend/src/components/CompanyTable.tsx`

- Add checkbox column (first column)
- Track `selectedIds: Set<string>` state
- Show selection toolbar when `selectedIds.size > 0`
  - "Изменить статус" dropdown → PATCH bulk-status
  - "Экспорт CSV" button → POST export → download file
- Toggle all checkbox in header

---

## Step 4: Client Timezone in Company Card

### 4.1 Region → UTC mapping

New file: `frontend/src/utils/timezone.ts`

Map of Russian regions to UTC offsets:
```typescript
const REGION_TZ: Record<string, number> = {
  'Калининград': 2,
  'Москва': 3,
  'Санкт-Петербург': 3,
  'Самара': 4,
  'Екатеринбург': 5,
  'Омск': 6,
  'Красноярск': 7,
  'Иркутск': 8,
  'Владивосток': 10,
  // ...etc
}
```

### 4.2 Display in CompanyCard

File: `frontend/src/components/CompanyCard.tsx`

Add timezone block in the upper zone:
```
🕐 Регион: Калининград (UTC+2)
Текущее время клиента: 14:30 🟢
```

Use `Intl.DateTimeFormat` with the detected UTC offset to show current time.
Color indicator:
- 🟢 9:00–18:00 = рабочее
- 🟡 8:00–9:00, 18:00–20:00 = граничное
- 🔴 20:00–8:00 = нерабочее

Also show admin's current time for comparison.

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

| File | Step |
|------|------|
| `backend/app/models.py` | 1.1 |
| `backend/app/routers/auth.py` | 1.2, 1.3 |
| `backend/app/telegram_webhook.py` | 1.4 |
| `backend/app/scheduler.py` | 2.1 (new) |
| `backend/app/notifications.py` | 2.2-2.5 |
| `backend/app/main.py` | 2.1 |
| `backend/app/routers/companies.py` | 2.5, 3.1 |
| `frontend/src/components/ProfileModal.tsx` | 1.5 (new) |
| `frontend/src/pages/Dashboard.tsx` | 1.5 |
| `frontend/src/components/CompanyTable.tsx` | 3.2 |
| `frontend/src/components/CompanyCard.tsx` | 4.2 |
| `frontend/src/utils/timezone.ts` | 4.1 (new) |
| `frontend/src/api/client.ts` | 3.2 |

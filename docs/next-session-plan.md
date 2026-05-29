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
| `backend/app/telegram_webhook.py` | +/tasks, /stats, /unbind, token /start |
| `backend/app/scheduler.py` | New: APScheduler, briefs, reminders, stale check |
| `backend/app/main.py` | +scheduler init on startup |
| `backend/app/routers/companies.py` | +notifications on assign & meeting status |
| `backend/app/schemas.py` | +tg fields in UserResponse |
| `backend/requirements.txt` | +apscheduler |
| `frontend/src/components/ProfileModal.tsx` | New: Telegram bind/unbind UI |
| `frontend/src/pages/Dashboard.tsx` | +"Настройки" button |
| `frontend/src/components/CompanyCard.tsx` | Fix: status buttons, LPR fields; +TimeZoneBlock |
| `frontend/src/utils/timezone.ts` | New: region to UTC mapping |

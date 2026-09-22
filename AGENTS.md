# AGENTS.md — Project Safety Rules

## ⚠️ CRITICAL: DATABASE SAFETY — MANDATORY

**NEVER run destructive database operations without verified backup.**

### Forbidden without backup:
- `docker compose down -v` (removes volumes)
- `docker volume rm`
- Any DB migration (Alembic, raw SQL)
- `DROP TABLE`, `TRUNCATE`, `DELETE` without WHERE
- Any operation that can lose data

### Required before ANY of the above:
1. **Verify backup exists** — check `/opt/novel-crm/backups/` on VPS or run manual `pg_dump`
2. **Verify backup is restorable** — test restore to a temp DB if possible
3. **Document the backup timestamp** in commit message or deployment log

### Historical incident:
> **2026-09-18**: Lost 73,312 companies + all activity/history (pipeline, activities, communications, meetings) due to `docker compose down -v` without backup. Recovered 39,453 companies from local Excel exports; original data with full history **LOST PERMANENTLY**.

### Backup schedule (VPS):
- Daily at 03:00 via `/opt/novel-crm/backup_to_telegram.sh` → Telegram bot
- Local retention: 7 days in `/opt/novel-crm/backups/` (~15MB each)
- Script NOT in repo — lives on VPS only

### Emergency backup command (run on VPS):
```bash
docker compose exec postgres pg_dump -U novel novel_crm | gzip > /opt/novel-crm/backups/emergency_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## Code Safety Rules

### Before any DB schema change:
1. Create migration file (Alembic) — never raw SQL in prod
2. Test migration locally on copy of production data
3. Verify rollback works
4. Deploy with `docker compose exec backend alembic upgrade head`

### Before any bulk data operation:
1. Test on 10-20 records first
2. Use transactions — wrap in `async with db.begin():`
3. Have rollback plan documented

### Field allowlist enforcement:
- Never use `setattr(model, user_input, value)` without allowlist
- All `apply` / `save` endpoints must validate field names against explicit allowlist

---

## Environment
- Production DB: `novel_crm` on `localhost:5433` (host network), user `novel`, password from `.env`
- Local DB: `novel_crm_dev` on `localhost:5432`, user `novel`, password `novel_secret_dev`
- `.env` files are NOT committed — each environment has its own

---

## Deployment
- Use `deploy/deploy.sh` — it handles build, migrations, restart, health check
- Never manually `docker compose restart` without health check
- Nginx runs on host (port 80/443) — Docker nginx is DISABLED (AppArmor issues)
- After server reboot: `sysctl -w net.ipv4.ip_nonlocal_bind=1` before starting nginx

---

## TypeSafe Integration Rules
- TypeSafe COMPLEMENTS existing AI — does NOT replace search/extraction
- TypeSafe validates EXTRACTED data quality, does NOT search
- Confidence threshold: 0.7 default for "needs_review" flag
- Store validation results in `ai_suggestions["validation"]` — separate from extraction/qualification
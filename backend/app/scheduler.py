import logging
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select, func
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import async_session
from app.models import User, Company, CallLog, Meeting, FollowUp
from app.notifications import notifier
from app.bounce_handler import poll_bounces

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))

async def morning_brief():
    now_msk = datetime.now(timezone.utc).astimezone(MSK)
    today = now_msk.date()
    yesterday = today - timedelta(days=1)
    async with async_session() as db:
        managers = await db.execute(select(User).where(User.tg_chat_id != None))
        managers = managers.scalars().all()

        admin_team_lines = []

        for user in managers:
            tasks = await db.execute(
                select(Company).where(
                    Company.assigned_to == user.id,
                    Company.next_call_date == today,
                    Company.is_deleted == False,
                    Company.call_status != "refused"
                )
            )
            tasks = tasks.scalars().all()

            calls_yesterday = await db.execute(
                select(func.count(CallLog.id)).where(
                    CallLog.user_id == user.id,
                    func.date(func.timezone('+03', CallLog.called_at)) == yesterday
                )
            )
            calls_count = calls_yesterday.scalar() or 0

            if tasks or user.role in ("admin", "lead"):
                lines = [f"Доброе утро, {user.name or user.email}!"]
                if tasks:
                    lines.append(f"Задач на сегодня: {len(tasks)}")
                    for c in tasks[:10]:
                        lines.append(f"- {c.name} (ИНН {c.inn})")
                    if len(tasks) > 10:
                        lines.append(f"...и ещё {len(tasks) - 10}")
                lines.append(f"Звонков вчера: {calls_count}")
                text = "\n".join(lines)
                await notifier.send_message(user.tg_chat_id, text)

            if user.role in ("admin", "lead"):
                admin_team_lines.append(f"{user.name or user.email}: {calls_count} зв., {len(tasks)} зад.")

        if admin_team_lines:
            await notifier.send_message(
                managers[0].tg_chat_id,
                "Сводка по команде:\n" + "\n".join(admin_team_lines)
            )

async def evening_summary():
    now_msk = datetime.now(timezone.utc).astimezone(MSK)
    today = now_msk.date()
    async with async_session() as db:
        managers = await db.execute(select(User).where(User.tg_chat_id != None))
        managers = managers.scalars().all()

        admin_team_lines = []

        for user in managers:
            calls_today = await db.execute(
                select(func.count(CallLog.id)).where(
                    CallLog.user_id == user.id,
                    func.date(func.timezone('+03', CallLog.called_at)) == today
                )
            )
            calls_count = calls_today.scalar() or 0

            statuses = await db.execute(
                select(CallLog.call_status, func.count(CallLog.id)).where(
                    CallLog.user_id == user.id,
                    func.date(func.timezone('+03', CallLog.called_at)) == today
                ).group_by(CallLog.call_status)
            )
            status_rows = statuses.all()

            lines = [f"Итог дня, {user.name or user.email}!"]
            lines.append(f"Звонков сегодня: {calls_count}")
            if status_rows:
                for s, cnt in status_rows:
                    lines.append(f"- {s}: {cnt}")
            text = "\n".join(lines)
            await notifier.send_message(user.tg_chat_id, text)

            if user.role in ("admin", "lead"):
                status_parts = ", ".join(f"{s}: {cnt}" for s, cnt in status_rows)
                admin_team_lines.append(f"{user.name or user.email}: {calls_count} зв. ({status_parts})")

        if admin_team_lines:
            admin_user = await db.execute(
                select(User).where(User.role.in_(["admin", "lead"]), User.tg_chat_id != None)
            )
            admin_user = admin_user.scalar_one_or_none()
            if admin_user:
                await notifier.send_message(
                    admin_user.tg_chat_id,
                    "Итоги команды:\n" + "\n".join(admin_team_lines)
                )

async def meeting_reminders():
    now_msk = datetime.now(timezone.utc).astimezone(MSK)
    today = now_msk.date()
    tomorrow = today + timedelta(days=1)
    minutes_now = now_msk.hour * 60 + now_msk.minute

    async with async_session() as db:
        meetings = await db.execute(
            select(Meeting, Company.name, User.tg_chat_id, User.name.label("manager_name"))
            .join(Company, Meeting.company_id == Company.id)
            .join(User, Meeting.booked_by == User.id)
            .where(Meeting.date.in_([today, tomorrow]))
        )
        meetings = meetings.all()

        admin_rows = await db.execute(
            select(User.id, User.tg_chat_id).where(User.role.in_(["admin", "lead"]), User.tg_chat_id != None)
        )
        admin_chats = {admin_chat for _, admin_chat in admin_rows.all() if admin_chat}

        for meeting, company_name, chat_id, manager_name in meetings:
            if not chat_id:
                continue
            chat_ids = {chat_id} | admin_chats
            if meeting.date == tomorrow and not meeting.reminded_1d:
                text = f"⏰ Напоминание: встреча с {company_name} завтра в {meeting.hour:02d}:00."
                for cid in chat_ids:
                    await notifier.send_message(cid, text)
                meeting.reminded_1d = True
                await db.commit()
            elif meeting.date == today:
                meeting_minutes = meeting.hour * 60
                minutes_until = meeting_minutes - minutes_now
                if not meeting.reminded_1h and 45 <= minutes_until <= 75:
                    text = f"⏰ Напоминание: встреча с {company_name} через ~1 час (в {meeting.hour:02d}:00)."
                    for cid in chat_ids:
                        await notifier.send_message(cid, text)
                    meeting.reminded_1h = True
                    await db.commit()
                elif not meeting.reminded_10m and 1 <= minutes_until <= 15:
                    text = f"⏰ Напоминание: встреча с {company_name} через ~10 минут (в {meeting.hour:02d}:00)."
                    for cid in chat_ids:
                        await notifier.send_message(cid, text)
                    meeting.reminded_10m = True
                    await db.commit()

async def stale_check():
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    async with async_session() as db:
        stale = await db.execute(
            select(Company).where(
                Company.call_status == "interested",
                Company.updated_at < three_days_ago,
                Company.is_deleted == False,
                Company.assigned_to != None
            )
        )
        stale = stale.scalars().all()

        for company in stale:
            manager = await db.execute(select(User).where(User.id == company.assigned_to))
            manager = manager.scalar_one_or_none()
            if manager and manager.tg_chat_id:
                await notifier.send_message(
                    manager.tg_chat_id,
                    f"Напоминание: компания {company.name} в статусе «Заинтересован» уже 3+ дня без активности."
                )

async def send_follow_ups():
    now = datetime.now(timezone.utc)
    async with async_session() as db:
        pending = await db.execute(
            select(FollowUp).where(
                FollowUp.status == "pending",
                FollowUp.scheduled_at <= now,
            )
        )
        for fup in pending.scalars().all():
            try:
                from app.email_sender import _send_via_smtp
                _send_via_smtp(
                    recipient_email=fup.recipient_email,
                    subject=fup.subject,
                    html_body=fup.body_html or "",
                    text_body=fup.body_text,
                )
                fup.status = "sent"
                fup.sent_at = now
                await db.commit()
                logger.info(f"Follow-up {fup.id} sent to {fup.recipient_email}")
            except Exception:
                logger.exception(f"Failed to send follow-up {fup.id}")
                fup.status = "failed"
                await db.commit()


def create_scheduler():
    scheduler = AsyncIOScheduler(timezone=MSK)

    scheduler.add_job(morning_brief, "cron", hour=9, minute=0, id="morning_brief")
    scheduler.add_job(evening_summary, "cron", hour=18, minute=0, id="evening_summary")
    scheduler.add_job(meeting_reminders, "interval", minutes=15, id="meeting_reminders")
    scheduler.add_job(stale_check, "cron", hour=10, minute=0, id="stale_check")
    scheduler.add_job(send_follow_ups, "interval", minutes=15, id="send_follow_ups")
    scheduler.add_job(poll_bounces, "interval", minutes=5, id="poll_bounces")

    return scheduler

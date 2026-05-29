import os
import logging
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select, func
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from app.database import async_session
from app.models import User, Company, CallLog, TgToken
from app.notifications import notifier

logger = logging.getLogger(__name__)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "7700904608:AAEqNYwQ2pMUXsmidO9P0fkLzvgFHbI4rOY")
TG_WEBHOOK_URL = os.getenv("TG_WEBHOOK_URL", "https://novel.maxnov.ru/api/telegram/webhook")

router = APIRouter(prefix="/api/telegram", tags=["telegram-webhook"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    token = args[0] if args else None

    if token:
        async with async_session() as db:
            result = await db.execute(
                select(TgToken).where(
                    TgToken.token == token,
                    TgToken.used == False,
                    TgToken.expires_at > datetime.now(timezone.utc)
                )
            )
            tg_token = result.scalar_one_or_none()
            if tg_token:
                result = await db.execute(select(User).where(User.id == tg_token.user_id))
                user = result.scalar_one_or_none()
                if user:
                    tg_token.used = True
                    user.tg_chat_id = update.effective_chat.id
                    user.tg_username = update.effective_user.username
                    await db.commit()
                    await update.message.reply_text(
                        f"Аккаунт привязан!\n"
                        f"Пользователь: {user.name or user.email}\n\n"
                        f"Теперь вы будете получать уведомления из CRM."
                    )
                    await notifier.send_message(
                        update.effective_chat.id,
                        f"Добро пожаловать в Novel CRM, {user.name or user.email}!"
                    )
                    return

    await update.message.reply_text(
        "Novel CRM Bot\n\n"
        "Команды:\n"
        "/tasks - Мои задачи на сегодня\n"
        "/stats - Статистика звонков\n"
        "/unbind - Отвязать аккаунт\n"
        "/help - Справка"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/start - Запустить бота\n"
        "/tasks - Мои задачи на сегодня\n"
        "/stats - Статистика звонков\n"
        "/unbind - Отвязать аккаунт\n"
        "/help - Показать справку"
    )

async def unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    async with async_session() as db:
        result = await db.execute(select(User).where(User.tg_chat_id == chat_id))
        user = result.scalar_one_or_none()
        if user:
            user.tg_chat_id = None
            user.tg_username = None
            await db.commit()
            await update.message.reply_text("Аккаунт отвязан от Telegram.")
        else:
            await update.message.reply_text("Аккаунт не найден. Возможно, он уже отвязан.")

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    async with async_session() as db:
        result = await db.execute(select(User).where(User.tg_chat_id == chat_id))
        user = result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Аккаунт не привязан. Используйте /start с токеном из настроек CRM.")
            return

        today = date.today()
        stmt = select(Company).where(
            Company.assigned_to == user.id,
            Company.next_call_date == today,
            Company.is_deleted == False,
            Company.call_status != "refused"
        ).order_by(Company.call_status, Company.name)
        result = await db.execute(stmt)
        companies = result.scalars().all()

        if not companies:
            await update.message.reply_text("На сегодня задач нет.")
            return

        lines = [f"Задач на сегодня: {len(companies)}"]
        for c in companies:
            status_icon = {
                "new": "new", "callback": "callback", "in_progress": "in_progress",
                "interested": "interested", "meeting": "meeting"
            }.get(c.call_status, c.call_status)
            lines.append(f"{c.name} (ИНН {c.inn})")
        await update.message.reply_text("\n".join(lines))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    async with async_session() as db:
        result = await db.execute(select(User).where(User.tg_chat_id == chat_id))
        user = result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Аккаунт не привязан.")
            return

        today = date.today()
        total = await db.execute(
            select(func.count(CallLog.id)).where(
                CallLog.user_id == user.id,
                func.date(CallLog.called_at) == today
            )
        )
        calls_today = total.scalar() or 0

        assigned = await db.execute(
            select(func.count(Company.id)).where(
                Company.assigned_to == user.id,
                Company.is_deleted == False,
                Company.call_status != "refused"
            )
        )
        total_assigned = assigned.scalar() or 0

        next_calls = await db.execute(
            select(func.count(Company.id)).where(
                Company.assigned_to == user.id,
                Company.next_call_date == today,
                Company.is_deleted == False,
                Company.call_status != "refused"
            )
        )
        tasks_today = next_calls.scalar() or 0

        await update.message.reply_text(
            f"Статистика:\n\n"
            f"Звонков сегодня: {calls_today}\n"
            f"Задач на сегодня: {tasks_today}\n"
            f"Всего в работе: {total_assigned}"
        )

_application = None

def build_application():
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("unbind", unbind))
    return app

async def start_polling():
    global _application
    try:
        _application = build_application()
        await _application.initialize()
        await _application.updater.start_polling()
        try:
            await _application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Telegram webhook deleted, polling started")
        except Exception as e:
            logger.warning(f"Could not delete webhook: {e}")
        logger.info("Telegram bot polling started")
    except Exception as e:
        logger.error(f"Failed to start Telegram polling: {e}")
        _application = None

async def stop_polling():
    global _application
    if _application:
        try:
            await _application.updater.stop()
            await _application.stop()
            await _application.shutdown()
            logger.info("Telegram bot polling stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram polling: {e}")
        _application = None

@router.post("/webhook")
async def telegram_webhook(request: Request):
    if not _application:
        return {"status": "not_initialized"}
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, _application.bot)
        await _application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-webhook")
async def setup_webhook():
    return {"status": "polling_mode", "detail": "Bot is running in polling mode. Use delete-webhook to clear Telegram webhook."}

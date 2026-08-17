import os
import asyncio
import logging
from datetime import date, datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select, func
from telegram import Bot, Update

from app.database import async_session
from app.models import User, Company, CallLog, TgToken
from app.notifications import notifier

logger = logging.getLogger(__name__)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")

router = APIRouter(prefix="/api/telegram", tags=["telegram-webhook"])

_polling_task = None

async def start(update: Update, context):
    args = context.args if hasattr(context, 'args') else []
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

async def help_command(update: Update, context):
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/start - Запустить бота\n"
        "/tasks - Мои задачи на сегодня\n"
        "/stats - Статистика звонков\n"
        "/unbind - Отвязать аккаунт\n"
        "/help - Показать справку"
    )

async def unbind(update: Update, context):
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

async def tasks_command(update: Update, context):
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
            lines.append(f"{c.name} (ИНН {c.inn})")
        await update.message.reply_text("\n".join(lines))

async def stats_command(update: Update, context):
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

_handlers = {}

async def _handle_update(bot, update):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text.startswith('/'):
        return

    parts = text.split()
    command = parts[0].lower().lstrip('/')

    context = type('Context', (), {'args': parts[1:]})()
    context.bot = bot

    handler = _handlers.get(command)
    if handler:
        try:
            await handler(update, context)
        except Exception as e:
            logger.error(f"Error handling /{command}: {e}")
            try:
                await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
            except Exception:
                pass
    else:
        await update.message.reply_text(
            "Неизвестная команда. Используйте /help для списка команд."
        )

async def _polling_loop(bot):
    offset = 0
    while True:
        try:
            updates = await bot.get_updates(
                offset=offset,
                timeout=30,
                allowed_updates=['message']
            )
            for update in updates:
                offset = update.update_id + 1
                await _handle_update(bot, update)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)

async def start_polling():
    global _polling_task
    if not TG_BOT_TOKEN:
        logger.warning("TG_BOT_TOKEN not set, Telegram polling disabled")
        return
    bot = Bot(token=TG_BOT_TOKEN)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Telegram webhook deleted")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")

    _handlers['start'] = start
    _handlers['help'] = help_command
    _handlers['tasks'] = tasks_command
    _handlers['stats'] = stats_command
    _handlers['unbind'] = unbind

    _polling_task = asyncio.create_task(_polling_loop(bot))
    logger.info("Telegram bot polling started")

async def stop_polling():
    global _polling_task
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except Exception:
            pass
        _polling_task = None
        logger.info("Telegram bot polling stopped")

@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, Bot(token=TG_BOT_TOKEN))
        await _handle_update(Bot(token=TG_BOT_TOKEN), update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-webhook")
async def setup_webhook():
    return {"status": "polling_mode", "detail": "Bot is running in polling mode."}

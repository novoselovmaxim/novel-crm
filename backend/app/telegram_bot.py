import asyncio
import os
from datetime import datetime, date
from sqlalchemy import select, func
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from app.database import async_session
from app.models import User, Company, CallLog

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Novel CRM Bot\n\n"
        "Команды:\n"
        "/bind - Привязать аккаунт CRM\n"
        "/tasks - Мои задачи на сегодня\n"
        "/stats - Статистика"
    )

async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    await update.message.reply_text(
        f"✅ Telegram привязан!\n"
        f"Chat ID: {chat_id}\n"
        f"Username: @{username or 'N/A'}\n\n"
        "Теперь вы будете получать уведомления из CRM."
    )

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def main():
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bind", bind))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("stats", stats))
    
    print("🤖 Telegram bot started (polling mode)")
    app.run_polling()

if __name__ == "__main__":
    main()

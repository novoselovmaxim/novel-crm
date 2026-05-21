import asyncio
import os
from datetime import datetime, date
from sqlalchemy import select, func
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "7700904608:AAEqNYwQ2pMUXsmidO9P0fkLzvgFHbI4rOY")

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
    await update.message.reply_text(
        "📋 Задачи на сегодня:\n\n"
        "Функционал в разработке..."
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Статистика:\n\n"
        "Функционал в разработке..."
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

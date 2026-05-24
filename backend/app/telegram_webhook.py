import os
import logging
from fastapi import APIRouter, Request, HTTPException
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "7700904608:AAEqNYwQ2pMUXsmidO9P0fkLzvgFHbI4rOY")
TG_WEBHOOK_URL = os.getenv("TG_WEBHOOK_URL", "https://novel.maxnov.ru/api/telegram/webhook")

router = APIRouter(prefix="/api/telegram", tags=["telegram-webhook"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Novel CRM Bot</b>\n\n"
        "Этот бот привязан к CRM системе Novel.\n\n"
        "Для привязки аккаунта:\n"
        "1. Откройте настройки в CRM\n"
        "2. Нажмите 'Привязать Telegram'\n"
        "3. Подтвердите привязку\n\n"
        "После привязки вы будете получать уведомления о:\n"
        "• Новых задачах\n"
        "• Изменениях статусов\n"
        "• Напоминаниях о звонках"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Доступные команды:</b>\n\n"
        "/start - Запустить бота\n"
        "/help - Показать справку\n"
        "/status - Статус привязки\n"
        "/unbind - Отвязать аккаунт"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"📊 <b>Статус:</b>\n\n"
        f"Chat ID: {chat_id}\n"
        f"Статус: Ожидает привязки к CRM\n\n"
        f"Для привязки откройте настройки в CRM."
    )

class TelegramWebhookHandler:
    def __init__(self):
        self.application = None

    async def initialize(self):
        self.application = ApplicationBuilder().token(TG_BOT_TOKEN).build()
        
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("status", status_command))
        
        try:
            await self.application.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Telegram application: {e}")
            self.application = None
            return
        
        try:
            await self.application.bot.set_webhook(url=TG_WEBHOOK_URL)
            logger.info(f"Telegram webhook set to {TG_WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {e}")

    async def process_update(self, request: Request):
        if not self.application:
            await self.initialize()
        
        try:
            update_data = await request.json()
            update = Update.de_json(update_data, self.application.bot)
            await self.application.process_update(update)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}")
            raise HTTPException(status_code=500, detail=str(e))

webhook_handler = TelegramWebhookHandler()

@router.post("/webhook")
async def telegram_webhook(request: Request):
    return await webhook_handler.process_update(request)

@router.post("/setup-webhook")
async def setup_webhook():
    if not webhook_handler.application:
        await webhook_handler.initialize()
    try:
        await webhook_handler.application.bot.set_webhook(url=TG_WEBHOOK_URL)
        return {"status": "ok", "webhook_url": TG_WEBHOOK_URL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

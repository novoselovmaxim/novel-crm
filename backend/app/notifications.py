import asyncio
import os
import logging
from typing import Optional
from sqlalchemy import select
from telegram import Bot
from app.database import async_session
from app.models import User

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TG_BOT_TOKEN", "7700904608:AAEqNYwQ2pMUXsmidO9P0fkLzvgFHbI4rOY")
        self.bot = Bot(token=self.token)
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            try:
                me = await self.bot.get_me()
                logger.info(f"Telegram bot initialized: @{me.username}")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self._initialized = False

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML"):
        if not self._initialized:
            await self.initialize()
        if not self._initialized:
            logger.warning("Telegram bot not initialized, skipping message")
            return False
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return False

    async def notify_user_by_email(self, email: str, text: str):
        async with async_session() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user and user.tg_chat_id:
                return await self.send_message(user.tg_chat_id, text)
        return False

    async def notify_all_managers(self, text: str):
        async with async_session() as session:
            result = await session.execute(select(User).where(User.tg_chat_id != None))
            users = result.scalars().all()
            for user in users:
                await self.send_message(user.tg_chat_id, text)

notifier = TelegramNotifier()

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.notifications import notifier
from typing import Optional
import logging

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

class BindRequest(BaseModel):
    email: str
    chat_id: int
    username: Optional[str] = None

class MessageRequest(BaseModel):
    chat_id: int
    text: str

class TestNotificationRequest(BaseModel):
    email: str

@router.post("/bind")
async def bind_telegram(request: BindRequest, db=Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.tg_chat_id = request.chat_id
    user.tg_username = request.username
    await db.commit()
    
    await notifier.send_message(
        request.chat_id,
        f"✅ <b>Аккаунт привязан!</b>\n\n"
        f"Пользователь: {user.name or user.email}\n"
        f"Роль: {user.role.value}\n\n"
        f"Теперь вы будете получать уведомления из CRM."
    )
    
    return {"status": "ok", "message": "Telegram account bound successfully"}

@router.post("/test")
async def test_notification(request: TestNotificationRequest, db=Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not user.tg_chat_id:
        raise HTTPException(status_code=404, detail="User not found or Telegram not bound")
    
    success = await notifier.notify_user_by_email(
        request.email,
        "🔔 <b>Тестовое уведомление</b>\n\n"
        "Это тестовое сообщение из Novel CRM.\n"
        "Если вы его видите - уведомления работают! ✅"
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    
    return {"status": "ok", "message": "Test notification sent"}

@router.post("/notify")
async def send_notification(request: MessageRequest):
    success = await notifier.send_message(request.chat_id, request.text)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"status": "ok"}

@router.get("/status/{email}")
async def telegram_status(email: str, db=Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "email": user.email,
        "telegram_bound": user.tg_chat_id is not None,
        "chat_id": user.tg_chat_id,
        "username": user.tg_username
    }

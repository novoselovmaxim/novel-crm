import uuid
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db, settings
from ..models import User, TgToken
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from ..auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])

TG_BOT_USERNAME = os.getenv("TG_BOT_USERNAME", "novelsales_bot")


class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)})
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    try:
        payload = jwt.decode(request.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return TokenResponse(
        access_token=create_access_token({"sub": user_id}),
        refresh_token=create_refresh_token({"sub": user_id})
    )


@router.post("/register", response_model=UserResponse)
async def register(
    request: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        role=request.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/managers", response_model=list[UserResponse])
async def list_managers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.role == "manager", User.is_active == True))
    return result.scalars().all()

class TgLinkResponse(BaseModel):
    token: str
    bot_username: str
    link: str

@router.post("/tg-link", response_model=TgLinkResponse)
async def tg_link(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    token = str(uuid.uuid4())
    tg_token = TgToken(
        user_id=current_user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db.add(tg_token)
    await db.commit()
    return TgLinkResponse(
        token=token,
        bot_username=TG_BOT_USERNAME,
        link=f"https://t.me/{TG_BOT_USERNAME}?start={token}"
    )

class TgBindRequest(BaseModel):
    token: str
    chat_id: int
    username: str | None = None

@router.post("/tg-bind")
async def tg_bind(
    request: TgBindRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TgToken).where(
            TgToken.token == request.token,
            TgToken.used == False,
            TgToken.expires_at > datetime.now(timezone.utc)
        )
    )
    tg_token = result.scalar_one_or_none()
    if not tg_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == tg_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tg_token.used = True
    user.tg_chat_id = request.chat_id
    user.tg_username = request.username
    await db.commit()

    from ..notifications import notifier
    await notifier.send_message(
        request.chat_id,
        f"Аккаунт привязан!\n\n"
        f"Пользователь: {user.name or user.email}\n"
        f"Роль: {user.role.value}\n\n"
        f"Теперь вы будете получать уведомления из CRM."
    )

    return {"status": "ok", "message": "Telegram account bound successfully"}

@router.post("/tg-unbind")
async def tg_unbind(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.tg_chat_id = None
    current_user.tg_username = None
    await db.commit()
    return {"status": "ok", "message": "Telegram account unbound successfully"}

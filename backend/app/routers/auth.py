from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db, settings
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from ..auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


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

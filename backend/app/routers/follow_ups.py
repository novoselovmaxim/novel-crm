"""Follow-ups — create, list, update, cancel."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Company, FollowUp, User
from ..schemas import FollowUpCreate, FollowUpResponse, FollowUpUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/follow-ups", tags=["follow-ups"])


@router.get("/{company_id}", response_model=list[FollowUpResponse])
async def list_follow_ups(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FollowUp)
        .where(FollowUp.company_id == company_id)
        .order_by(FollowUp.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=FollowUpResponse, status_code=201)
async def create_follow_up(
    req: FollowUpCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == req.company_id, Company.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")

    fup = FollowUp(
        company_id=req.company_id,
        user_id=current_user.id,
        recipient_email=req.recipient_email,
        trigger_type=req.trigger_type,
        subject=req.subject,
        body_html=req.body_html,
        body_text=req.body_text,
        scheduled_at=req.scheduled_at,
    )
    db.add(fup)
    await db.commit()
    await db.refresh(fup)
    return fup


@router.patch("/{fup_id}", response_model=FollowUpResponse)
async def update_follow_up(
    fup_id: uuid.UUID,
    req: FollowUpUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FollowUp).where(FollowUp.id == fup_id))
    fup = result.scalar_one_or_none()
    if not fup:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fup, key, value)
    await db.commit()
    await db.refresh(fup)
    return fup

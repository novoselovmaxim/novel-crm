from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date

from collections import Counter

from ..database import get_db
from ..models import User, Company, CallLog
from ..schemas import DashboardMetrics
from ..auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/me", response_model=DashboardMetrics)
async def my_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    base_query = select(Company).where(Company.is_deleted == False)
    if current_user.role == "manager":
        base_query = base_query.where(Company.assigned_to == current_user.id)
    
    result = await db.execute(base_query)
    companies = result.scalars().all()
    
    today = date.today()
    tasks_today = sum(1 for c in companies if c.next_call_date == today)
    overdue = sum(1 for c in companies if c.next_call_date and c.next_call_date < today)
    
    calls_today_result = await db.execute(
        select(func.count(CallLog.id)).where(
            CallLog.user_id == current_user.id,
            func.date(CallLog.called_at) == today
        )
    )
    calls_today = calls_today_result.scalar() or 0
    
    total_all = sum(1 for c in companies if c.call_status != "refused")
    
    pipeline_counts = dict(Counter(c.pipeline_stage for c in companies if c.pipeline_stage))
    
    return DashboardMetrics(
        total_companies=total_all,
        new_companies=sum(1 for c in companies if c.call_status == "new"),
        in_progress=sum(1 for c in companies if c.call_status == "in_progress"),
        interested=sum(1 for c in companies if c.call_status == "interested"),
        meetings_scheduled=sum(1 for c in companies if c.call_status == "meeting"),
        refused=sum(1 for c in companies if c.call_status == "refused"),
        calls_today=calls_today,
        tasks_today=tasks_today,
        overdue=overdue,
        archived=sum(1 for c in companies if c.call_status == "refused"),
        unprocessed=sum(1 for c in companies if c.call_count == 0 and c.call_status != "refused"),
        pipeline_counts=pipeline_counts,
    )

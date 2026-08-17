from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import uuid

from ..database import get_db
from ..models import User, Company, PipelineLog, Meeting
from ..schemas import CompanyResponse, PipelineLogResponse, PipelineStageUpdate
from ..auth import get_current_user

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

PIPELINE_STAGES = [
    "new", "in_progress", "message_sent", "diagnosis_done", "test_offered",
    "test_done", "reserve", "client", "partner"
]

HIDDEN_STATUSES = ["refused"]


@router.get("")
async def get_pipeline_board(
    search: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    base = select(Company).where(
        Company.is_deleted == False,
        Company.pipeline_stage.in_(PIPELINE_STAGES),
        ~Company.call_status.in_(HIDDEN_STATUSES),
    )

    if current_user.role == "manager":
        base = base.where(Company.assigned_to == current_user.id)
    elif assigned_to:
        base = base.where(Company.assigned_to == assigned_to)

    if search:
        base = base.where(Company.name.ilike(f"%{search}%"))

    result = await db.execute(base)
    all_companies = result.scalars().all()

    meeting_map = {}
    m_result = await db.execute(
        select(Meeting, Company.name)
        .join(Company, Meeting.company_id == Company.id)
        .order_by(Meeting.date.desc(), Meeting.hour.desc())
    )
    for m, cname in m_result.all():
        meeting_map.setdefault(str(m.company_id), {
            "date": m.date.isoformat(),
            "hour": m.hour,
            "company_name": cname,
            "notes": m.notes,
        })

    groups = []
    for stage in PIPELINE_STAGES:
        stage_companies = [c for c in all_companies if c.pipeline_stage == stage]
        items = []
        for c in stage_companies[:20]:
            data = CompanyResponse.model_validate(c)
            data.has_meeting = str(c.id) in meeting_map
            data.next_meeting = meeting_map.get(str(c.id))
            items.append(data)
        groups.append({
            "stage": stage,
            "count": len(stage_companies),
            "companies": items,
        })

    return {"groups": groups, "total": len(all_companies)}


@router.patch("/{company_id}")
async def move_company_stage(
    company_id: uuid.UUID,
    request: PipelineStageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    from_stage = company.pipeline_stage
    company.pipeline_stage = request.stage

    log = PipelineLog(
        company_id=company.id,
        user_id=current_user.id,
        from_stage=from_stage,
        to_stage=request.stage,
    )
    db.add(log)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("/log/{company_id}", response_model=list[PipelineLogResponse])
async def get_pipeline_log(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PipelineLog)
        .where(PipelineLog.company_id == company_id)
        .order_by(PipelineLog.changed_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/stages")
async def list_stages():
    labels = {
        "new": "Новый",
        "in_progress": "В работе",
        "message_sent": "Сообщение отправлено",
        "diagnosis_done": "Диагностика пройдена",
        "test_offered": "Тест предложен",
        "test_done": "Тест выполнен",
        "reserve": "Резерв",
        "client": "Клиент",
        "partner": "Партнёр",
    }
    return {"stages": [{"key": s, "label": labels.get(s, s)} for s in PIPELINE_STAGES]}

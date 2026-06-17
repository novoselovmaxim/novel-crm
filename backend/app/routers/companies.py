from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, distinct, case
from typing import Optional
import csv
import io
import uuid

from ..database import get_db
from ..models import User, Company, CallLog, AuditLog, ImportSourceData, CompanyComment, Meeting
from ..schemas import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse, CallLogCreate, CallLogResponse, AssignRequest, StatusUpdateRequest, BulkStatusRequest, BulkStatusResponse, ExportRequest, MeetingCreate, CommentCreate, CommentResponse
from ..auth import get_current_user, require_admin, require_admin_or_lead
from ..notifications import notifier
from ..cp_generator import generate_cp, generate_cp_html
from ..email_sender import send_cp_email

router = APIRouter(prefix="/api/companies", tags=["companies"])

ARCHIVE_STATUS = "refused"

@router.get("/regions")
async def list_regions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(distinct(Company.region)).where(Company.is_deleted == False, Company.region != None).order_by(Company.region)
    result = await db.execute(query)
    regions = [r[0] for r in result.all() if r[0]]
    return {"regions": regions}

@router.get("/org-forms")
async def list_org_forms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(distinct(Company.org_form)).where(Company.is_deleted == False, Company.org_form != None).order_by(Company.org_form)
    result = await db.execute(query)
    forms = [r[0] for r in result.all() if r[0]]
    return {"org_forms": forms}

@router.get("/activities")
async def list_activities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(distinct(Company.activity_main)).where(Company.is_deleted == False, Company.activity_main != None).order_by(Company.activity_main)
    result = await db.execute(query)
    activities = [r[0] for r in result.all() if r[0]]
    return {"activities": activities}

@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    region: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    archived: bool = Query(False, description="Show archived (refused) companies only"),
    source: Optional[str] = Query(None, description="Filter by import source id"),
    org_form: Optional[str] = Query(None, description="Filter by OPF"),
    activity: Optional[str] = Query(None, description="Filter by activity_main"),
    sort_by: Optional[str] = Query(None, description="Comma-separated sort fields: revenue, name"),
    sort_order: Optional[str] = Query("desc", description="Comma-separated sort orders: asc, desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Company).where(Company.is_deleted == False)
    count_query = select(func.count()).select_from(Company).where(Company.is_deleted == False)
    
    if archived:
        query = query.where(Company.call_status == ARCHIVE_STATUS)
        count_query = count_query.where(Company.call_status == ARCHIVE_STATUS)
    else:
        query = query.where(Company.call_status != ARCHIVE_STATUS)
        count_query = count_query.where(Company.call_status != ARCHIVE_STATUS)
    
    if current_user.role == "manager":
        query = query.where(Company.assigned_to == current_user.id)
        count_query = count_query.where(Company.assigned_to == current_user.id)
    
    if search:
        search_filter = or_(
            Company.name.ilike(f"%{search}%"),
            Company.inn.ilike(f"%{search}%"),
            Company.phone.ilike(f"%{search}%"),
            Company.email.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if region:
        query = query.where(Company.region == region)
        count_query = count_query.where(Company.region == region)
    
    if status:
        query = query.where(Company.call_status == status)
        count_query = count_query.where(Company.call_status == status)
    
    if assigned_to:
        query = query.where(Company.assigned_to == assigned_to)
        count_query = count_query.where(Company.assigned_to == assigned_to)
    
    if source:
        try:
            source_uuid = uuid.UUID(source)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid source UUID")
        subq = select(ImportSourceData.company_id).where(ImportSourceData.source_id == source_uuid, ImportSourceData.company_id.isnot(None))
        query = query.where(Company.id.in_(subq))
        count_query = count_query.where(Company.id.in_(subq))
    
    if org_form:
        query = query.where(Company.org_form == org_form)
        count_query = count_query.where(Company.org_form == org_form)
    
    if activity:
        query = query.where(Company.activity_main == activity)
        count_query = count_query.where(Company.activity_main == activity)
    
    SORTABLE = {"revenue": Company.revenue, "name": Company.name}
    if sort_by:
        fields = [s.strip() for s in sort_by.split(",") if s.strip() in SORTABLE]
        orders = [s.strip().lower() for s in (sort_order or "desc").split(",")]
        order_cols = []
        for i, f in enumerate(fields):
            col = SORTABLE[f]
            o = orders[i] if i < len(orders) else "desc"
            order_cols.append(col.asc().nulls_last() if o == "asc" else col.desc().nulls_last())
        if order_cols:
            query = query.order_by(*order_cols)
    else:
        query = query.order_by(
            case(
                (Company.next_call_date.is_(None), 0),
                (Company.call_status == "new", 1),
                else_=2
            ),
            Company.next_call_date.asc().nulls_last(),
            Company.created_at.desc().nulls_last()
        )
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    companies = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return CompanyListResponse(
        items=[CompanyResponse.model_validate(c) for c in companies],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return company

@router.post("", response_model=CompanyResponse)
async def create_company(
    request: CompanyCreate,
    current_user: User = Depends(require_admin_or_lead),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.inn == request.inn))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Company with this INN already exists")
    
    company = Company(**request.model_dump())
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company

@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    request: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_value = getattr(company, field)
        setattr(company, field, value)
        audit = AuditLog(
            user_id=current_user.id,
            company_id=company.id,
            field_name=field,
            old_value=str(old_value) if old_value else None,
            new_value=str(value) if value else None
        )
        db.add(audit)
    
    await db.commit()
    await db.refresh(company)
    return company

@router.get("/{company_id}/calls", response_model=list[CallLogResponse])
async def list_calls(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = (
        select(CallLog)
        .where(CallLog.company_id == company_id)
        .order_by(CallLog.called_at.desc())
        .limit(50)
    )
    rows = await db.execute(stmt)
    return rows.scalars().all()

@router.post("/{company_id}/call", response_model=CallLogResponse)
async def log_call(
    company_id: uuid.UUID,
    request: CallLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.call_count += 1
    company.call_status = request.call_status
    if request.next_call_date:
        company.next_call_date = request.next_call_date
    from sqlalchemy.sql import func as sql_func
    company.last_called_at = sql_func.now()
    
    call_log = CallLog(
        company_id=company_id,
        user_id=current_user.id,
        call_status=request.call_status,
        notes=request.notes
    )
    db.add(call_log)
    await db.commit()
    await db.refresh(call_log)

    if request.call_status == "meeting":
        admins = await db.execute(
            select(User).where(User.role.in_(["admin", "lead"]), User.tg_chat_id != None)
        )
        for admin in admins.scalars().all():
            await notifier.send_message(
                admin.tg_chat_id,
                f"Назначена встреча с {company.name} (ИНН {company.inn})"
            )

    return call_log

@router.delete("/{company_id}/calls/{call_id}")
async def delete_call(
    company_id: uuid.UUID,
    call_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(select(CallLog).where(CallLog.id == call_id, CallLog.company_id == company_id))
    call_log = result.scalar_one_or_none()
    if not call_log:
        raise HTTPException(status_code=404, detail="Call log not found")

    if current_user.role not in ("admin", "lead") and call_log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(call_log)
    if company.call_count > 0:
        company.call_count -= 1
    await db.commit()
    return {"message": "Call log deleted"}

@router.post("/{company_id}/meeting")
async def schedule_meeting(
    company_id: uuid.UUID,
    request: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    hour = int(request.meeting_time.split(':')[0])
    
    conflict = await db.execute(
        select(Meeting).where(Meeting.date == request.meeting_date, Meeting.hour == hour)
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Это время уже занято другой встречей")
    
    meeting = Meeting(
        company_id=company_id,
        booked_by=current_user.id,
        date=request.meeting_date,
        hour=hour,
        notes=request.notes,
    )
    db.add(meeting)
    
    company.call_status = "meeting"
    company.next_call_date = request.meeting_date
    
    call_log = CallLog(
        company_id=company_id,
        user_id=current_user.id,
        call_status="meeting",
        notes=f"Встреча: {request.meeting_date} {request.meeting_time}" + (f" - {request.notes}" if request.notes else "")
    )
    db.add(call_log)
    await db.commit()
    await db.refresh(meeting)
    return {"status": "ok", "message": f"Meeting scheduled for {request.meeting_date} at {request.meeting_time}", "meeting_id": str(meeting.id)}

@router.get("/{company_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = (
        select(CompanyComment, User.name)
        .join(User, CompanyComment.user_id == User.id)
        .where(CompanyComment.company_id == company_id)
        .order_by(CompanyComment.created_at.asc())
    )
    rows = await db.execute(stmt)
    comments = []
    for row in rows.all():
        comment, user_name = row
        comments.append(CommentResponse(
            id=comment.id,
            company_id=comment.company_id,
            user_id=comment.user_id,
            user_name=user_name,
            text=comment.text,
            created_at=comment.created_at
        ))
    return comments

@router.post("/{company_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    company_id: uuid.UUID,
    request: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    comment = CompanyComment(
        company_id=company_id,
        user_id=current_user.id,
        text=request.text
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        company_id=comment.company_id,
        user_id=comment.user_id,
        user_name=current_user.name,
        text=comment.text,
        created_at=comment.created_at
    )

@router.delete("/{company_id}/comments/{comment_id}")
async def delete_comment(
    company_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    result = await db.execute(select(CompanyComment).where(CompanyComment.id == comment_id, CompanyComment.company_id == company_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if current_user.role not in ("admin", "lead") and comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(comment)
    await db.commit()
    return {"message": "Comment deleted"}

@router.patch("/{company_id}/assign", response_model=CompanyResponse)
async def assign_company(
    company_id: uuid.UUID,
    request: AssignRequest,
    current_user: User = Depends(require_admin_or_lead),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.assigned_to = request.user_id
    await db.commit()
    await db.refresh(company)

    if request.user_id:
        assignee = await db.execute(select(User).where(User.id == request.user_id))
        assignee = assignee.scalar_one_or_none()
        if assignee:
            await notifier.notify_user_by_email(
                assignee.email,
                f"Вам назначена компания {company.name} (ИНН {company.inn})"
            )

    return company

@router.patch("/{company_id}/status", response_model=CompanyResponse)
async def update_company_status(
    company_id: uuid.UUID,
    request: StatusUpdateRequest,
    current_user: User = Depends(require_admin_or_lead),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.call_status = request.call_status
    await db.commit()
    await db.refresh(company)

    if request.call_status == "meeting":
        admins = await db.execute(
            select(User).where(User.role.in_(["admin", "lead"]), User.tg_chat_id != None)
        )
        for admin in admins.scalars().all():
            await notifier.send_message(
                admin.tg_chat_id,
                f"Назначена встреча с {company.name} (ИНН {company.inn})"
            )

    return company

@router.delete("/{company_id}")
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.is_deleted = True
    await db.commit()
    return {"message": "Company deleted"}

@router.post("/bulk-status", response_model=BulkStatusResponse)
async def bulk_update_status(
    request: BulkStatusRequest,
    current_user: User = Depends(require_admin_or_lead),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Company).where(
            Company.id.in_(request.company_ids),
            Company.is_deleted == False
        )
    )
    companies = result.scalars().all()

    if not companies:
        raise HTTPException(status_code=404, detail="No companies found")

    for company in companies:
        company.call_status = request.call_status

    await db.commit()
    return BulkStatusResponse(updated=len(companies))

@router.post("/export")
async def export_companies(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Company).where(
        Company.id.in_(request.company_ids),
        Company.is_deleted == False
    )

    if current_user.role == "manager":
        query = query.where(Company.assigned_to == current_user.id)

    result = await db.execute(query)
    companies = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    columns = [c.name for c in Company.__table__.columns]
    writer.writerow(columns)
    for company in companies:
        writer.writerow([getattr(company, c) for c in columns])

    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=companies.csv"}
    )


@router.post("/{company_id}/cp")
async def generate_company_cp(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.director:
        raise HTTPException(status_code=400, detail="Заполните поле «Руководитель»")
    if not company.lpr_phone:
        raise HTTPException(status_code=400, detail="Заполните поле «Номер ЛПР»")

    lpr_firstname = company.director.split()[0] if company.director.split() else ""
    buf = generate_cp(
        company_name=company.name or "",
        lpr_name=company.director,
        lpr_phone=company.lpr_phone,
        lpr_firstname=lpr_firstname,
    )

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in (company.name or "proposal"))
    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="CP_{safe_name}.docx"'},
    )


@router.post("/{company_id}/cp/send")
async def send_company_cp(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.director:
        raise HTTPException(status_code=400, detail="Заполните поле «Руководитель»")
    if not company.lpr_phone:
        raise HTTPException(status_code=400, detail="Заполните поле «Номер ЛПР»")
    if not company.lpr_email:
        raise HTTPException(status_code=400, detail="Заполните поле «Email ЛПР»")

    lpr_firstname = company.director.split()[0] if company.director.split() else ""
    html = generate_cp_html(
        company_name=company.name or "",
        lpr_name=company.director,
        lpr_phone=company.lpr_phone,
        lpr_firstname=lpr_firstname,
    )

    try:
        send_cp_email(
            recipient_email=company.lpr_email,
            html_body=html,
            company_name=company.name or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки email: {e}")

    return {"message": f"КП отправлено на {company.lpr_email}"}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
import uuid

from ..database import get_db
from ..models import User, Company, CallLog, AuditLog
from ..schemas import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse, CallLogCreate, CallLogResponse, AssignRequest
from ..auth import get_current_user, require_admin, require_admin_or_lead

router = APIRouter(prefix="/api/companies", tags=["companies"])

@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    region: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Company).where(Company.is_deleted == False)
    count_query = select(func.count()).select_from(Company).where(Company.is_deleted == False)
    
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
    
    query = query.order_by(Company.next_call_date.asc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    
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
    return call_log

@router.patch("/{company_id}/assign", response_model=CompanyResponse)
async def assign_company(
    company_id: uuid.UUID,
    request: AssignRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.assigned_to = request.user_id
    await db.commit()
    await db.refresh(company)
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

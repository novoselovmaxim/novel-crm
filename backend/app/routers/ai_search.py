"""AI search endpoints — enrich company data via Tavily."""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db, settings
from ..models import Company, User
from ..ai_search import search_company_info
from ..schemas import AiApplyRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])

def _has_value(val) -> bool:
    return val is not None and val != ""


@router.post("/search/{company_id}")
async def ai_search_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.tavily_api_key:
        raise HTTPException(status_code=400, detail="Tavily API key not configured")

    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    info = await search_company_info(
        name=company.name or "",
        inn=company.inn or "",
        website=company.website or company.focus_link or "",
    )

    auto_saved = []
    suggestions = {}

    def _try_autosave(field: str, current_val, new_val, label: str):
        if not _has_value(new_val):
            return
        if _has_value(current_val):
            if str(current_val).strip() != str(new_val).strip():
                suggestions[field] = {"current": current_val, "suggested": new_val, "label": label}
            return
        setattr(company, field, new_val)
        auto_saved.append(label)

    _try_autosave("website", company.website, info.get("website"), "Сайт")
    _try_autosave("email", company.email, info.get("email"), "Email компании")
    _try_autosave("activity_main", company.activity_main, info.get("activity"), "Деятельность")

    if company.phone:
        suggested_phone = info.get("phone")
        if suggested_phone and suggested_phone not in company.phone:
            suggestions["phone"] = {"current": company.phone, "suggested": suggested_phone, "label": "Телефон"}
    elif info.get("phone"):
        company.phone = info["phone"]
        auto_saved.append("Телефон")

    ai_suggestions = company.ai_suggestions or {}
    if suggestions:
        existing = ai_suggestions.get("pending", {})
        for field, val in suggestions.items():
            existing[field] = val
        ai_suggestions["pending"] = existing

    if info.get("description"):
        ai_suggestions["ai_summary"] = info["description"]

    if auto_saved or suggestions:
        company.ai_suggestions = ai_suggestions
        await db.commit()
        await db.refresh(company)

    from ..schemas import CompanyResponse
    return {
        "company_id": company_id,
        "auto_saved": auto_saved,
        "suggestions": suggestions,
        "ai_summary": info.get("description", ""),
        "has_pending": bool(suggestions),
        "sources": info.get("sources", []),
        "company": CompanyResponse.model_validate(company).model_dump(),
    }


@router.post("/apply/{company_id}")
async def ai_apply_field(
    company_id: uuid.UUID,
    request: AiApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    ai_suggestions = company.ai_suggestions or {}
    pending = ai_suggestions.get("pending", {})

    if request.field == "ai_summary":
        company.ai_summary = request.value
        ai_suggestions.pop("ai_summary", None)
    elif request.field in pending:
        setattr(company, request.field, request.value)
        del pending[request.field]
        ai_suggestions["pending"] = pending
    else:
        raise HTTPException(status_code=400, detail=f"No pending suggestion for '{request.field}'")


@router.post("/qualify/{company_id}")
async def ai_qualify_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.zveno_api_key:
        raise HTTPException(status_code=400, detail="ZVENO API key not configured")

    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from ..ai_qualify import qualify_company
    qualification = await qualify_company(company, db)

    ai_suggestions = company.ai_suggestions or {}
    ai_suggestions["qualification"] = qualification
    company.ai_suggestions = ai_suggestions
    await db.commit()
    await db.refresh(company)

    return {"company_id": company_id, "qualification": qualification}

    company.ai_suggestions = ai_suggestions if ai_suggestions else None
    await db.commit()
    await db.refresh(company)
    return {"message": f"Field '{request.field}' updated", "company": company}


@router.post("/reject/{company_id}")
async def ai_reject_field(
    company_id: uuid.UUID,
    request: AiApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    ai_suggestions = company.ai_suggestions or {}
    pending = ai_suggestions.get("pending", {})

    if request.field in pending:
        del pending[request.field]
        ai_suggestions["pending"] = pending
        company.ai_suggestions = ai_suggestions if ai_suggestions else None
        await db.commit()
        await db.refresh(company)
        return {"message": f"Suggestion for '{request.field}' rejected"}

    raise HTTPException(status_code=400, detail=f"No pending suggestion for '{request.field}'")

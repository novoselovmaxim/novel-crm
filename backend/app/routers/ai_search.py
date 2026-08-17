"""AI search endpoints — enrich company data via Tavily."""
import copy
import json
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

    suggestions = {}

    def _try_suggest(field: str, current_val, new_val, label: str, mode: str = "replace"):
        if not _has_value(new_val):
            return
        if _has_value(current_val):
            if mode == "add":
                if new_val not in current_val:
                    suggestions[field] = {"current": current_val, "suggested": new_val, "label": label, "mode": "add"}
                return
            if str(current_val).strip() != str(new_val).strip():
                suggestions[field] = {"current": current_val, "suggested": new_val, "label": label}
            return
        suggestions[field] = {"current": "", "suggested": new_val, "label": label}

    _try_suggest("website", company.website, info.get("website"), "Сайт")
    _try_suggest("activity_main", company.activity_main, info.get("activity"), "Деятельность")

    suggested_phone = info.get("phone")
    if suggested_phone:
        already = company.phone and any(
            suggested_phone.strip("+ ()-") in p.strip("+ ()-")
            for p in company.phone.split(",")
        )
        if not already:
            suggestions["phone"] = {
                "current": company.phone or "",
                "suggested": suggested_phone,
                "label": "Добавить номер" if company.phone else "Телефон",
                "mode": "add",
            }

    suggested_email = info.get("email")
    if suggested_email:
        already = company.email and suggested_email.lower() in company.email.lower()
        if not already:
            suggestions["email"] = {
                "current": company.email or "",
                "suggested": suggested_email,
                "label": "Добавить email" if company.email else "Email",
                "mode": "add",
            }

    ai_suggestions = copy.deepcopy(company.ai_suggestions) if company.ai_suggestions else {}
    if suggestions:
        existing = ai_suggestions.get("pending", {})
        for field, val in suggestions.items():
            existing[field] = val
        ai_suggestions["pending"] = existing

    if info.get("description"):
        ai_suggestions["ai_summary"] = info["description"]

    if suggestions:
        company.ai_suggestions = ai_suggestions
        await db.commit()
        await db.refresh(company)

    from ..schemas import CompanyResponse
    return {
        "company_id": company_id,
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
    logger.warning("Apply request: field=%s value=%s pending_keys=%s ai_suggestions=%s",
        request.field, request.value,
        list(pending.keys()),
        json.dumps(ai_suggestions, ensure_ascii=False, default=str)[:300])

    if request.field == "ai_summary":
        company.ai_summary = request.value
        ai_suggestions.pop("ai_summary", None)
    elif request.field in pending:
        suggestion = pending[request.field]
        mode = suggestion.get("mode", "replace")
        if mode == "add":
            existing = getattr(company, request.field) or ""
            if request.value not in existing:
                setattr(company, request.field, f"{existing}, {request.value}".lstrip(", "))
        else:
            setattr(company, request.field, request.value)
        del pending[request.field]
        ai_suggestions["pending"] = pending
    else:
        logger.warning("APPLY 400: field='%s' not in pending=%s", request.field, list(pending.keys()))
        raise HTTPException(status_code=400, detail=f"No pending suggestion for '{request.field}'")

    company.ai_suggestions = ai_suggestions if ai_suggestions else None
    await db.commit()
    await db.refresh(company)
    return {"message": f"Field '{request.field}' updated"}


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

    ai_suggestions = copy.deepcopy(company.ai_suggestions) if company.ai_suggestions else {}
    ai_suggestions["qualification"] = qualification
    company.ai_suggestions = ai_suggestions
    await db.commit()
    await db.refresh(company)

    return {"company_id": company_id, "qualification": qualification}


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

    ai_suggestions = copy.deepcopy(company.ai_suggestions) if company.ai_suggestions else {}
    pending = ai_suggestions.get("pending", {})

    if request.field in pending:
        del pending[request.field]
        ai_suggestions["pending"] = pending
        company.ai_suggestions = ai_suggestions if ai_suggestions else None
        await db.commit()
        await db.refresh(company)
        return {"message": f"Suggestion for '{request.field}' rejected"}

    raise HTTPException(status_code=400, detail=f"No pending suggestion for '{request.field}'")

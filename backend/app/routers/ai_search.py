"""AI search endpoints — enrich company data via Tavily."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db, settings
from ..models import Company, User
from ..ai_search import search_company_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


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

    updates = {}
    if info.get("website") and not company.website:
        updates["website"] = info["website"]
    if info.get("phone") and not company.phone:
        updates["phone"] = info["phone"]
    if info.get("activity") and not company.activity_main:
        updates["activity_main"] = info["activity"]

    enrichments = []
    for key, val in info.items():
        if val and key not in ("name", "inn", "sources", "website_content", "description"):
            enrichments.append(f"{key}: {val}")

    info["enrichments"] = enrichments
    info["summary"] = info.get("description", "")

    return {
        "company_id": company_id,
        "found_fields": info,
        "ai_summary": info.get("description", ""),
        "auto_updates": updates,
    }

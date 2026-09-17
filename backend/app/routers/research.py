"""Research endpoints — multi-source company investigation."""
import copy
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db, settings
from ..models import Company, User
from ..schemas import CompanyResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    sources: list[str] = ["brave", "exa", "zveno"]
    custom_query: str = ""


class FollowUpRequest(BaseModel):
    question: str
    context: str = ""


class SaveResearchRequest(BaseModel):
    suggestions: dict


@router.post("/{company_id}")
async def research_company_endpoint(
    company_id: uuid.UUID,
    request: ResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run multi-source company research."""
    available_sources = []
    if settings.brave_api_key:
        available_sources.append("brave")
    if settings.exa_api_key:
        available_sources.append("exa")
    if settings.zveno_api_key:
        available_sources.append("zveno")

    requested = [s for s in request.sources if s in available_sources]
    if not requested:
        raise HTTPException(
            status_code=400,
            detail=f"No sources configured. Available: {', '.join(available_sources)}",
        )

    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from ..services.search_engine import research_company

    research = await research_company(
        name=company.name or "",
        inn=company.inn or "",
        website=company.website or company.focus_link or "",
        custom_query=request.custom_query,
        sources=requested,
    )

    # Build suggestions from extracted data
    suggestions = {}
    extracted = research.get("extracted_data", {})

    def _try_suggest(field, current_val, new_val, label, mode="replace"):
        if not new_val:
            return
        if current_val:
            if mode == "add":
                if new_val not in current_val:
                    suggestions[field] = {
                        "current": current_val,
                        "suggested": new_val,
                        "label": label,
                        "mode": "add",
                    }
                return
            if str(current_val).strip() != str(new_val).strip():
                suggestions[field] = {
                    "current": current_val,
                    "suggested": new_val,
                    "label": label,
                }
            return
        suggestions[field] = {"current": "", "suggested": new_val, "label": label}

    _try_suggest("website", company.website, extracted.get("website"), "Сайт")
    _try_suggest(
        "activity_main", company.activity_main, extracted.get("activity"), "Деятельность"
    )

    suggested_phone = extracted.get("phone")
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

    suggested_email = extracted.get("email")
    if suggested_email:
        already = company.email and suggested_email.lower() in company.email.lower()
        if not already:
            suggestions["email"] = {
                "current": company.email or "",
                "suggested": suggested_email,
                "label": "Добавить email" if company.email else "Email",
                "mode": "add",
            }

    # Store suggestions
    ai_suggestions = copy.deepcopy(company.ai_suggestions) if company.ai_suggestions else {}
    if suggestions:
        existing = ai_suggestions.get("pending", {})
        for field, val in suggestions.items():
            existing[field] = val
        ai_suggestions["pending"] = existing

    if extracted.get("description"):
        ai_suggestions["ai_summary"] = extracted["description"]

    if suggestions:
        company.ai_suggestions = ai_suggestions
        await db.commit()
        await db.refresh(company)

    return {
        "company_id": company_id,
        "suggestions": suggestions,
        "ai_summary": extracted.get("description", ""),
        "has_pending": bool(suggestions),
        "sources": research.get("sources", []),
        "brave_results": research.get("brave_results", []),
        "exa_results": research.get("exa_results", []),
        "zveno_answer": research.get("zveno_answer", ""),
        "zveno_results": research.get("zveno_results", []),
        "scraped_texts": research.get("scraped_texts", []),
        "all_urls": research.get("all_urls", []),
        "raw_text_preview": research.get("raw_text_preview", ""),
        "company": CompanyResponse.model_validate(company).model_dump(),
    }


@router.post("/{company_id}/follow-up")
async def research_follow_up(
    company_id: uuid.UUID,
    request: FollowUpRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Answer a follow-up question about company research results using GPT."""
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    context = request.context or f"Компания: {company.name}, ИНН: {company.inn}"
    if company.activity_main:
        context += f"\nДеятельность: {company.activity_main}"
    if company.description:
        context += f"\nОписание: {company.description}"

    prompt = f"""Ты аналитик по компаниям. Ответь на вопрос, опираясь на контекст.

Контекст:
{context}

Вопрос: {request.question}

Ответь кратко и по существу на русском языке. Если данных недостаточно — скажи об этом."""

    try:
        from ..ai_search import _extract_with_gpt
        # Use GPT to generate follow-up answer
        client = None
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        except Exception:
            pass

        if client:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            answer = resp.choices[0].message.content or "Не удалось получить ответ"
        else:
            answer = "OpenAI API key не настроен"

        return {"answer": answer, "question": request.question}
    except Exception as e:
        logger.exception("Follow-up failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{company_id}/save")
async def save_research_data(
    company_id: uuid.UUID,
    request: SaveResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save research data to company fields."""
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    updated_fields = []
    for field, value in request.suggestions.items():
        if not value:
            continue
        current_val = getattr(company, field, None)
        if field == "phone" and current_val:
            if value not in current_val:
                setattr(company, field, f"{current_val}, {value}")
                updated_fields.append(field)
        elif field == "email" and current_val:
            if value.lower() not in current_val.lower():
                setattr(company, field, f"{current_val}, {value}")
                updated_fields.append(field)
        else:
            if str(current_val or "").strip() != str(value).strip():
                setattr(company, field, value)
                updated_fields.append(field)

    if updated_fields:
        # Clear pending suggestions for saved fields
        ai_suggestions = copy.deepcopy(company.ai_suggestions) if company.ai_suggestions else {}
        pending = ai_suggestions.get("pending", {})
        for field in updated_fields:
            pending.pop(field, None)
        ai_suggestions["pending"] = pending
        company.ai_suggestions = ai_suggestions
        await db.commit()
        await db.refresh(company)

    return {
        "updated_fields": updated_fields,
        "company": CompanyResponse.model_validate(company).model_dump(),
    }

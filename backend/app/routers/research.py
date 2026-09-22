"""Research endpoints -- multi-source company investigation."""
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
from ..services.search_engine import research_company
from ..ai_search import search_company_info
from ..ai_qualify import qualify_company

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

# Field allowlist for save operations
ALLOWED_FIELDS = ["website", "phone", "email", "activity_main", "ai_summary"]


class ResearchRequest(BaseModel):
    sources: list[str] = ["brave", "exa"]
    custom_query: str = ""


class FollowUpRequest(BaseModel):
    question: str
    context: str = ""


class SaveResearchRequest(BaseModel):
    suggestions: dict


def _filter_suggestions_by_validation(suggestions: dict, validation: dict) -> dict:
    """Filter out suggestions that TypeSafe validation flagged as unreliable."""
    if not validation:
        return suggestions
    
    field_validation_map = {
        "website": "website_is_official",
        "phone": "phone_is_direct",
        "email": "email_is_business",
        "activity_main": "activity_matches_okved",
    }
    
    filtered = {}
    for field, suggestion in suggestions.items():
        validation_key = field_validation_map.get(field)
        if validation_key and validation_key in validation:
            val = validation[validation_key]
            # Only keep suggestions where validation passed (answer >= 0.5 and not needs_review)
            answer = val.get("answer", 0)
            needs_review = val.get("needs_review", True)
            if answer >= 0.5 and not needs_review:
                filtered[field] = suggestion
            else:
                logger.info("Filtered out suggestion for %s due to validation: answer=%.2f, needs_review=%s", 
                           field, answer, needs_review)
        else:
            # No validation for this field - keep it
            filtered[field] = suggestion
    return filtered


@router.post("/{company_id}")
async def research_company_endpoint(
    company_id: uuid.UUID,
    request: ResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run multi-source company research with validation."""
    available_sources = []
    if settings.brave_api_key:
        available_sources.append("brave")
    if settings.exa_api_key:
        available_sources.append("exa")

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

    # Use multi-source research (Brave + Exa + Scraping)
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

    # Run TypeSafe validation on extracted data
    validation = {}
    try:
        from ..ai_search import search_company_info
        validation_info = await search_company_info(
            name=company.name or "",
            inn=company.inn or "",
            website=company.website or company.focus_link or "",
            region=company.region or "",
            okved=company.activity_code or "",
            revenue=company.revenue or 0,
            employees=company.employees or 0,
        )
        if validation_info.get("validation"):
            validation = validation_info["validation"]
            ai_suggestions["validation"] = validation
    except Exception as e:
        logger.warning("TypeSafe validation failed in research: %s", e)

    # Filter suggestions based on TypeSafe validation
    filtered_suggestions = _filter_suggestions_by_validation(suggestions, validation)

    if filtered_suggestions or extracted.get("description"):
        company.ai_suggestions = ai_suggestions
        await db.commit()
        await db.refresh(company)

    # Run qualification (ВЭД check)
    qualification = await qualify_company(company, db)

    return {
        "company_id": company_id,
        "suggestions": filtered_suggestions,
        "ai_summary": extracted.get("description", ""),
        "has_pending": bool(filtered_suggestions),
        "validation": validation,
        "qualification": qualification,
        "sources": research.get("sources", []),
        "brave_results": research.get("brave_results", []),
        "exa_results": research.get("exa_results", []),
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
    """Answer a follow-up question about company research results."""
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    context = request.context or f"Компания: {company.name}, ИНН: {company.inn}"
    if company.activity_main:
        context += f"\nДеятельность: {company.activity_main}"
    if company.ai_summary:
        context += f"\nОписание: {company.ai_summary}"

    if not settings.zveno_api_key:
        return {
            "answer": "AI-функция недоступна (ZVENO API key не настроен). "
                      "Используйте данные из исследования: Brave результаты, Exa, скрейпинг сайтов. "
                      "Вопрос: " + request.question,
            "question": request.question
        }

    prompt = f"""Ты аналитик по компаниям. Ответь на вопрос, опираясь на контекст.

Контекст:
{context}

Вопрос: {request.question}

Ответь кратко и по существу на русском языке. Если данных недостаточно -- скажи об этом."""

    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as c:
            payload = {
                "model": settings.llm_model_qualify,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.3,
            }
            resp = await c.post(
                f"{settings.zveno_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.zveno_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            data = resp.json()
            if "choices" in data and data["choices"]:
                answer = data["choices"][0]["message"]["content"] or "Не удалось получить ответ"
            else:
                logger.warning("ZVENO follow-up failed: %s", json.dumps(data, ensure_ascii=False)[:300])
                answer = f"ZVENO error: {data.get('error', {}).get('message', 'Unknown error')}"
    except Exception as e:
        logger.exception("Follow-up failed")
        answer = f"Ошибка вызова AI: {str(e)}"

    return {"answer": answer, "question": request.question}


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

    # Enforce field allowlist
    invalid_fields = [f for f in request.suggestions.keys() if f not in ALLOWED_FIELDS]
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Fields not allowed for update: {', '.join(invalid_fields)}. Allowed: {', '.join(ALLOWED_FIELDS)}"
        )

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
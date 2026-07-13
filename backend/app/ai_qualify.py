"""Lead qualification — does this company do ВЭД?"""
import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .database import settings
from .models import Company

logger = logging.getLogger(__name__)

QUALIFY_SYSTEM_PROMPT = """Ты — эксперт по ВЭД (внешнеэкономической деятельности). 
Проанализируй компанию и определи, занимается ли она внешнеэкономической деятельностью, 
является ли импортёром или экспортёром, работает ли с зарубежными партнёрами, 
осуществляет ли валютные платежи.

Оцени пригодность компании как потенциального клиента для сервиса международных 
валютных переводов (аналог Wise/Revolut для бизнеса в РФ).

Ответь строго в формате JSON без markdown-обёртки:
{
  "score": 0-100,
  "has_ved": true/false/null,
  "is_importer": true/false/null,
  "is_exporter": true/false/null,
  "has_foreign_payments": true/false/null,
  "has_international_partners": true/false/null,
  "reasoning": "Подробное объяснение вывода на русском",
  "evidence": ["Короткий факт 1", "Короткий факт 2"],
  "needs_review": true/false
}

Где:
- score — общая оценка likelihood (0 = точно не ВЭД, 100 = идеальный клиент)
- has_ved — занимается ли ВЭД в принципе
- needs_review — true если данных недостаточно и нужно вмешательство человека
- evidence — конкретные факты из данных компании или поиска
"""


async def qualify_company(
    company: Company,
    db: AsyncSession,
) -> dict:
    """Run qualification: gather data + search + LLM analysis."""
    result = {
        "score": 0,
        "has_ved": None,
        "is_importer": None,
        "is_exporter": None,
        "has_foreign_payments": None,
        "has_international_partners": None,
        "reasoning": "",
        "evidence": [],
        "needs_review": True,
    }

    # — 1. Gather existing company data —
    company_data_lines = [
        f"Название: {company.name}",
        f"ИНН: {company.inn}",
        f"Регион: {company.region}",
        f"Основной вид деятельности: {company.activity_main or '—'}",
        f"Доп. деятельность: {company.activity_other or '—'}",
        f"Выручка: {company.revenue or '—'}",
        f"Сотрудники: {company.employees or '—'}",
        f"Обороты импорта: {company.import_turnover or '—'}",
        f"Обороты экспорта: {company.export_turnover or '—'}",
        f"Подтверждённый импорт: {company.import_confirmed or '—'}",
        f"Валютные платежи: {company.foreign_payments or '—'}",
        f"Предмет снабжения: {company.supply_subject or '—'}",
    ]

    # — 2. Search via Tavily —
    search_results = []
    ved_keywords = [
        f"{company.name} {company.inn} ВЭД импорт экспорт",
        f"{company.name} {company.inn} внешнеэкономическая деятельность валютные платежи",
    ]

    if settings.tavily_api_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            for q in ved_keywords:
                sr = client.search(
                    query=q,
                    search_depth="advanced",
                    max_results=3,
                    include_answer=False,
                )
                for item in sr.get("results", []):
                    snippet = f"{item.get('title', '')}: {item.get('content', '')[:300]}"
                    if snippet not in search_results:
                        search_results.append(snippet)
        except Exception:
            logger.exception("Tavily search failed for qualification")

    company_text = "\n".join(company_data_lines)
    search_text = "\n".join(search_results[:5]) if search_results else "Результаты поиска недоступны"

    # — 3. Call ZVENO —
    if not settings.zveno_api_key:
        result["reasoning"] = "ZVENO API key not configured"
        return result

    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as c:
            payload = {
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": QUALIFY_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"=== Данные компании ===\n{company_text}\n\n=== Результаты веб-поиска ===\n{search_text}",
                    },
                ],
                "temperature": 0.1,
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
            logger.info("ZVENO response status=%s body=%s", resp.status_code, json.dumps(data, ensure_ascii=False)[:500])
            if "choices" in data:
                content = data["choices"][0]["message"]["content"].strip()
                content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(content)
                result.update(parsed)
            elif "error" in data:
                result["reasoning"] = f"ZVENO error: {data['error']}"
            else:
                result["reasoning"] = f"Неожиданный ответ ZVENO: {json.dumps(data, ensure_ascii=False)[:300]}"
    except Exception:
        logger.exception("ZVENO qualification call failed")
        result["reasoning"] = "Ошибка вызова AI для квалификации"

    return result

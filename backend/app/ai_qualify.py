"""Lead qualification -- does this company do ВЭД?

Works without LLM by analyzing company data fields.
"""
import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .database import settings
from .models import Company

logger = logging.getLogger(__name__)

VED_KEYWORDS_IMPORT = [
    "импорт", "import", "ввоза", "закупк", "покупк за границ",
    "поставк из", "закупаю", "ввожу", "таможен", "customs",
    "форекс", "валютн", "перевод за границ", "swift", "сепа",
]

VED_KEYWORDS_EXPORT = [
    "экспорт", "export", "вывоз", "продаж за границ", "поставк за границ",
    "клиент за границ", "покупател за границ", "международн",
    "форекс", "валютн", "перевод из за границ",
]

VED_KEYWORDS_ACTIVITY = [
    "внешнеэкономическ", "вэд", "международн", "foreign trade",
    "таможен", "брокер", "переводчик", "логистик", "перевозк",
    "форекс", "депозитар", "банк", "платежн", "payment",
]


async def qualify_company(
    company: Company,
    db: AsyncSession,
) -> dict:
    """Run qualification by analyzing company data fields.
    
    No external LLM needed - uses heuristics on existing data.
    """
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

    score = 0
    evidence = []
    has_ved = False
    is_importer = False
    is_exporter = False
    has_foreign_payments = False
    has_international_partners = False

    # 1. Check explicit VED fields
    if company.import_turnover and company.import_turnover > 0:
        has_ved = True
        is_importer = True
        score += 30
        evidence.append(f"Обороты импорта: {company.import_turnover:,.0f} руб.")
    
    if company.export_turnover and company.export_turnover > 0:
        has_ved = True
        is_exporter = True
        score += 30
        evidence.append(f"Обороты экспорта: {company.export_turnover:,.0f} руб.")
    
    if company.import_confirmed and company.import_confirmed > 0:
        has_ved = True
        is_importer = True
        score += 20
        evidence.append(f"Подтверждённый импорт: {company.import_confirmed:,.0f} руб.")

    if company.foreign_payments and company.foreign_payments > 0:
        has_ved = True
        has_foreign_payments = True
        score += 25
        evidence.append(f"Валютные платежи: {company.foreign_payments:,.0f} руб.")

    # 2. Check supply_subject for VED keywords
    if company.supply_subject:
        subj_lower = company.supply_subject.lower()
        for kw in VED_KEYWORDS_IMPORT:
            if kw in subj_lower:
                is_importer = True
                has_ved = True
                score += 10
                evidence.append(f"Предмет снабжения (импорт): {company.supply_subject[:100]}")
                break
        for kw in VED_KEYWORDS_EXPORT:
            if kw in subj_lower:
                is_exporter = True
                has_ved = True
                score += 10
                evidence.append(f"Предмет снабжения (экспорт): {company.supply_subject[:100]}")
                break

    # 3. Check activity_main for VED-related keywords
    if company.activity_main:
        act_lower = company.activity_main.lower()
        for kw in VED_KEYWORDS_ACTIVITY:
            if kw in act_lower:
                has_ved = True
                score += 15
                evidence.append(f"Деятельность содержит '{kw}': {company.activity_main[:100]}")
                break

    if company.activity_other:
        act_lower = company.activity_other.lower()
        for kw in VED_KEYWORDS_ACTIVITY:
            if kw in act_lower:
                has_ved = True
                score += 10
                evidence.append(f"Доп. деятельность содержит '{kw}': {company.activity_other[:100]}")
                break

    # 4. Check revenue scale (larger companies more likely to do VED)
    if company.revenue and company.revenue > 0:
        if company.revenue > 100_000_000:  # > 100M
            score += 10
            evidence.append(f"Высокая выручка: {company.revenue:,.0f} руб.")
        elif company.revenue > 10_000_000:  # > 10M
            score += 5
            evidence.append(f"Выручка: {company.revenue:,.0f} руб.")

    # 5. Check employees
    if company.employees and company.employees > 50:
        score += 5
        evidence.append(f"Команда: {company.employees} чел.")

    # 6. Determine final flags
    result["score"] = min(score, 100)
    result["has_ved"] = has_ved
    result["is_importer"] = is_importer if is_importer else (None if not has_ved else False)
    result["is_exporter"] = is_exporter if is_exporter else (None if not has_ved else False)
    result["has_foreign_payments"] = has_foreign_payments if has_foreign_payments else (None if not has_ved else False)
    result["has_international_partners"] = has_international_partners
    result["evidence"] = evidence[:5]  # top 5

    if has_ved:
        result["reasoning"] = "Компания имеет признаки ВЭД деятельности: " + "; ".join(evidence[:3])
        result["needs_review"] = False
    else:
        result["reasoning"] = "Прямых признаков ВЭД в данных не найдено. Рекомендуется ручная проверка."
        result["needs_review"] = True

    logger.info("Qualification result: score=%d, has_ved=%s, evidence=%s", result["score"], result["has_ved"], evidence)
    return result
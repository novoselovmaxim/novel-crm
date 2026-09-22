import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..database import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    field: str
    question_type: str
    answer: Any
    confidence: Optional[float] = None
    needs_review: bool = False


class TypeSafeClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.typesafe_api_key
        self.base_url = base_url or settings.typesafe_base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from typesafe_sdk import TypeSafeClient as SDKClient
                self._client = SDKClient(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise RuntimeError("typesafe-sdk not installed. Run: pip install typesafe-sdk")
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def validate_company_data(
        self,
        company_name: str,
        inn: str,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        activity: Optional[str] = None,
        region: Optional[str] = None,
        okved: Optional[str] = None,
        revenue: Optional[int] = None,
        employees: Optional[int] = None,
    ) -> List[ValidationResult]:
        if not self.is_configured():
            logger.warning("TypeSafe API key not configured, skipping validation")
            return []

        state_parts = [
            f"Компания: {company_name}",
            f"ИНН: {inn}",
        ]
        if region:
            state_parts.append(f"Регион: {region}")
        if okved:
            state_parts.append(f"ОКВЭД: {okved}")
        if revenue:
            state_parts.append(f"Выручка: {revenue:,}")
        if employees:
            state_parts.append(f"Сотрудники: {employees}")
        if website:
            state_parts.append(f"Сайт: {website}")
        if phone:
            state_parts.append(f"Телефон: {phone}")
        if email:
            state_parts.append(f"Email: {email}")
        if activity:
            state_parts.append(f"Деятельность: {activity}")

        state = "\n".join(state_parts)

        questions = {}

        if website:
            questions["website_is_company_site"] = {
                "type": "noul",
                "instructions": "Это официальный сайт компании, а не агрегатор, каталог или справочник (например, не rusprofile, list-org, 2gis, sbis, egrul, msp, zapros)?"
            }
            questions["website_matches_company"] = {
                "type": "noul",
                "instructions": "Содержимое страницы соответствует указанной компании (название, ИНН, деятельность)?"
            }

        if phone:
            questions["phone_is_direct"] = {
                "type": "noul",
                "instructions": "Это прямой телефон компании, а не телефон агрегатора, колл-центра или справочника?"
            }
            if region:
                questions["phone_region_match"] = {
                    "type": "noul",
                    "instructions": f"Код региона в телефоне ({phone}) соответствует региону регистрации компании ({region})?"
                }

        if email and website:
            questions["email_matches_domain"] = {
                "type": "noul",
                "instructions": f"Email ({email}) принадлежит домену сайта компании ({website})?"
            }

        if activity and okved:
            questions["activity_matches_okved"] = {
                "type": "noul",
                "instructions": f"Описание деятельности ('{activity}') соответствует коду ОКВЭД ({okved})?"
            }

        if revenue and employees:
            questions["data_consistency"] = {
                "type": "noul",
                "instructions": f"Для выручки {revenue:,} и {employees} сотрудников такая деятельность ('{activity or 'не указана'}') выглядит логично и консистентно?"
            }

        if questions:
            questions["overall_completeness"] = {
                "type": "score",
                "instructions": "Оцените полноту и достоверность всех данных от 1 до 10",
                "criteria": [
                    {"score": 1, "label": "Неполные/противоречивы", "description": "Данные неполные или противоречивы"},
                    {"score": 5, "label": "Базовые есть, есть сомнения", "description": "Базовые данные есть, есть сомнения в качестве"},
                    {"score": 10, "label": "Полные и достоверные", "description": "Данные полные, консистентные, достоверные"},
                ]
            }

        if not questions:
            return []

        try:
            client = self._get_client()
            response = client.system_one(
                state=state,
                model="jev-latest",
                questions=questions,
            )

            results = []
            for qid, answer in response.answers.items():
                confidence = getattr(answer, 'confidence', None)
                value = None

                if hasattr(answer, 'noul') and answer.noul is not None:
                    value = answer.noul
                elif hasattr(answer, 'choice') and answer.choice:
                    value = answer.choice
                elif hasattr(answer, 'score') and answer.score is not None:
                    value = answer.score

                needs_review = False
                if confidence is not None:
                    needs_review = confidence < 0.7

                results.append(ValidationResult(
                    field=qid,
                    question_type=answer.type if hasattr(answer, 'type') else 'unknown',
                    answer=value,
                    confidence=confidence,
                    needs_review=needs_review,
                ))

            return results

        except Exception as e:
            logger.error(f"TypeSafe validation error: {e}")
            return []


async def validate_company_data(
    company_name: str,
    inn: str,
    website: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    activity: Optional[str] = None,
    region: Optional[str] = None,
    okved: Optional[str] = None,
    revenue: Optional[int] = None,
    employees: Optional[int] = None,
) -> List[ValidationResult]:
    client = TypeSafeClient()
    return await client.validate_company_data(
        company_name=company_name,
        inn=inn,
        website=website,
        phone=phone,
        email=email,
        activity=activity,
        region=region,
        okved=okved,
        revenue=revenue,
        employees=employees,
    )
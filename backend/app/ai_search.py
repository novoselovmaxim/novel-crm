"""AI-powered company search using Tavily."""
import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .database import settings

logger = logging.getLogger(__name__)


def _extract_text_from_html(html: str, max_chars: int = 5000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


async def search_company_info(name: str, inn: str = "", website: str = "") -> dict:
    """Search for company info using Tavily + optional website scrape.
    Returns enriched data about the company."""
    result = {
        "name": name,
        "inn": inn,
        "website": website or "",
        "description": "",
        "phone": "",
        "email": "",
        "region": "",
        "activity": "",
        "revenue_hint": "",
        "employees_hint": "",
        "sources": [],
    }

    if not settings.tavily_api_key:
        result["description"] = "Tavily API key not configured"
        return result

    query = f"{name} {inn} компания деятельность отзывы".strip()
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        search_result = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
        )
    except Exception:
        logger.exception("Tavily search failed, falling back to httpx")

        try:
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.get(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_answer": True,
                    },
                )
                search_result = resp.json()
        except Exception:
            logger.exception("Tavily fallback also failed")
            result["description"] = "Search unavailable"
            return result

    answer = search_result.get("answer", "")
    if answer:
        result["description"] = answer

    for item in search_result.get("results", []):
        url = item.get("url", "")
        title = item.get("title", "")
        content = item.get("content", "")
        result["sources"].append({"url": url, "title": title, "snippet": content[:300]})

        if not result["website"] and url:
            domain = re.search(r"https?://([^/]+)", url)
            if domain and "tavily" not in domain.group(1) and "google" not in domain.group(1):
                result["website"] = f"https://{domain.group(1)}"

        if content:
            text = content.lower()
            phone_match = re.search(r"\+?7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", content)
            if phone_match and not result["phone"]:
                result["phone"] = phone_match.group(0)
            email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.+-]+", content)
            if email_match and not result["email"]:
                result["email"] = email_match.group(0)

    if result["website"]:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
                resp = await c.get(
                    result["website"],
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    text = _extract_text_from_html(resp.text)
                    result["website_content"] = text[:2000]
                    activity_match = re.search(
                        r"(?:деятельность|услуги|направление|сфера|специализация)\s*[:\-]?\s*([^.\n]{10,200})",
                        text, re.IGNORECASE,
                    )
                    if activity_match and not result["activity"]:
                        result["activity"] = activity_match.group(1).strip()
        except Exception:
            logger.info(f"Could not scrape {result['website']}")

    return result


def format_ai_result(data: dict) -> str:
    lines = [f"🔍 {data['name']} (ИНН {data['inn']})"]
    if data.get("description"):
        lines.append(f"\n📝 {data['description']}")
    if data.get("website"):
        lines.append(f"\n🌐 Сайт: {data['website']}")
    if data.get("phone"):
        lines.append(f"📞 {data['phone']}")
    if data.get("email"):
        lines.append(f"✉️ {data['email']}")
    if data.get("activity"):
        lines.append(f"📋 Деятельность: {data['activity']}")
    if data.get("sources"):
        lines.append(f"\nИсточники ({len(data['sources'])}):")
        for s in data["sources"][:5]:
            lines.append(f"  • {s['title']}")
    return "\n".join(lines)

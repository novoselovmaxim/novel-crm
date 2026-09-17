"""Exa Search API client.

Docs: https://docs.exa.ai
Best-in-class company search (62% accuracy in benchmarks).
"""
import logging

import httpx

from ..database import settings

logger = logging.getLogger(__name__)

EXA_BASE = "https://api.exa.ai"


async def search_exa_company(
    name: str,
    inn: str = "",
    query: str = "",
    num_results: int = 10,
) -> dict:
    """Semantic company search via Exa.

    Returns: {"results": [{"title", "url", "text", "score"}], "query": str}
    """
    if not settings.exa_api_key:
        logger.info("Exa API key not configured, skipping")
        return {"results": [], "query": query}

    search_query = query or f"{name} {inn} официальный сайт контакты руководство"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{EXA_BASE}/search",
                headers={
                    "x-api-key": settings.exa_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": search_query,
                    "numResults": num_results,
                    "type": "neural",
                    "contents": {
                        "text": {"maxCharacters": 2000},
                    },
                    "excludeDomains": [
                        "rusprofile.com",
                        "list-org.com",
                        "sbis.ru",
                        "checko.ru",
                        "2gis.ru",
                        "yandex.ru",
                        "google.ru",
                        "google.com",
                    ],
                },
            )
            if resp.status_code != 200:
                logger.warning("Exa search error %s: %s", resp.status_code, resp.text[:200])
                return {"results": [], "query": search_query, "error": resp.text[:200]}
            data = resp.json()
            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "text": r.get("text", ""),
                    "publishedDate": r.get("publishedDate", ""),
                    "score": r.get("score", 0),
                })
            return {"results": results, "query": search_query}
    except Exception:
        logger.exception("Exa search failed")
        return {"results": [], "query": search_query}


async def search_exa_contacts(name: str) -> dict:
    """Search for company contacts/decision makers via Exa."""
    return await search_exa_company(
        name=name,
        query=f"{name} руководитель директор контакт телефон email LinkedIn",
        num_results=5,
    )

"""Brave Search API client.

Docs: https://api-dashboard.search.brave.com/documentation/web-search
Free tier: $5/month credits (~1000 queries).
"""
import logging

import httpx

from ..database import settings

logger = logging.getLogger(__name__)

BRAVE_BASE = "https://api.search.brave.com/res/v1"


async def search_brave_web(query: str, count: int = 10) -> dict:
    """Web search via Brave API.

    Returns: {"results": [{"title", "url", "description", "age"}], "query": str}
    """
    if not settings.brave_api_key:
        logger.info("Brave API key not configured, skipping")
        return {"results": [], "query": query}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BRAVE_BASE}/web/search",
                headers={"X-Subscription-Token": settings.brave_api_key},
                params={
                    "q": query,
                    "count": count,
                    "country": "ru",
                    "search_lang": "ru",
                },
            )
            if resp.status_code != 200:
                logger.warning("Brave search error %s: %s", resp.status_code, resp.text[:200])
                return {"results": [], "query": query, "error": resp.text[:200]}
            data = resp.json()
            results = []
            for r in data.get("web", {}).get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                    "age": r.get("age", ""),
                })
            return {"results": results, "query": query}
    except Exception:
        logger.exception("Brave search failed")
        return {"results": [], "query": query}


async def search_brave_news(query: str, count: int = 5) -> dict:
    """Search news about a company via Brave."""
    if not settings.brave_api_key:
        return {"results": []}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BRAVE_BASE}/news/search",
                headers={"X-Subscription-Token": settings.brave_api_key},
                params={
                    "q": query,
                    "count": count,
                    "country": "ru",
                    "search_lang": "ru",
                },
            )
            if resp.status_code != 200:
                return {"results": []}
            data = resp.json()
            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                    "age": r.get("age", ""),
                })
            return {"results": results}
    except Exception:
        logger.exception("Brave news search failed")
        return {"results": []}

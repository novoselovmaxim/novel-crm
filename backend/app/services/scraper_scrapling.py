"""Scrapling-based scraper — anti-bot web scraping.

Replaces the basic httpx scraping in ai_search.py with Scrapling's
StealthyFetcher that handles Cloudflare, CAPTCHAs, and anti-bot systems.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _extract_text_from_html(html: str, max_chars: int = 5000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


async def scrape_url(url: str, timeout: int = 15) -> str:
    """Scrape a single URL, trying Scrapling first then falling back to httpx."""
    # Try Scrapling StealthyFetcher
    try:
        from scrapling import StealthyFetcher
        fetcher = StealthyFetcher()
        response = await fetcher.fetch(url, timeout=timeout)
        if response.status == 200:
            text = response.markdown()[:5000]
            if text and len(text) > 100:
                return text
    except ImportError:
        logger.debug("Scrapling not installed, using httpx fallback")
    except Exception as e:
        logger.debug("Scrapling failed for %s: %s", url, str(e)[:100])

    # Fallback: httpx + BeautifulSoup
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            resp = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                return _extract_text_from_html(resp.text, max_chars=5000)
    except Exception:
        logger.debug("httpx fallback also failed for %s", url)
    return ""


async def scrape_company_sites(urls: list[str]) -> list[str]:
    """Scrape multiple company URLs in parallel."""
    import asyncio
    if not urls:
        return []
    results = await asyncio.gather(
        *[scrape_url(u) for u in urls[:5]],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, str) and r]

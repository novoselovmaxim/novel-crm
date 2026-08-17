"""Multi-source AI company search with LLM extraction.

Flow:
  1. Tavily search
  2. DuckDuckGo search (free, no API key needed)
  3. Scrape top URLs from all sources
  4. Send all raw data → ZVENO GPT for structured extraction
  5. Fallback to regex extraction if GPT unavailable
"""
import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .database import settings

logger = logging.getLogger(__name__)

AGGREGATOR_DOMAINS = frozenset({
    "zachestnyibiznes", "list-org", "rusprofile", "sbis", "sbisru",
    "nalog", "e-nalog", "yandex", "google", "tavily",
    "vk", "facebook", "2gis", "spark", "spark-interfax",
    "kontragent", "audit-it", "rusbk", "rsprime", "fedresurs",
    "kontur", "focus-kontur", "focus",
})

EXTRACT_SYSTEM_PROMPT = """Ты — помощник по извлечению структурированных данных о компаниях.
Из сырых результатов веб-поиска определи точные данные компании.

Верни JSON без markdown-обёртки:
{
  "website": "официальный сайт компании или пустая строка",
  "phone": "контактный телефон компании или пустая строка",
  "email": "контактный email компании или пустая строка",
  "activity": "основной вид деятельности (30-100 символов) или пустая строка",
  "description": "краткое описание компании (1-3 предложения) или пустая строка"
}

Правила:
1. Сайт — только реальный домен компании (.ru/.com/.рф). Не aggregator, не каталог, не страница соцсети.
2. Телефон — только прямой номер компании, не техподдержка aggregator'а.
3. Email — только контактный email компании.
4. Деятельность — коротко, суть: "Производство удобрений", "IT-услуги" и т.п.
5. Если не уверен — оставь поле пустым. Лучше пусто, чем неверно."""


def _is_company_domain(domain: str) -> bool:
    domain = domain.lower().removeprefix("www.")
    for agg in AGGREGATOR_DOMAINS:
        if agg in domain:
            return False
    parts = domain.split(".")
    if len(parts) < 2:
        return False
    tld = parts[-1]
    return tld in ("ru", "com", "net", "org", "su", "рф", "info", "biz", "pro")


def _extract_text_from_html(html: str, max_chars: int = 5000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def _deduplicate_urls(urls: list[str]) -> list[str]:
    seen = set()
    result = []
    for url in urls:
        domain = re.sub(r"https?://(www\.)?", "", url).rstrip("/").lower()
        if domain not in seen:
            seen.add(domain)
            result.append(url)
    return result


def _search_tavily(query: str) -> dict:
    """Run Tavily search. Returns dict with answer + results list."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=settings.tavily_api_key)
    return client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=True,
    )


def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """Run DuckDuckGo search. Returns list of {title, href, body}."""
    try:
        from duckduckgo_search import DDGS
        results = []
        for r in DDGS().text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "href": r.get("href", ""),
                "body": r.get("body", ""),
            })
        return results
    except Exception:
        logger.exception("DuckDuckGo search failed")
        return []


async def _scrape_url(url: str, timeout: int = 10) -> str:
    """Scrape a single URL and return clean text."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            resp = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                return _extract_text_from_html(resp.text, max_chars=3000)
    except Exception:
        logger.info("Could not scrape %s", url)
    return ""


async def _extract_with_gpt(raw_text: str) -> dict:
    """Send raw search data to ZVENO GPT for structured extraction."""
    if not settings.zveno_api_key:
        logger.info("ZVENO not configured, skipping GPT extraction")
        return {}

    try:
        async with httpx.AsyncClient(timeout=60) as c:
            payload = {
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Извлеки данные компании из этих результатов поиска:\n\n{raw_text[:8000]}"},
                ],
                "temperature": 0.05,
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
            if "choices" in data:
                content = data["choices"][0]["message"]["content"].strip()
                content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(content)
            else:
                logger.warning("GPT extraction failed: %s", json.dumps(data, ensure_ascii=False)[:300])
    except Exception:
        logger.exception("GPT extraction call failed")
    return {}


def _extract_with_regex(texts: list[str]) -> dict:
    """Fallback: extract phone/email/activity via regex from all texts."""
    result: dict = {"phone": "", "email": "", "activity": ""}
    all_text = " ".join(texts)
    phone_match = re.search(r"\+?7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", all_text)
    if phone_match:
        result["phone"] = phone_match.group(0)
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.+-]+", all_text)
    if email_match:
        result["email"] = email_match.group(0)
    patterns = [
        r"(?:занимается|специализируется|предоставляет|производит|оказывает)\s+([^\.;]{15,300})",
        r"(?:деятельность|основной вид деятельности)\s*[:\-–]?\s*([^\.;]{10,200})",
    ]
    for pat in patterns:
        m = re.search(pat, all_text, re.IGNORECASE)
        if m:
            result["activity"] = m.group(1).strip()[:200]
            break
    return result


async def search_company_info(name: str, inn: str = "", website: str = "") -> dict:
    """Multi-source search with GPT extraction."""

    # — 1. Tavily search —
    answer = ""
    tavily_texts: list[str] = []
    urls: list[str] = []
    sources: list[dict] = []

    if settings.tavily_api_key:
        try:
            query = f"{name} {inn} компания официальный сайт деятельность"
            sr = _search_tavily(query)
            answer = sr.get("answer", "")
            for item in sr.get("results", []):
                url = item.get("url", "")
                content = item.get("content", "")
                if url:
                    urls.append(url)
                    sources.append({"url": url, "title": item.get("title", ""), "snippet": content[:300]})
                if content:
                    tavily_texts.append(f"{item.get('title', '')}: {content[:500]}")
        except Exception:
            logger.exception("Tavily search failed")

    # — 2. DuckDuckGo search —
    ddg_texts: list[str] = []
    try:
        query = f"{name} {inn} сайт контакты"
        ddg_results = _search_duckduckgo(query)
        for r in ddg_results:
            url = r.get("href", "")
            body = r.get("body", "")
            if url:
                urls.append(url)
            if body:
                ddg_texts.append(f"{r.get('title', '')}: {body[:500]}")
    except Exception:
        logger.exception("DuckDuckGo search failed")

    # — 3. Deduplicate URLs and pick candidates —
    urls = _deduplicate_urls(urls)
    company_candidates = [u for u in urls if _is_company_domain(re.sub(r"https?://", "", u).split("/")[0])]
    first_party_url = company_candidates[0] if company_candidates else urls[0] if urls else website or ""

    # — 4. Scrape top unique URLs (max 3) —
    scrape_texts: list[str] = []
    to_scrape = []
    seen_domains = set()
    for url in company_candidates[:5]:
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        if domain not in seen_domains and len(to_scrape) < 3:
            seen_domains.add(domain)
            to_scrape.append(url)
    if not to_scrape:
        for url in urls[:3]:
            domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
            if domain not in seen_domains:
                seen_domains.add(domain)
                to_scrape.append(url)

    import asyncio
    scrape_results = await asyncio.gather(*[_scrape_url(u) for u in to_scrape], return_exceptions=True)
    for t in scrape_results:
        if isinstance(t, str) and t:
            scrape_texts.append(t)

    # — 5. Build raw text for GPT —
    raw_parts = []
    if answer:
        raw_parts.append(f"=== AI summary ===\n{answer}")
    if tavily_texts:
        raw_parts.append(f"=== Tavily results ===\n" + "\n".join(tavily_texts[:3]))
    if ddg_texts:
        raw_parts.append(f"=== DuckDuckGo results ===\n" + "\n".join(ddg_texts[:3]))
    if scrape_texts:
        raw_parts.append(f"=== Website content ===\n" + "\n\n".join(scrape_texts[:2]))
    raw_text = "\n\n".join(raw_parts)

    # — 6. Try GPT extraction —
    extracted = await _extract_with_gpt(raw_text)

    # — 7. Fallback: regex extraction —
    if not extracted or not extracted.get("phone") and not extracted.get("email"):
        regex_result = _extract_with_regex(tavily_texts + ddg_texts + scrape_texts)
        for key in ("phone", "email", "activity"):
            if not extracted.get(key):
                extracted[key] = regex_result.get(key, "")

    # — 8. Build result —
    first_party_domain = re.sub(r"https?://(www\.)?", "", first_party_url).split("/")[0].lower()
    if not _is_company_domain(first_party_domain):
        first_party_url = website or ""

    result = {
        "name": name,
        "inn": inn,
        "website": extracted.get("website", "") or first_party_url,
        "description": extracted.get("description", "") or answer or "",
        "phone": extracted.get("phone", "").rstrip("."),
        "email": extracted.get("email", "").rstrip(".,;"),
        "region": "",
        "activity": extracted.get("activity", ""),
        "revenue_hint": "",
        "employees_hint": "",
        "sources": sources,
        "website_candidates": company_candidates[:5],
    }

    return result

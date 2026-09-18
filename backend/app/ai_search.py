"""Multi-source AI company search with LLM extraction.

Flow:
  1. Brave Search (works from RF, has API key)
  2. Scrape top URLs from Brave results
  3. Send all raw data -> ZVENO GPT (free model) for structured extraction
  4. Regex extraction as last resort
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
    "nalog", "e-nalog", "yandex", "google",
    "vk", "facebook", "2gis", "spark", "spark-interfax",
    "kontragent", "audit-it", "rusbk", "rsprime", "fedresurs",
    "kontur", "focus-kontur", "focus",
    "checko", "checko.ru", "companies.rbc", "audit-it",
    "skyscanner", "aviasales", "tripadvisor", "booking", "airbnb",
    "ostrovok", "kinopoisk", "wikipedia", "instagram", "tiktok",
    "youtube", "twitter", "x.com", "avito", "ozon", "wildberries",
    "aliexpress", "ebay", "apple", "microsoft",
})

KEYS = ("website", "phone", "email", "activity", "description")

SEARCH_SYSTEM_PROMPT = """Ты — поисковый ассистент. Ищи информацию о российской компании по запросу и возвращай данные.

Верни ТОЛЬКО JSON без markdown-обёртки:
{
  "website": "официальный сайт компании или пустая строка",
  "phone": "контактный телефон компании или пустая строка",
  "email": "контактный email компании или пустая строка",
  "activity": "основной вид деятельности (30-100 символов) или пустая строка",
  "description": "краткое описание компании (1-3 предложения) или пустая строка"
}

Правила:
1. Сайт — только реальный домен компании (.ru/.com/.рф). Не агрегатор, не каталог, не страница соцсети.
2. Телефон — только прямой номер компании, не техподдержка агрегатора.
3. Email — только контактный email компании.
4. Если не уверен — оставь поле пустым. Лучше пусто, чем неверно."""

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


def _domain_of(url: str) -> str:
    """Extract bare domain from URL."""
    domain = re.sub(r"https?://(www\.)?", "", url).rstrip("/").lower()
    return domain


def _is_company_domain(domain: str) -> bool:
    """Filter out aggregator/known non-company domains."""
    for bad in AGGREGATOR_DOMAINS:
        if bad in domain:
            return False
    return True


def _parse_json(content: str) -> Optional[dict]:
    """Robust JSON extraction from LLM output."""
    content = content.strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    logger.warning("Failed to parse JSON from LLM: %s", content[:200])
    return None


def _extract_text_from_html(html: str, max_chars: int = 3000) -> str:
    """Clean HTML to plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:max_chars]


def _deduplicate_urls(urls: list[str]) -> list[str]:
    """Deduplicate URLs by domain."""
    seen = set()
    result = []
    for url in urls:
        domain = re.sub(r"https?://(www\.)?", "", url).rstrip("/").lower()
        if domain not in seen:
            seen.add(domain)
            result.append(url)
    return result


async def _search_brave(query: str, num_results: int = 10, timeout: int = 15) -> dict:
    """Search via Brave Search API.
    Returns {"results": [{"title", "url", "description", "age"}]}.
    """
    if not settings.brave_api_key:
        logger.info("Brave API key not configured, skipping")
        return {"results": []}

    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            resp = await c.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": settings.brave_api_key},
                params={"q": query, "count": num_results, "search_lang": "ru", "country": "ru"},
            )
            if resp.status_code != 200:
                logger.warning("Brave search error %s: %s", resp.status_code, resp.text[:300])
                return {"results": []}
            data = resp.json()
            results = []
            for r in data.get("web", {}).get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                    "age": r.get("age", ""),
                })
            return {"results": results}
    except Exception:
        logger.exception("Brave search failed")
        return {"results": []}


async def _search_zveno_perplexity(query: str, timeout: int = 90) -> dict:
    """Search via ZVENO Perplexity sonar-pro-search.
    Returns {"answer": str, "results": [{url, title, content}]}.
    """
    if not settings.zveno_api_key:
        logger.info("ZVENO not configured, skipping sonar search")
        return {"answer": "", "results": []}

    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            payload = {
                "model": "perplexity/sonar-pro-search",
                "messages": [
                    {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
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
            if resp.status_code != 200:
                logger.warning("Sonar search error %s: %s", resp.status_code, resp.text[:300])
                return {"answer": "", "results": []}
            data = resp.json()
            if "choices" not in data or not data["choices"]:
                logger.warning("Sonar search returned no choices: %s", json.dumps(data, ensure_ascii=False)[:300])
                return {"answer": "", "results": []}
            msg = data["choices"][0].get("message", {})
            answer = msg.get("content", "") or ""
            results = []
            for ann in msg.get("annotations") or []:
                cit = (ann or {}).get("url_citation") or {}
                url = cit.get("url", "")
                if url:
                    results.append({
                        "url": url,
                        "title": cit.get("title", ""),
                        "content": "",
                    })
            return {"answer": answer, "results": results}
    except Exception:
        logger.exception("Sonar search failed")
        return {"answer": "", "results": []}


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
    """Send raw search data to ZVENO GPT (free model) for structured extraction."""
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
            if "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"].strip()
                parsed = _parse_json(content)
                if parsed is not None:
                    return parsed
                logger.warning("GPT extraction returned non-JSON: %s", content[:200])
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
    """Multi-source search with LLM extraction (Brave + ZVENO GPT free model)."""

    # 1. Brave search
    queries = [f"{name} {inn} официальный сайт телефон email деятельность"]
    if website:
        queries.insert(0, f"{name} {inn} {website} официальный сайт контакты деятельность")

    answer = ""
    urls = []
    brave_snippets = []

    for q in queries:
        # Try Brave first
        res = await _search_brave(q, num_results=10)
        for r in res.get("results", []):
            urls.append(r["url"])
            snippet = f"{r.get('title', '')}: {r.get('description', '')}"
            if snippet not in brave_snippets:
                brave_snippets.append(snippet)

        # Try ZVENO sonar as supplement
        zveno_res = await _search_zveno_perplexity(q)
        if zveno_res.get("answer"):
            answer = zveno_res["answer"]
        for r in zveno_res.get("results", []):
            if r["url"] not in urls:
                urls.append(r["url"])

        # Break after first successful query
        if res.get("results") or zveno_res.get("results"):
            break

    # Deduplicate & filter aggregators
    urls = _deduplicate_urls(urls)
    company_urls = [u for u in urls if _is_company_domain(_domain_of(u))]
    other_urls = [u for u in urls if not _is_company_domain(_domain_of(u))]
    prioritized = company_urls[:3] + other_urls[:2]

    # 2. Scrape top URLs
    scraped_texts = []
    for url in prioritized[:5]:
        text = await _scrape_url(url)
        if text:
            scraped_texts.append(f"--- {url} ---\n{text}")

    # 3. Build raw text for GPT
    raw_parts = brave_snippets + scraped_texts
    if answer:
        raw_parts.insert(0, f"=== ZVENO AI summary ===\n{answer}")
    raw_text = "\n\n".join(raw_parts)

    # 4. GPT extraction (primary) - using ZVENO free model
    extracted = await _extract_with_gpt(raw_text) if raw_text else {}

    # 5. Regex fallback
    if not extracted or not any(v for v in extracted.values() if v):
        logger.info("GPT extraction empty, using regex fallback")
        extracted = _extract_with_regex(scraped_texts)

    # 6. Build result
    result = {
        "website": extracted.get("website", ""),
        "phone": extracted.get("phone", ""),
        "email": extracted.get("email", ""),
        "activity": extracted.get("activity", ""),
        "description": extracted.get("description", ""),
        "sources": brave_snippets[:5],
        "website_candidates": prioritized[:5],
    }
    return result
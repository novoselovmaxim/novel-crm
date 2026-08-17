"""Multi-source AI company search with LLM extraction.

Flow:
  1. ZVENO Perplexity sonar-pro-search (works from RF, no external keys)
  2. Scrape top URLs from result citations
  3. Send all raw data → ZVENO GPT for structured extraction (fallback)
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

SONAR_MODEL = "perplexity/sonar-pro-search"

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
    """Return bare domain without scheme/path."""
    if not url:
        return ""
    if "://" not in url:
        url = "//" + url
    try:
        from urllib.parse import urlparse
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return url.lower()


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


def _parse_json(content: str) -> Optional[dict]:
    """Robust JSON parse: strip code fences, fall back to first {...} block."""
    if not content:
        return None
    stripped = re.sub(r"^```(?:json)?\s*", "", content.strip())
    stripped = re.sub(r"\s*```$", "", stripped).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", stripped, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


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


async def _search_zveno_perplexity(query: str, timeout: int = 90) -> dict:
    """Search via ZVENO Perplexity sonar-pro-search.
    Returns {"answer": str, "results": [{url, title, content}]}."""
    if not settings.zveno_api_key:
        logger.info("ZVENO not configured, skipping sonar search")
        return {"answer": "", "results": []}

    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            payload = {
                "model": SONAR_MODEL,
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
    """Multi-source search with LLM extraction (ZVENO sonar primary)."""

    # — 1. Sonar search —
    queries = [f"{name} {inn} официальный сайт телефон email деятельность"]
    if website:
        queries.insert(0, f"{name} {inn} {website} официальный сайт контакты деятельность")

    answer = ""
    results: list[dict] = []
    seen_urls = set()
    for q in queries:
        sr = await _search_zveno_perplexity(q)
        if sr.get("answer"):
            answer = sr["answer"]
        for r in sr.get("results", []):
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(r)
        if answer:
            break

    sources = [
        {"url": r["url"], "title": r.get("title", ""), "snippet": ""}
        for r in results[:8]
    ]

    # — 2. Try structured JSON from sonar —
    extracted: dict = _parse_json(answer) or {}

    # — 3. Deduplicate URLs and pick candidates —
    urls = _deduplicate_urls([r["url"] for r in results])
    company_candidates = [u for u in urls if _is_company_domain(_domain_of(u))]
    first_party_url = company_candidates[0] if company_candidates else urls[0] if urls else website or ""

    # — 4. Scrape top unique URLs (max 3) —
    scrape_texts: list[str] = []
    to_scrape = []
    seen_domains = set()
    for url in company_candidates[:5]:
        domain = _domain_of(url)
        if domain not in seen_domains and len(to_scrape) < 3:
            seen_domains.add(domain)
            to_scrape.append(url)
    if not to_scrape:
        for url in urls[:3]:
            domain = _domain_of(url)
            if domain not in seen_domains:
                seen_domains.add(domain)
                to_scrape.append(url)

    import asyncio
    scrape_results = await asyncio.gather(*[_scrape_url(u) for u in to_scrape], return_exceptions=True)
    for t in scrape_results:
        if isinstance(t, str) and t:
            scrape_texts.append(t)

    # — 5. Build raw text for GPT (fallback enrichment) —
    raw_parts = []
    if answer:
        raw_parts.append(f"=== AI summary ===\n{answer}")
    if scrape_texts:
        raw_parts.append(f"=== Website content ===\n" + "\n\n".join(scrape_texts[:2]))
    raw_text = "\n\n".join(raw_parts)

    # — 6. Fallback: GPT extraction if sonar gave nothing useful —
    if not extracted or not any(extracted.get(k) for k in KEYS):
        gpt_extracted = await _extract_with_gpt(raw_text)
        for key in KEYS:
            if not extracted.get(key):
                extracted[key] = gpt_extracted.get(key, "")

    # — 7. Last resort: regex extraction —
    if not any(extracted.get(k) for k in ("phone", "email", "activity")):
        regex_result = _extract_with_regex(scrape_texts)
        for key in ("phone", "email", "activity"):
            if not extracted.get(key):
                extracted[key] = regex_result.get(key, "")

    # — 8. Build result —
    first_party_domain = _domain_of(first_party_url)
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
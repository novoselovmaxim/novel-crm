"""Multi-source search orchestrator.

Coordinates Brave, Exa, ZVENO Sonar, Scrapling scraping, and LLM extraction
for comprehensive company research.
"""
import asyncio
import json
import logging
import re
from typing import Optional

from .search_brave import search_brave_web
from .search_exa import search_exa_company
from .scraper_scrapling import scrape_company_sites
from ..ai_search import (
    _search_zveno_perplexity,
    _extract_with_gpt,
    _extract_with_regex,
    _parse_json,
    _domain_of,
    _is_company_domain,
    _deduplicate_urls,
    KEYS,
)

logger = logging.getLogger(__name__)

AGGREGATOR_DOMAINS = frozenset({
    "zachestnyibiznes", "list-org", "rusprofile", "sbis", "sbisru",
    "nalog", "e-nalog", "yandex", "google",
    "vk", "facebook", "2gis", "spark", "spark-interfax",
    "kontragent", "audit-it", "rusbk", "rsprime", "fedresurs",
    "kontur", "focus-kontur", "focus",
    "checko", "checko.ru", "companies.rbc",
})


async def research_company(
    name: str,
    inn: str = "",
    website: str = "",
    custom_query: str = "",
    sources: Optional[list[str]] = None,
) -> dict:
    """Multi-source company research.

    sources: list of ["brave", "exa", "zveno"]
    custom_query: user-provided search query

    Returns dict with results from all sources, extracted data, and metadata.
    """
    if sources is None:
        sources = ["brave", "exa", "zveno"]

    base_query = f"{name} {inn}".strip()
    if custom_query:
        search_query = f"{base_query} {custom_query}"
    else:
        search_query = f"{base_query} официальный сайт телефон email деятельность руководство"

    # --- 1. Parallel search across all sources ---
    tasks = {}
    if "brave" in sources:
        tasks["brave"] = search_brave_web(search_query, count=10)
    if "exa" in sources:
        tasks["exa"] = search_exa_company(name=name, inn=inn, query=search_query)
    if "zveno" in sources:
        tasks["zveno"] = _search_zveno_perplexity(search_query)

    done = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results_map = dict(zip(tasks.keys(), done))

    # --- 2. Collect all URLs ---
    all_urls: list[str] = []
    for source_name, result in results_map.items():
        if isinstance(result, Exception):
            logger.warning("Search source %s failed: %s", source_name, result)
            continue
        if source_name == "zveno":
            for r in result.get("results", []):
                url = r.get("url", "")
                if url:
                    all_urls.append(url)
        elif source_name in ("brave", "exa"):
            for r in result.get("results", []):
                url = r.get("url", "")
                if url:
                    all_urls.append(url)

    # --- 3. Deduplicate and filter ---
    unique_urls = _deduplicate_urls(all_urls)
    company_urls = [u for u in unique_urls if _is_company_domain(_domain_of(u))]
    # Prefer company domains, then add others
    urls_to_scrape = (company_urls[:3] + [u for u in unique_urls if u not in company_urls][:2])[:5]

    # --- 4. Scraping via Scrapling ---
    scraped_texts = await scrape_company_sites(urls_to_scrape)

    # --- 5. Build raw text for extraction ---
    raw_parts: list[str] = []
    zveno_answer = ""
    zveno_data = results_map.get("zveno")
    if zveno_data and not isinstance(zveno_data, Exception):
        zveno_answer = zveno_data.get("answer", "")
        if zveno_answer:
            raw_parts.append(f"=== ZVENO AI summary ===\n{zveno_answer}")

    brave_data = results_map.get("brave")
    if brave_data and not isinstance(brave_data, Exception):
        brave_text = "\n".join(
            f"[{r['title']}] {r['description']}"
            for r in brave_data.get("results", [])[:5]
        )
        if brave_text:
            raw_parts.append(f"=== Brave Search ===\n{brave_text}")

    exa_data = results_map.get("exa")
    if exa_data and not isinstance(exa_data, Exception):
        exa_text = "\n".join(
            f"[{r['title']}] {r.get('text', '')[:500]}"
            for r in exa_data.get("results", [])[:5]
        )
        if exa_text:
            raw_parts.append(f"=== Exa Semantic Search ===\n{exa_text}")

    if scraped_texts:
        raw_parts.append("=== Website content ===\n" + "\n\n".join(scraped_texts[:2]))

    raw_text = "\n\n".join(raw_parts)

    # --- 6. Extract structured data ---
    extracted: dict = _parse_json(zveno_answer) or {}

    # GPT extraction fallback
    if not extracted or not any(extracted.get(k) for k in KEYS):
        gpt_extracted = await _extract_with_gpt(raw_text)
        for key in KEYS:
            if not extracted.get(key):
                extracted[key] = gpt_extracted.get(key, "")

    # Regex extraction last resort
    if not any(extracted.get(k) for k in ("phone", "email", "activity")):
        regex_result = _extract_with_regex(scraped_texts)
        for key in ("phone", "email", "activity"):
            if not extracted.get(key):
                extracted[key] = regex_result.get(key, "")

    # --- 7. Source status for UI ---
    sources_info = []
    for source_name in ["brave", "exa", "zveno"]:
        result = results_map.get(source_name)
        if result is None:
            sources_info.append({"name": source_name, "status": "skipped", "count": 0})
        elif isinstance(result, Exception):
            sources_info.append({
                "name": source_name,
                "status": "error",
                "error": str(result)[:200],
                "count": 0,
            })
        else:
            count = len(result.get("results", []))
            sources_info.append({"name": source_name, "status": "ok", "count": count})

    return {
        "brave_results": results_map.get("brave", {}).get("results", [])
            if brave_data and not isinstance(brave_data, Exception) else [],
        "exa_results": results_map.get("exa", {}).get("results", [])
            if exa_data and not isinstance(exa_data, Exception) else [],
        "zveno_answer": zveno_answer,
        "zveno_results": results_map.get("zveno", {}).get("results", [])
            if zveno_data and not isinstance(zveno_data, Exception) else [],
        "scraped_texts": scraped_texts,
        "extracted_data": extracted,
        "sources": sources_info,
        "all_urls": company_urls[:10],
        "raw_text_preview": raw_text[:3000],
    }

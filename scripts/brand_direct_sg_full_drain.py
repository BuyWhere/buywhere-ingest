#!/usr/bin/env python3
"""Brand-direct SG full-batch drain (Apple SG buy.xml + Samsung SG sitemaps).

Replaces the per-URL regex parsing in scripts/apple_sg_buy_xml_lane.py and
scripts/samsung_sg_sitemap_lane.py with JSON-LD-aware parsing (matching the
probe at scripts/brand_direct_sg_probe.py), then drains the full batches
asynchronously with bounded concurrency and writes:

  - merchants/apple_sg_buy_xml_full_2026-06-06.ndjson
  - merchants/samsung_sg_sitemap_full_2026-06-06.ndjson
  - data/brand_direct/apple_sg_buy_xml_full_2026-06-06_failures.json
  - data/brand_direct/samsung_sg_sitemap_full_2026-06-06_failures.json

Schema (each row, in addition to the per-merchant fields):
  sku (Apple part number or Samsung model code),
  name, url, price, currency=SGD, source, region=SG, platform=direct_http.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
MERCHANTS_DIR = REPO_ROOT / "merchants"
FAILURES_DIR = REPO_ROOT / "data" / "brand_direct"
MERCHANTS_DIR.mkdir(parents=True, exist_ok=True)
FAILURES_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = REPO_ROOT / "data" / "brand_direct" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

APPLE_SG_BUY_XML = "https://www.apple.com/sg/shop/sitemaps/buy.xml"
SAMSUNG_SG_SITEMAP = "https://www.samsung.com/sg/sitemap.xml"

DATE = datetime.now(timezone.utc).date().isoformat()


@dataclass
class Failure:
    url: str
    error: str


@dataclass
class DrainResult:
    merchant_id: str
    source: str
    records: list[dict[str, Any]] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    total_candidates: int = 0
    elapsed_seconds: float = 0.0


def extract_xml_locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    return [node.text.strip() for node in root.findall(".//{*}loc") if node.text]


def normalize_currency(value: Any) -> str:
    if value is None:
        return "SGD"
    text = str(value).strip().upper()
    if text in {"SGD", "S$", "SG$"}:
        return "SGD"
    return text or "SGD"


def normalize_price(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^0-9.]", "", value)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def first_jsonld_product(html: str) -> Optional[dict[str, Any]]:
    for raw in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    ):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            if isinstance(entry, dict) and entry.get("@type") == "Product":
                return entry
    return None


def derive_apple_record(html: str, url: str) -> Optional[dict[str, Any]]:
    product = first_jsonld_product(html)
    if product is None:
        return None
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    sku = offers.get("sku") or product.get("sku") or product.get("mpn")
    if not sku:
        return None
    return {
        "merchant_id": "apple_sg",
        "source": "apple_sg_buy_xml",
        "region": "SG",
        "country_code": "SG",
        "platform": "direct_http",
        "url": url,
        "currency": normalize_currency(offers.get("priceCurrency") or "SGD"),
        "category": "apple_store",
        "name": product.get("name"),
        "sku": sku,
        "part_number": sku,
        "price": normalize_price(offers.get("price")),
        "brand": (product.get("brand") or {}).get("name")
        if isinstance(product.get("brand"), dict)
        else (product.get("brand") or "Apple"),
        "availability": offers.get("availability"),
    }


def derive_samsung_record(html: str, url: str, sitemap: str) -> Optional[dict[str, Any]]:
    product = first_jsonld_product(html)
    if product is not None:
        offers = product.get("offers") or {}
        if not isinstance(offers, dict):
            offers = {}
        sku = product.get("sku") or offers.get("sku")
        brand_field = product.get("brand")
        if isinstance(brand_field, dict):
            brand = brand_field.get("name") or "Samsung"
        elif isinstance(brand_field, str) and brand_field:
            brand = brand_field
        else:
            brand = "Samsung"
        path_parts = [p for p in urlparse(url).path.split("/") if p]
        category = path_parts[2] if len(path_parts) > 2 else None
        if not sku:
            return None
        return {
            "merchant_id": "samsung_sg",
            "source": "samsung_sg_sitemap",
            "region": "SG",
            "country_code": "SG",
            "platform": "direct_http",
            "url": url,
            "currency": normalize_currency(offers.get("priceCurrency") or "SGD"),
            "category": category,
            "name": product.get("name"),
            "sku": sku,
            "part_number": sku,
            "price": normalize_price(offers.get("price")),
            "brand": brand,
            "availability": offers.get("availability"),
            "sitemap": sitemap,
        }
    model_match = re.search(r'id="modelCode"[^>]*value="([^"]+)"', html)
    if not model_match:
        return None
    sku = model_match.group(1)
    path_parts = [p for p in urlparse(url).path.split("/") if p]
    category = path_parts[2] if len(path_parts) > 2 else None
    return {
        "merchant_id": "samsung_sg",
        "source": "samsung_sg_sitemap",
        "region": "SG",
        "country_code": "SG",
        "platform": "direct_http",
        "url": url,
        "currency": "SGD",
        "category": category,
        "name": None,
        "sku": sku,
        "part_number": sku,
        "price": None,
        "brand": "Samsung",
        "availability": None,
        "sitemap": sitemap,
    }


def looks_like_samsung_product_url(url: str) -> bool:
    segments = [segment for segment in urlparse(url).path.split("/") if segment]
    if len(segments) < 3:
        return False
    leaf = segments[-1]
    if leaf.startswith("all-"):
        return False
    if not re.search(r"\d", leaf):
        return False
    if leaf.count("-") < 2:
        return False
    return True


async def fetch_text(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 30.0,
    retries: int = 2,
) -> Optional[str]:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True)
            if resp.status_code in (429, 541):
                if attempt < retries:
                    await asyncio.sleep(2.0 + attempt * 2.0)
                    continue
            if resp.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"status {resp.status_code}", request=resp.request, response=resp
                )
            return resp.text
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                await asyncio.sleep(0.5 + attempt * 0.5)
    raise last_exc if last_exc else RuntimeError("unknown fetch error")


async def scrape_with_limit(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    urls: list[str],
    parser,
    failures: list[Failure],
    *,
    source: str,
    cache_lock: asyncio.Lock,
    failure_lock: asyncio.Lock,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    parsed_total = 0
    existing = load_cache(source)
    failures_existing = load_failure_cache(source)
    if existing:
        print(f"  cache: {len(existing)} already parsed", flush=True)
    if failures_existing:
        print(f"  cache: {len(failures_existing)} previously failed", flush=True)
    records.extend(existing.values())
    parsed_total = len(existing)
    pending_urls = [url for url in urls if url not in existing and url not in failures_existing]
    print(f"  pending: {len(pending_urls)} (skipped cached)", flush=True)

    async def worker(url: str) -> None:
        nonlocal parsed_total
        async with semaphore:
            try:
                html = await fetch_text(client, url)
            except Exception as exc:  # noqa: BLE001
                async with failure_lock:
                    failures.append(Failure(url=url, error=str(exc)))
                    append_failure_cache(source, url, str(exc))
                return
            if html is None:
                async with failure_lock:
                    failures.append(Failure(url=url, error="empty_body"))
                    append_failure_cache(source, url, "empty_body")
                return
            try:
                record = parser(html, url)
            except Exception as exc:  # noqa: BLE001
                async with failure_lock:
                    failures.append(Failure(url=url, error=f"parse: {exc}"))
                    append_failure_cache(source, url, f"parse: {exc}")
                return
            if record is None:
                async with failure_lock:
                    failures.append(Failure(url=url, error="no_product_payload"))
                    append_failure_cache(source, url, "no_product_payload")
                return
            async with cache_lock:
                records.append(record)
                append_cache(source, record)
                parsed_total += 1
                if parsed_total % 100 == 0:
                    print(f"  parsed {parsed_total}/{len(urls)}", flush=True)

    if pending_urls:
        await asyncio.gather(*(worker(url) for url in pending_urls))
    return records


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for record in records:
        sku = record.get("sku")
        url = record.get("url")
        key = f"{sku}|{url}" if sku else f"url:{url}"
        if key not in seen:
            seen[key] = record
    return list(seen.values())


def validate_record(record: dict[str, Any], *, source: str) -> Optional[str]:
    for required in ("sku", "url", "name", "source", "region", "platform"):
        if not record.get(required):
            return f"missing {required}"
    if record.get("source") != source:
        return f"wrong source={record.get('source')}"
    if record.get("region") != "SG":
        return f"wrong region={record.get('region')}"
    if record.get("platform") != "direct_http":
        return f"wrong platform={record.get('platform')}"
    if record.get("currency") not in {"SGD"}:
        return f"wrong currency={record.get('currency')}"
    return None


def write_ndjson(path: Path, records: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def cache_path(source: str) -> Path:
    return CACHE_DIR / f"{source}_cache.jsonl"


def load_cache(source: str) -> dict[str, dict[str, Any]]:
    path = cache_path(source)
    if not path.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = record.get("url")
            if url:
                cache[url] = record
    return cache


def append_cache(source: str, record: dict[str, Any]) -> None:
    path = cache_path(source)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def cache_failures_path(source: str) -> Path:
    return CACHE_DIR / f"{source}_failures_cache.jsonl"


def load_failure_cache(source: str) -> dict[str, str]:
    path = cache_failures_path(source)
    if not path.exists():
        return {}
    failures: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = obj.get("url")
            err = obj.get("error")
            if url and err is not None:
                failures[url] = err
    return failures


def append_failure_cache(source: str, url: str, error: str) -> None:
    path = cache_failures_path(source)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"url": url, "error": error}, ensure_ascii=False) + "\n")


async def drain_apple(client: httpx.AsyncClient, concurrency: int) -> DrainResult:
    print("[apple] discovering buy.xml URLs...", flush=True)
    body = await fetch_text(client, APPLE_SG_BUY_XML, timeout=60.0, retries=4)
    if body is None:
        return DrainResult(merchant_id="apple_sg", source="apple_sg_buy_xml")
    all_locs = extract_xml_locs(body)
    urls = sorted({loc for loc in all_locs if "/sg/shop/buy-" in loc})
    print(f"[apple] discovered {len(urls)} unique buy URLs", flush=True)
    result = DrainResult(merchant_id="apple_sg", source="apple_sg_buy_xml")
    result.total_candidates = len(urls)
    sem = asyncio.Semaphore(concurrency)
    cache_lock = asyncio.Lock()
    failure_lock = asyncio.Lock()
    started = time.monotonic()
    result.records = await scrape_with_limit(
        client, sem, urls, derive_apple_record, result.failures,
        source="apple_sg_buy_xml",
        cache_lock=cache_lock,
        failure_lock=failure_lock,
    )
    result.elapsed_seconds = time.monotonic() - started
    result.records = deduplicate_records(result.records)
    return result


async def drain_samsung(client: httpx.AsyncClient, concurrency: int) -> DrainResult:
    print("[samsung] discovering sitemap URLs...", flush=True)
    body = await fetch_text(client, SAMSUNG_SG_SITEMAP, timeout=60.0, retries=4)
    if body is None:
        return DrainResult(merchant_id="samsung_sg", source="samsung_sg_sitemap")
    b2c_sitemaps = [loc for loc in extract_xml_locs(body) if loc.endswith("b2c-sitemap.xml")]
    child_sitemaps: list[str] = []
    for b2c in b2c_sitemaps:
        sub = await fetch_text(client, b2c, timeout=60.0, retries=4)
        if not sub:
            continue
        child_sitemaps.extend(extract_xml_locs(sub))
    print(f"[samsung] discovered {len(child_sitemaps)} child sitemaps", flush=True)

    candidates_by_sitemap: dict[str, list[str]] = {}
    for sitemap in child_sitemaps:
        sub = await fetch_text(client, sitemap, timeout=60.0, retries=4)
        if not sub:
            continue
        candidates_by_sitemap[sitemap] = [u for u in extract_xml_locs(sub) if looks_like_samsung_product_url(u)]
    total_candidates = sum(len(v) for v in candidates_by_sitemap.values())
    print(f"[samsung] discovered {total_candidates} candidate URLs across {len(candidates_by_sitemap)} sitemaps", flush=True)
    result = DrainResult(merchant_id="samsung_sg", source="samsung_sg_sitemap")
    result.total_candidates = total_candidates
    sem = asyncio.Semaphore(concurrency)
    cache_lock = asyncio.Lock()
    failure_lock = asyncio.Lock()
    started = time.monotonic()

    existing = load_cache("samsung_sg_sitemap")
    failures_existing = load_failure_cache("samsung_sg_sitemap")
    if existing:
        print(f"  cache: {len(existing)} already parsed", flush=True)
    if failures_existing:
        print(f"  cache: {len(failures_existing)} previously failed", flush=True)
    records: list[dict[str, Any]] = list(existing.values())
    pending: list[tuple[str, str]] = []
    for sitemap, urls in candidates_by_sitemap.items():
        for url in urls:
            if url in existing or url in failures_existing:
                continue
            pending.append((sitemap, url))
    print(f"  pending: {len(pending)} (skipped cached)", flush=True)

    parsed_total = len(records)

    async def samsung_worker(sitemap: str, url: str) -> None:
        nonlocal parsed_total
        async with sem:
            try:
                html = await fetch_text(client, url)
            except Exception as exc:  # noqa: BLE001
                async with failure_lock:
                    result.failures.append(Failure(url=url, error=str(exc)))
                    append_failure_cache("samsung_sg_sitemap", url, str(exc))
                return
            if html is None:
                async with failure_lock:
                    result.failures.append(Failure(url=url, error="empty_body"))
                    append_failure_cache("samsung_sg_sitemap", url, "empty_body")
                return
            try:
                record = derive_samsung_record(html, url, sitemap)
            except Exception as exc:  # noqa: BLE001
                async with failure_lock:
                    result.failures.append(Failure(url=url, error=f"parse: {exc}"))
                    append_failure_cache("samsung_sg_sitemap", url, f"parse: {exc}")
                return
            if record is None:
                async with failure_lock:
                    result.failures.append(Failure(url=url, error="no_product_payload"))
                    append_failure_cache("samsung_sg_sitemap", url, "no_product_payload")
                return
            async with cache_lock:
                records.append(record)
                append_cache("samsung_sg_sitemap", record)
                parsed_total += 1
                if parsed_total % 200 == 0:
                    print(f"  parsed {parsed_total}/{total_candidates}", flush=True)

    if pending:
        await asyncio.gather(*(samsung_worker(sitemap, url) for sitemap, url in pending))
    result.elapsed_seconds = time.monotonic() - started
    result.records = deduplicate_records(records)
    return result


def write_outputs(result: DrainResult, *, source: str, failures_path: Path) -> dict[str, Any]:
    ndjson_path = MERCHANTS_DIR / f"{source}_full_{DATE}.ndjson"
    cached = list(load_cache(source).values())
    merged = deduplicate_records(cached)
    written = write_ndjson(ndjson_path, merged)

    invalid: list[dict[str, str]] = []
    for record in merged:
        err = validate_record(record, source=source)
        if err:
            invalid.append({"url": record.get("url", ""), "error": err})

    failures_from_cache = list(load_failure_cache(source).items())
    failure_count = len(failures_from_cache)

    failures_payload = {
        "source": source,
        "merchant_id": result.merchant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": result.total_candidates,
        "record_count": written,
        "unique_records": written,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "failure_count": failure_count,
        "failures": [
            {"url": url, "error": err}
            for url, err in failures_from_cache[:1000]
        ],
        "invalid_schema": invalid,
    }
    failures_path.write_text(json.dumps(failures_payload, indent=2), encoding="utf-8")

    return {
        "source": source,
        "ndjson_path": str(ndjson_path.relative_to(REPO_ROOT)),
        "failures_path": str(failures_path.relative_to(REPO_ROOT)),
        "record_count": written,
        "total_candidates": result.total_candidates,
        "failure_count": failure_count,
        "invalid_count": len(invalid),
        "elapsed_seconds": round(result.elapsed_seconds, 2),
    }


async def main_async(concurrency: int) -> int:
    timeout = httpx.Timeout(30.0, connect=20.0)
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, http2=False) as client:
        apple_result = await drain_apple(client, concurrency)
        samsung_result = await drain_samsung(client, concurrency)

    apple_summary = write_outputs(
        apple_result,
        source="apple_sg_buy_xml",
        failures_path=FAILURES_DIR / f"apple_sg_buy_xml_full_{DATE}_failures.json",
    )
    samsung_summary = write_outputs(
        samsung_result,
        source="samsung_sg_sitemap",
        failures_path=FAILURES_DIR / f"samsung_sg_sitemap_full_{DATE}_failures.json",
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "concurrency": concurrency,
        "apple": apple_summary,
        "samsung": samsung_summary,
        "combined_record_count": apple_summary["record_count"] + samsung_summary["record_count"],
    }
    summary_path = FAILURES_DIR / f"brand_direct_sg_full_drain_{DATE}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=12)
    args = parser.parse_args()
    return asyncio.run(main_async(args.concurrency))


if __name__ == "__main__":
    raise SystemExit(main())

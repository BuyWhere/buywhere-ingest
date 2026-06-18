#!/usr/bin/env python3
"""Probe Apple/Samsung SG brand-direct surfaces and emit first-batch artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "brand_direct"
MERCHANTS_DIR = REPO_ROOT / "merchants"

APPLE_SEED_PAGES = [
    "https://www.apple.com/sg/iphone/",
    "https://www.apple.com/sg/ipad/",
    "https://www.apple.com/sg/watch/",
    "https://www.apple.com/sg/airpods/",
    "https://www.apple.com/sg/mac/",
]
APPLE_SG_BUY_XML = "https://www.apple.com/sg/shop/sitemaps/buy.xml"

SAMSUNG_SG_SITEMAP = "https://www.samsung.com/sg/sitemap.xml"


@dataclass
class FetchResult:
    url: str
    status: int
    body: str


def fetch_text(url: str, timeout: int = 30, retries: int = 3) -> FetchResult:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = getattr(response, "status", 200)
                return FetchResult(url=url, status=status, body=body)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return FetchResult(url=url, status=exc.code, body=body)
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(1.0 + attempt)
    raise RuntimeError(f"fetch failed for {url}: {last_error}")


def extract_xml_locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    return [node.text.strip() for node in root.findall(".//{*}loc") if node.text]


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MERCHANTS_DIR.mkdir(parents=True, exist_ok=True)


def discover_apple_buy_pages() -> list[str]:
    buy_pages = set(extract_xml_locs(fetch_text(APPLE_SG_BUY_XML, timeout=60).body))
    if buy_pages:
        return sorted(url for url in buy_pages if "/sg/shop/buy-" in url)

    href_pattern = re.compile(r'href="(?P<href>/sg/shop/buy-[^"]+)"')
    for seed_url in APPLE_SEED_PAGES:
        result = fetch_text(seed_url)
        for match in href_pattern.finditer(result.body):
            buy_pages.add(urljoin("https://www.apple.com", match.group("href")))
    return sorted(buy_pages)


def parse_apple_product_page(html: str, url: str) -> dict[str, Any] | None:
    for raw_json in re.findall(
        r'<script type="application/ld\+json">(?P<payload>.*?)</script>',
        html,
        re.DOTALL,
    ):
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or payload.get("@type") != "Product":
            continue
        offers = payload.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}
        return {
            "merchant_id": "apple_sg",
            "source": "apple_sg_buy_xml",
            "region": "SG",
            "country_code": "SG",
            "platform": "direct_http",
            "url": url,
            "currency": offers.get("priceCurrency"),
            "category": "apple_store",
            "name": payload.get("name"),
            "sku": offers.get("sku"),
            "part_number": offers.get("sku"),
            "price": offers.get("price"),
            "brand": "Apple",
            "availability": offers.get("availability"),
        }
    return None


def probe_apple(batch_limit: int) -> dict[str, Any]:
    buy_pages = discover_apple_buy_pages()
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for buy_page in buy_pages[:batch_limit]:
        try:
            result = fetch_text(buy_page)
            record = parse_apple_product_page(result.body, buy_page)
            if record:
                records.append(record)
            else:
                failures.append({"url": buy_page, "error": "no_product_json_ld"})
        except Exception as exc:  # pragma: no cover - heartbeat artifact path
            failures.append({"url": buy_page, "error": str(exc)})
    unique_skus = len({record["sku"] for record in records if record.get("sku")})
    return {
        "seed_pages": APPLE_SEED_PAGES,
        "buy_pages": buy_pages,
        "buy_page_count": len(buy_pages),
        "batch_limit": batch_limit,
        "record_count": len(records),
        "unique_skus": unique_skus,
        "family_count": len({urlparse(url).path.split("/")[4] for url in buy_pages if len(urlparse(url).path.split("/")) > 4}),
        "failures": failures,
        "records": records,
    }


def looks_like_samsung_product_url(url: str) -> bool:
    parsed = urlparse(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
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


def parse_samsung_product(html: str, url: str) -> dict[str, Any] | None:
    for raw_json in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    ):
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("@type") != "Product":
                continue
            offers = entry.get("offers") or {}
            if not isinstance(offers, dict):
                offers = {}
            return {
                "merchant_id": "samsung_sg",
                "source": "samsung_sg",
                "region": "SG",
                "country_code": "SG",
                "platform": "direct_http",
                "url": url,
                "name": entry.get("name"),
                "sku": entry.get("sku"),
                "price": offers.get("price"),
                "currency": offers.get("priceCurrency"),
                "availability": offers.get("availability"),
                "brand": ((entry.get("brand") or {}) if isinstance(entry.get("brand"), dict) else {}).get("name"),
                "category": urlparse(url).path.split("/")[2] if len(urlparse(url).path.split("/")) > 2 else None,
            }
    model_code_match = re.search(r'id="modelCode"[^>]*value="([^"]+)"', html)
    if not model_code_match:
        return None
    return {
        "merchant_id": "samsung_sg",
        "source": "samsung_sg",
        "region": "SG",
        "country_code": "SG",
        "platform": "direct_http",
        "url": url,
        "name": None,
        "sku": model_code_match.group(1),
        "price": None,
        "currency": "SGD",
        "availability": None,
        "brand": "Samsung",
        "category": urlparse(url).path.split("/")[2] if len(urlparse(url).path.split("/")) > 2 else None,
    }


def discover_samsung_candidate_urls() -> dict[str, list[str]]:
    top_level = extract_xml_locs(fetch_text(SAMSUNG_SG_SITEMAP).body)
    b2c_sitemaps = [loc for loc in top_level if loc.endswith("b2c-sitemap.xml")]
    child_sitemaps: list[str] = []
    for b2c_sitemap in b2c_sitemaps:
        child_sitemaps.extend(extract_xml_locs(fetch_text(b2c_sitemap).body))

    candidates_by_sitemap: dict[str, list[str]] = {}
    for child_sitemap in child_sitemaps:
        urls = extract_xml_locs(fetch_text(child_sitemap).body)
        candidates_by_sitemap[child_sitemap] = [
            url for url in urls if looks_like_samsung_product_url(url)
        ]
    return candidates_by_sitemap


def probe_samsung(batch_limit: int) -> dict[str, Any]:
    candidates_by_sitemap = discover_samsung_candidate_urls()
    all_candidates = [
        {"sitemap": sitemap, "url": url}
        for sitemap, urls in candidates_by_sitemap.items()
        for url in urls
    ]

    verified: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for candidate in all_candidates[:batch_limit]:
        try:
            result = fetch_text(candidate["url"])
            record = parse_samsung_product(result.body, candidate["url"])
            if record:
                record["sitemap"] = candidate["sitemap"]
                verified.append(record)
            else:
                failures.append({"url": candidate["url"], "error": "no_product_payload"})
        except Exception as exc:  # pragma: no cover - heartbeat artifact path
            failures.append({"url": candidate["url"], "error": str(exc)})

    return {
        "sitemap_count": len(candidates_by_sitemap),
        "candidate_count": len(all_candidates),
        "batch_limit": batch_limit,
        "verified_count": len(verified),
        "candidates_by_sitemap": candidates_by_sitemap,
        "verified_records": verified,
        "failures": failures,
    }


def write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument(
        "--samsung-batch-limit",
        type=int,
        default=120,
        help="Max candidate Samsung SG URLs to verify into the first batch.",
    )
    parser.add_argument(
        "--apple-batch-limit",
        type=int,
        default=40,
        help="Max Apple SG buy.xml product URLs to verify into the first batch.",
    )
    args = parser.parse_args()

    ensure_output_dirs()

    apple = probe_apple(batch_limit=args.apple_batch_limit)
    samsung = probe_samsung(batch_limit=args.samsung_batch_limit)

    apple_summary_path = OUTPUT_DIR / f"apple_sg_brand_probe_{args.date}.json"
    samsung_summary_path = OUTPUT_DIR / f"samsung_sg_brand_probe_{args.date}.json"
    apple_ndjson_path = MERCHANTS_DIR / f"apple_sg_{args.date}.ndjson"
    samsung_ndjson_path = MERCHANTS_DIR / f"samsung_sg_{args.date}.ndjson"
    samsung_candidates_path = OUTPUT_DIR / f"samsung_sg_candidates_{args.date}.ndjson"

    apple_summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **apple,
        "artifact_path": str(apple_ndjson_path.relative_to(REPO_ROOT)),
    }
    samsung_summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **samsung,
        "artifact_path": str(samsung_ndjson_path.relative_to(REPO_ROOT)),
        "candidate_artifact_path": str(samsung_candidates_path.relative_to(REPO_ROOT)),
    }

    apple_summary_path.write_text(json.dumps(apple_summary, indent=2), encoding="utf-8")
    samsung_summary_path.write_text(json.dumps(samsung_summary, indent=2), encoding="utf-8")
    write_ndjson(apple_ndjson_path, apple["records"])
    write_ndjson(samsung_ndjson_path, samsung["verified_records"])
    write_ndjson(samsung_candidates_path, [
        {"sitemap": sitemap, "url": url}
        for sitemap, urls in samsung["candidates_by_sitemap"].items()
        for url in urls
    ])

    category_counts = Counter(
        record.get("category") for record in samsung["verified_records"] if record.get("category")
    )
    summary = {
        "apple": {
            "family_count": apple["family_count"],
            "record_count": apple["record_count"],
            "unique_skus": apple["unique_skus"],
            "artifact_path": str(apple_ndjson_path.relative_to(REPO_ROOT)),
            "summary_path": str(apple_summary_path.relative_to(REPO_ROOT)),
            "sample": apple["records"][:5],
        },
        "samsung": {
            "sitemap_count": samsung["sitemap_count"],
            "candidate_count": samsung["candidate_count"],
            "verified_count": samsung["verified_count"],
            "artifact_path": str(samsung_ndjson_path.relative_to(REPO_ROOT)),
            "candidate_artifact_path": str(samsung_candidates_path.relative_to(REPO_ROOT)),
            "summary_path": str(samsung_summary_path.relative_to(REPO_ROOT)),
            "category_counts": dict(category_counts),
            "sample": samsung["verified_records"][:5],
        },
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Ingest Bách hoá XANH Vietnam grocery products via sitemap + product pages."""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products

BASE_URL = "https://www.bachhoaxanh.com"
DISCOVERY_SITEMAP_URLS = [
    f"{BASE_URL}/sitemap.xml",
    f"{BASE_URL}/sitemap_index.xml",
    f"{BASE_URL}/sitemap-products.xml",
    f"{BASE_URL}/robots.txt",
]
SEED_PAGES = [
    f"{BASE_URL}/",
    f"{BASE_URL}/vi",
    f"{BASE_URL}/products",
    f"{BASE_URL}/danh-muc",
]

MERCHANT_DEFAULTS = {
    "source": "bach_hoaxanh_vn",
    "merchant_id": "bach_hoaxanh_vn",
    "region": "VN",
    "country_code": "VN",
    "currency": "VND",
    "platform": "custom",
    "is_active": True,
    "in_stock": True,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TIMEOUT = 30
MAX_WORKERS = 8


def fetch(url: str, retries: int = 2) -> str | None:
    for _ in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception:
            continue
    return None


def _parse_sitemap(xml_text: str) -> tuple[list[str], bool]:
    """Return parsed urls and whether input is a sitemap index."""
    soup = BeautifulSoup(xml_text, "xml")
    locs = [loc.get_text().strip() for loc in soup.find_all("loc")]
    return locs, bool(soup.find_all("sitemap"))


def _extract_domain_urls(urls: list[str], base_url: str) -> list[str]:
    return [
        u for u in urls
        if u.startswith(base_url)
        and "googleusercontent.com" not in u
        and " " not in u
    ]


def _collect_sitemap_urls() -> list[str]:
    sitemap_urls: list[str] = []
    seen: set[str] = set()
    attempted: list[str] = []

    for candidate in DISCOVERY_SITEMAP_URLS:
        attempted.append(candidate)
        text = fetch(candidate)
        if not text:
            continue
        if candidate.endswith("robots.txt"):
            for line in text.splitlines():
                if line.lower().startswith("sitemap:"):
                    robots_url = line.split(":", 1)[1].strip()
                    if robots_url and robots_url.startswith("http") and robots_url not in seen:
                        seen.add(robots_url)
                        sitemap_urls.append(robots_url)
            continue
        urls, is_index = _parse_sitemap(text)
        if is_index:
            for url in urls:
                if url and url not in seen:
                    seen.add(url)
                    sitemap_urls.append(url)
        elif urls:
            if "sitemap" in candidate:
                if candidate not in seen:
                    seen.add(candidate)
                    sitemap_urls.append(candidate)

    if sitemap_urls:
        return sitemap_urls

    print("Bach Hoa Xanh discovery blocked; checked:", file=sys.stderr)
    for source in attempted:
        print(f"  - {source}", file=sys.stderr)
    return []


def _collect_product_urls() -> list[str]:
    product_urls: list[str] = []
    seen: set[str] = set()

    # 1) Parse sitemap index + direct sitemap outputs
    for sitemap_url in _collect_sitemap_urls():
        text = fetch(sitemap_url)
        if not text:
            continue
        urls, is_index = _parse_sitemap(text)
        if is_index:
            for nested in urls:
                nested_xml = fetch(nested)
                if not nested_xml:
                    continue
                nested_urls, _ = _parse_sitemap(nested_xml)
                for u in _extract_domain_urls(nested_urls, BASE_URL):
                    if u not in seen:
                        seen.add(u)
                        product_urls.append(u)
        else:
            for u in _extract_domain_urls(urls, BASE_URL):
                if u not in seen:
                    seen.add(u)
                    product_urls.append(u)

    # 2) Optional fallback: seed pages with linked product URLs
    if not product_urls:
        for seed in SEED_PAGES:
            html = fetch(seed)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]
                full = href
                if href.startswith("/"):
                    full = urljoin(BASE_URL, href)
                if not full.startswith("http"):
                    continue
                parsed = urlparse(full)
                if "bachhoaxanh.com" not in parsed.netloc and parsed.netloc not in {"bachhoaxanh.com"}:
                    continue
                path = (parsed.path or "").strip("/")
                if not path:
                    continue
                if re.search(r"([A-Za-z0-9]+--[A-Za-z0-9]+)", path):
                    if full not in seen:
                        seen.add(full)
                        product_urls.append(full)

    return product_urls


def _parse_price(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).strip()
    if not text:
        return None
    return text.replace(",", "")


def _extract_product(html: str, url: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        content = script.string
        if not content:
            continue
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict) or payload.get("@type") != "Product":
            continue

        brand = payload.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        offers = payload.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if not isinstance(offers, dict):
            offers = {}

        price = _parse_price(offers.get("price"))
        if price is None:
            # Fallback to priceRange / listPrice style fields if present.
            for key in ("lowPrice", "highPrice", "price", "amount"):
                candidate = payload.get(key)
                price = _parse_price(candidate)
                if price:
                    break

        sku = payload.get("sku")
        if not sku:
            sku_match = re.search(r"--([A-Za-z0-9]+)$", url)
            sku = sku_match.group(1) if sku_match else None
        if not sku:
            return None

        image = payload.get("image")
        image_url = None
        if isinstance(image, list) and image:
            image_url = image[0]
        elif isinstance(image, str):
            image_url = image

        category = payload.get("category") or "grocery"
        category_path = None
        if isinstance(category, list):
            category_path = category
        elif category:
            category_path = [category]

        availability = offers.get("availability", "")
        in_stock = True
        if isinstance(availability, str):
            in_stock = "instock" in availability.lower()

        return {
            "sku": sku,
            "title": payload.get("name", ""),
            "price": price,
            "url": payload.get("url", url),
            "brand": brand,
            "image_url": image_url,
            "category": category,
            "category_path": category_path,
            "in_stock": in_stock,
            "source": "bach_hoaxanh_vn",
            "merchant_id": "bach_hoaxanh_vn",
            "raw_data": payload,
        }
    return None


def _scrape_product(url: str) -> dict[str, Any] | None:
    html = fetch(url)
    if not html:
        return None
    return _extract_product(html, url)


def scrape_products(urls: list[str]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    total = len(urls)
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_scrape_product, url): url for url in urls}
        for fut in as_completed(futures):
            done += 1
            try:
                product = fut.result()
            except Exception:
                product = None
            if product:
                products.append(product)
            if done % 100 == 0:
                print(f"  Progress: {done}/{total}", file=sys.stderr)
    print(f"Scraped {len(products)}/{total} product pages", file=sys.stderr)
    return products


def dedupe(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for product in products:
        key = str(product.get("sku") or product.get("url", ""))
        if key and key not in seen:
            seen[key] = product
    return list(seen.values())


def write_snapshot(products: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for product in products:
            file.write(json.dumps(product, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bach Hoa XANH VN grocery ingestion")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "merchants" / "bach_hoaxanh_vn_2026-06-19.ndjson",
    )
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-products", type=int, default=None)
    args = parser.parse_args()

    if not args.skip_ingest:
        assert_ingestion_allowed()

    targets = configured_database_targets()
    print("Targets:", json.dumps(targets, indent=2), file=sys.stderr)

    product_urls = _collect_product_urls()
    print(f"Discovered product URLs: {len(product_urls)}", file=sys.stderr)
    if not product_urls:
        print(
            "FATAL: no product discovery source reachable for Bach Hoa Xanh VN "
            "(try providing network/proxy access).",
            file=sys.stderr,
        )
        return 1

    urls = product_urls if args.max_products is None else product_urls[: args.max_products]
    products = scrape_products(urls)
    deduped = dedupe(products)
    print(f"Deduped: {len(deduped)}", file=sys.stderr)

    write_snapshot(deduped, args.output)
    print(f"Snapshot: {args.output}", file=sys.stderr)

    ingested = 0
    if not args.skip_ingest:
        ingested = upsert_products(
            deduped,
            source="bach_hoaxanh_vn",
            merchant_id="bach_hoaxanh_vn",
            defaults=MERCHANT_DEFAULTS,
            metadata_tag={"script": "ingest_bach_hoaxanh_vn.py"},
        )
        print(f"Ingested: {ingested}", file=sys.stderr)

    result = {
        "merchant_id": "bach_hoaxanh_vn",
        "discovered": len(product_urls),
        "scraped": len(products),
        "deduped": len(deduped),
        "ingested": ingested,
        "output": str(args.output),
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

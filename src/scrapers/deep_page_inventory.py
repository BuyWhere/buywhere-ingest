"""Deep-page inventory/availability enrichment for product URLs.

Reads product listings (NDJSON) with URLs and enriches each row with
inventory/availability data by scraping the product detail page.

Targeted at the courts_sg, shopify and similar scrapers that already
expose a product URL but no in_stock signal.

Output schema per row (NDJSON):
  sku, url, in_stock, availability_text, brand
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.scrapers.base_scraper import BaseScraper


class DeepPageInventoryScraper(BaseScraper):
    """Scrape product detail pages for inventory/availability signals."""

    STOCK_OUT_PATTERNS = [
        r"out\s*of\s*stock",
        r"sold\s*out",
        r"unavailable",
        r"not\s*available",
        r"discontinued",
        r"no\s*longer\s*available",
    ]

    IN_STOCK_PATTERNS = [
        r"in\s*stock",
        r"available",
        r"add\s*to\s*cart",
        r"buy\s*now",
        r"ready\s*to\s*ship",
    ]

    def __init__(self, merchant_name: str = "deeppage", base_url: str = ""):
        super().__init__(merchant_name, base_url or "https://example.com")

    async def enrich(self, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for product in products:
            url = product.get("url")
            if not url:
                enriched.append({**product, "in_stock": None, "availability_text": None})
                continue
            try:
                html = await self.fetch(url)
            except Exception as exc:
                enriched.append({
                    **product,
                    "in_stock": None,
                    "availability_text": None,
                    "fetch_error": str(exc),
                })
                continue
            in_stock, availability_text = self._parse_inventory(html)
            enriched.append({
                **product,
                "in_stock": in_stock,
                "availability_text": availability_text,
            })
            await asyncio.sleep(0.25)
        return enriched

    async def _scrape_impl(self, products: list) -> None:
        pass

    def _parse_inventory(self, html: Optional[str]) -> tuple[Optional[bool], Optional[str]]:
        if not html:
            return None, None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # 1) JSON-LD Product offers.availability
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            raw = script.string
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            entries = payload if isinstance(payload, list) else [payload]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                offers = entry.get("offers")
                offer_list = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
                for offer in offer_list:
                    if not isinstance(offer, dict):
                        continue
                    availability = offer.get("availability", "")
                    if availability:
                        in_stock = availability.endswith("InStock")
                        return in_stock, availability

        # 2) Shopify-style inline product JSON
        for script in soup.find_all("script"):
            text = script.string or ""
            if "var product" not in text and "window.product" not in text:
                continue
            match = re.search(r"var\s+product\s*=\s*(\{.*?\});", text, re.DOTALL)
            if not match:
                match = re.search(r"window\.product\s*=\s*(\{.*?\});", text, re.DOTALL)
            if not match:
                continue
            try:
                product_json = json.loads(match.group(1))
            except Exception:
                continue
            variants = product_json.get("variants", [])
            if variants:
                first = variants[0]
                available = first.get("available")
                if available is not None:
                    return bool(available), "Shopify variant available={}".format(available)

        # 3) Stock/inventory/availability DOM nodes
        for elem in soup.find_all(["span", "div", "p"], class_=re.compile(r"stock|inventory|availability", re.I)):
            text = elem.get_text(" ", strip=True)
            if not text:
                continue
            lowered = text.lower()
            for pattern in self.STOCK_OUT_PATTERNS:
                if re.search(pattern, lowered):
                    return False, text
            for pattern in self.IN_STOCK_PATTERNS:
                if re.search(pattern, lowered):
                    return True, text

        # 4) Add-to-cart button heuristic
        add_btn = soup.find("button", string=re.compile(r"add\s*to\s*cart|add\s*to\s*bag|buy\s*now", re.I))
        if add_btn:
            disabled = add_btn.get("disabled")
            if disabled is not None and disabled is not False:
                return False, add_btn.get_text(strip=True)
            return True, add_btn.get_text(strip=True)

        return None, None


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input NDJSON with product URLs")
    parser.add_argument("--output", required=True, help="Output NDJSON with in_stock data")
    parser.add_argument("--limit", type=int, default=0, help="Optional max records (0 = no limit)")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as fh:
        products = [json.loads(line) for line in fh if line.strip()]
    if args.limit:
        products = products[: args.limit]

    scraper = DeepPageInventoryScraper()
    async with scraper:
        enriched = await scraper.enrich(products)

    with open(args.output, "w", encoding="utf-8") as fh:
        for row in enriched:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    in_stock_count = sum(1 for r in enriched if r.get("in_stock") is True)
    out_of_stock_count = sum(1 for r in enriched if r.get("in_stock") is False)
    unknown = sum(1 for r in enriched if r.get("in_stock") is None)
    print(
        f"enriched={len(enriched)} in_stock={in_stock_count} "
        f"out_of_stock={out_of_stock_count} unknown={unknown}"
    )


if __name__ == "__main__":
    asyncio.run(main())

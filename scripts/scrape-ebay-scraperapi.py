#!/usr/bin/env python3
"""
eBay US product scraper using ScraperAPI — no eBay Developer credentials needed.

Uses ScraperAPI to bypass eBay's IP blocks and scrape real product listings
from eBay search results pages. Uploads to R2 and runs Checkpoint B in-process.

Required env vars:
    SCRAPERAPI_KEY
    CLOUDFLARE_R2_ACCOUNT_ID
    CLOUDFLARE_R2_ACCESS_KEY_ID
    CLOUDFLARE_R2_SECRET_ACCESS_KEY
    CLOUDFLARE_R2_BUCKET           (defaults to 'buywhere-data')

Usage:
    SCRAPERAPI_KEY=xxx python3 scripts/scrape-ebay-scraperapi.py
    python3 scripts/scrape-ebay-scraperapi.py --target 5000 --delay 0.5
    python3 scripts/scrape-ebay-scraperapi.py --dry-run   # no R2 upload
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, quote

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

MERCHANT_ID = "ebay_us"
BUCKET = (os.environ.get("CLOUDFLARE_R2_BUCKET") or "Buywhere-data").lower()
R2_ACCOUNT_ID = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY = os.environ.get("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE = "https://api.scraperapi.com/"

# Checkpoint B thresholds
ZERO_PRICE_MAX_PCT = 5
NULL_IMAGE_MAX_PCT = 50
PLACEHOLDER_TITLE_MAX_PCT = 10
PLACEHOLDER_RE = re.compile(r"^ebay item\s+\d+", re.IGNORECASE)

KNOWN_BRANDS = [
    "Apple", "Samsung", "Sony", "LG", "Dell", "HP", "Lenovo", "Nike", "Adidas",
    "Canon", "Nikon", "Bose", "JBL", "Dyson", "Asus", "Acer", "Microsoft", "Google",
    "Panasonic", "Sharp", "Toshiba", "Motorola", "TCL", "Fujifilm", "GoPro", "DJI",
    "Fitbit", "Garmin", "Fossil", "Casio", "Seiko", "Converse", "Vans",
    "New Balance", "Puma", "Reebok", "Under Armour", "North Face", "Coach",
]

SEARCH_QUERIES = [
    ("Electronics", "laptop computer"),
    ("Electronics", "smartphone android"),
    ("Electronics", "headphones wireless bluetooth"),
    ("Electronics", "smart tv 4k"),
    ("Electronics", "gaming console"),
    ("Electronics", "digital camera"),
    ("Electronics", "tablet ipad"),
    ("Electronics", "smart watch fitness tracker"),
    ("Fashion", "women dress summer"),
    ("Fashion", "men sneakers shoes"),
    ("Fashion", "handbag purse leather"),
    ("Fashion", "jewelry necklace gold"),
    ("Fashion", "men shirt jacket"),
    ("Home & Garden", "sofa couch furniture"),
    ("Home & Garden", "kitchen appliances"),
    ("Home & Garden", "coffee maker espresso"),
    ("Home & Garden", "air purifier"),
    ("Sporting Goods", "exercise bike gym"),
    ("Sporting Goods", "running shoes outdoor"),
    ("Toys & Games", "LEGO building blocks"),
    ("Toys & Games", "board game family"),
    ("Collectibles", "trading cards basketball"),
    ("Auto Parts", "car accessories truck"),
    ("Beauty", "skincare serum face"),
    ("Health", "vitamins supplements protein"),
    ("Books", "bestseller fiction novel"),
    ("Electronics", "portable speaker bluetooth"),
    ("Electronics", "electric scooter bike"),
    ("Home & Garden", "vacuum cleaner robot"),
    ("Fashion", "sunglasses designer"),
]


# ── AWS Sig V4 for R2 ────────────────────────────────────────────────────────

def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _signing_key(secret: str, date_str: str) -> bytes:
    k = _hmac(f"AWS4{secret}".encode(), date_str)
    k = _hmac(k, "auto")
    k = _hmac(k, "s3")
    return _hmac(k, "aws4_request")


def r2_put(key: str, body: bytes) -> None:
    now = datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_str = amz_date[:8]
    host = f"{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    content_type = "application/x-ndjson"
    payload_hash = hashlib.sha256(body).hexdigest()
    cred_scope = f"{date_str}/auto/s3/aws4_request"
    credential = f"{R2_ACCESS_KEY}/{cred_scope}"
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"

    canonical_req = "\n".join([
        "PUT",
        f"/{BUCKET}/{key}",
        "",
        f"content-type:{content_type}\nhost:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n",
        signed_headers,
        payload_hash,
    ])
    str_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        cred_scope,
        hashlib.sha256(canonical_req.encode()).hexdigest(),
    ])
    signature = hmac.new(
        _signing_key(R2_SECRET_KEY, date_str),
        str_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    resp = requests.put(
        f"{R2_ENDPOINT}/{BUCKET}/{key}",
        data=body,
        headers={
            "Authorization": f"AWS4-HMAC-SHA256 Credential={credential},SignedHeaders={signed_headers},Signature={signature}",
            "Content-Type": content_type,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_hash,
        },
        timeout=120,
        verify=False,
    )
    resp.raise_for_status()
    log.info("Uploaded R2 key: %s (%d bytes)", key, len(body))


# ── ScraperAPI + eBay HTML parsing ───────────────────────────────────────────

def scraper_get(url: str, retries: int = 3) -> requests.Response:
    """Fetch a URL via ScraperAPI with retry."""
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url,
        "render": "true",
        "country_code": "us",
    }
    for attempt in range(retries):
        try:
            resp = requests.get(
                SCRAPERAPI_BASE,
                params=params,
                timeout=60,
            )
            if resp.status_code == 200:
                return resp
            log.warning("ScraperAPI attempt %d: HTTP %d for %s", attempt + 1, resp.status_code, url)
        except requests.RequestException as e:
            log.warning("ScraperAPI attempt %d error: %s", attempt + 1, e)
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return None


def _extract_brand(title: str) -> str:
    tl = title.lower()
    for brand in KNOWN_BRANDS:
        bl = brand.lower()
        if tl.startswith(bl) or f" {bl} " in tl or f" {bl}-" in tl:
            return brand
    return ""


def parse_ebay_search(html: str, category_name: str) -> list[dict]:
    """Parse eBay search results page and return product dicts."""
    soup = BeautifulSoup(html, "html.parser")
    products = []

    # Find all real product links (real item IDs are 10+ digits; placeholders use 123456)
    all_a = soup.find_all("a", href=True)
    product_links = [
        a for a in all_a
        if re.search(r"/itm/\d{10,}", a.get("href", ""))
        and a.get_text(strip=True)
        and a.get_text(strip=True).lower() not in ("shop on ebay",)
    ]

    log.debug("Found %d real product links", len(product_links))

    seen_ids: set = set()
    for a in product_links:
        title = re.sub(r"^New Listing\s*", "", a.get_text(strip=True), flags=re.IGNORECASE).strip()
        href = a.get("href", "")
        m = re.search(r"/itm/(\d+)", href)
        if not m:
            continue
        item_id = m.group(1)
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        if not title or len(title) < 5 or PLACEHOLDER_RE.match(title):
            continue

        item_url = f"https://www.ebay.com/itm/{item_id}"

        # Walk up DOM to find price and image in the containing card
        price = 0.0
        image_url = ""
        parent = a.parent
        for _ in range(12):
            if parent is None:
                break
            # Price: look for $XX.XX patterns in text nodes
            if not price:
                price_texts = parent.find_all(string=re.compile(r"\$[\d,]+\.?\d*"))
                if price_texts:
                    nums = re.findall(r"[\d,]+\.?\d*", price_texts[0].replace(",", ""))
                    if nums:
                        try:
                            price = float(nums[0])
                        except ValueError:
                            pass
            # Image from i.ebayimg.com
            if not image_url:
                img = parent.find("img", src=re.compile(r"i\.ebayimg\.com"))
                if img:
                    image_url = img.get("src", "")
            if price and image_url:
                break
            parent = parent.parent

        brand = _extract_brand(title)

        products.append({
            "sku": f"ebay_us_{item_id}",
            "merchant_id": MERCHANT_ID,
            "title": title,
            "description": "",
            "price": price,
            "currency": "USD",
            "url": item_url,
            "image_url": image_url,
            "category": category_name,
            "category_path": [category_name],
            "brand": brand,
            "is_active": True,
            "is_available": True,
            "metadata": {
                "item_id": item_id,
                "source": "ebay_us_scraperapi",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
        })

    return products


def search_ebay(query: str, category_name: str, page: int = 1) -> list[dict]:
    """Fetch one page of eBay search results via ScraperAPI."""
    params = urlencode({
        "_nkw": query,
        "_ipg": "200",
        "_pgn": str(page),
        "_sop": "12",  # sort by best match
    })
    url = f"https://www.ebay.com/sch/i.html?{params}"
    log.debug("Fetching: %s (page %d)", url, page)

    resp = scraper_get(url)
    if not resp:
        log.warning("Failed to fetch eBay search page for %r (page %d)", query, page)
        return []

    products = parse_ebay_search(resp.text, category_name)
    log.debug("Parsed %d products from %r page %d", len(products), query, page)
    return products


def scrape_all(target: int, delay: float) -> list[dict]:
    """Scrape across all search queries until target is met."""
    products: list[dict] = []
    seen: set = set()

    for cat_name, query in SEARCH_QUERIES:
        if len(products) >= target:
            break

        log.info("[%s] query=%r (total so far: %d/%d)", cat_name, query, len(products), target)

        for page in range(1, 6):  # up to 5 pages per query
            if len(products) >= target:
                break

            batch = search_ebay(query, cat_name, page)
            if not batch:
                break

            added = 0
            for p in batch:
                if p["sku"] not in seen:
                    seen.add(p["sku"])
                    products.append(p)
                    added += 1

            log.info("  page=%d → %d new items (total: %d)", page, added, len(products))

            if added == 0 or len(batch) < 10:
                break

            time.sleep(delay)

        time.sleep(delay * 0.5)

    return products


# ── Checkpoint B ─────────────────────────────────────────────────────────────

def run_checkpoint_b(products: list[dict]) -> dict:
    total = len(products)
    if total == 0:
        return {"pass": False, "total": 0, "violations": ["empty batch"]}

    zero_price = sum(1 for p in products if not p.get("price") or float(p.get("price", 0) or 0) == 0)
    null_image = sum(1 for p in products if not p.get("image_url"))
    placeholder = sum(1 for p in products if PLACEHOLDER_RE.match((p.get("title") or "").strip()))

    zp_pct = 100 * zero_price / total
    ni_pct = 100 * null_image / total
    ph_pct = 100 * placeholder / total

    violations = []
    if zp_pct > ZERO_PRICE_MAX_PCT:
        violations.append(f"zero_price {zp_pct:.1f}% > threshold {ZERO_PRICE_MAX_PCT}%")
    if ni_pct > NULL_IMAGE_MAX_PCT:
        violations.append(f"null_image {ni_pct:.1f}% > threshold {NULL_IMAGE_MAX_PCT}%")
    if ph_pct > PLACEHOLDER_TITLE_MAX_PCT:
        violations.append(f"placeholder_title {ph_pct:.1f}% > threshold {PLACEHOLDER_TITLE_MAX_PCT}%")

    return {
        "pass": len(violations) == 0,
        "total": total,
        "zeroPricePct": zp_pct,
        "nullImagePct": ni_pct,
        "placeholderTitlePct": ph_pct,
        "violations": violations,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import warnings
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(description="eBay US ScraperAPI scraper for BUY-30579")
    parser.add_argument("--target", type=int, default=5000, help="Target number of products")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Skip R2 upload, write locally only")
    args = parser.parse_args()

    if not SCRAPERAPI_KEY:
        log.error(
            "Missing SCRAPERAPI_KEY env var.\n"
            "  Set SCRAPERAPI_KEY to the ScraperAPI key (already in Railway buywhere-api env vars).\n"
            "  This scraper does NOT require eBay Developer credentials."
        )
        sys.exit(1)

    if not args.dry_run and (not R2_ACCOUNT_ID or not R2_ACCESS_KEY or not R2_SECRET_KEY):
        log.error("Missing R2 credentials. Set CLOUDFLARE_R2_ACCOUNT_ID, CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        sys.exit(1)

    # Verify bs4 is available
    try:
        from bs4 import BeautifulSoup  # noqa
    except ImportError:
        log.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4")
        sys.exit(1)

    log.info("Starting eBay US ScraperAPI scraper (target=%d, key=...%s)", args.target, SCRAPERAPI_KEY[-6:])
    start_ts = datetime.now(timezone.utc)

    products = scrape_all(args.target, args.delay)
    log.info("Total scraped: %d products", len(products))

    if not products:
        log.error("No products scraped — aborting")
        sys.exit(1)

    # Checkpoint B
    result = run_checkpoint_b(products)
    log.info(
        "Checkpoint B: %s  (total=%d, zero_price=%.1f%%, null_image=%.1f%%, placeholder=%.1f%%)",
        "PASS" if result["pass"] else "BLOCKED",
        result["total"],
        result["zeroPricePct"],
        result["nullImagePct"],
        result["placeholderTitlePct"],
    )

    if not result["pass"]:
        for v in result["violations"]:
            log.error("  Violation: %s", v)
        log.error("Checkpoint B BLOCKED — not uploading to R2.")
        sys.exit(1)

    # Write and upload
    timestamp = start_ts.strftime("%Y%m%d_%H%M%S")
    r2_key = f"scraping/ebay_us/products_{timestamp}.jsonl"
    local_path = f"/tmp/ebay_us_products_{timestamp}.jsonl"

    body = "\n".join(json.dumps(p, ensure_ascii=False) for p in products) + "\n"
    body_bytes = body.encode("utf-8")

    with open(local_path, "wb") as fh:
        fh.write(body_bytes)
    log.info("Written locally: %s", local_path)

    if not args.dry_run:
        r2_put(r2_key, body_bytes)
        print(f"\nCheckpoint B: PASS")
        print(f"R2 key: {r2_key}")
        print(f"Products: {len(products)}")
        print(f"zero_price: {result['zeroPricePct']:.1f}%")
        print(f"null_image: {result['nullImagePct']:.1f}%")
        print(f"placeholder_title: {result['placeholderTitlePct']:.1f}%")
        print(f"\nRun full audit: cd buywhere-ingest && npm run audit:ebay {r2_key}")
    else:
        log.info("Dry run — R2 upload skipped. File: %s", local_path)
        print(f"\nDry run complete.")
        print(f"Checkpoint B: PASS")
        print(f"Products scraped: {len(products)}")
        print(f"zero_price: {result['zeroPricePct']:.1f}%")
        print(f"null_image: {result['nullImagePct']:.1f}%")
        print(f"placeholder_title: {result['placeholderTitlePct']:.1f}%")
        print(f"Local: {local_path}")


if __name__ == "__main__":
    main()

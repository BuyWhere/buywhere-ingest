#!/usr/bin/env python3
"""
eBay US real product scraper for BUY-30579.

Uses the eBay Browse API (modern replacement for deprecated Finding API) to
fetch real product listings including images, then uploads to R2 and runs
Checkpoint B in-process before reporting success.

Required env vars:
    EBAY_CLIENT_ID                  eBay Developer Client ID
    EBAY_CLIENT_SECRET              eBay Developer Client Secret
    CLOUDFLARE_R2_ACCOUNT_ID
    CLOUDFLARE_R2_ACCESS_KEY_ID
    CLOUDFLARE_R2_SECRET_ACCESS_KEY
    CLOUDFLARE_R2_BUCKET           (defaults to 'buywhere-data')

Get free eBay API credentials at https://developer.ebay.com/
  → My Account → Get API Keys → Create App → copy Client ID + Client Secret

Usage:
    EBAY_CLIENT_ID=xxx EBAY_CLIENT_SECRET=yyy python3 scripts/scrape-ebay-pdp.py
    python3 scripts/scrape-ebay-pdp.py --target 5000 --delay 0.2
    python3 scripts/scrape-ebay-pdp.py --dry-run   # no R2 upload
"""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

MERCHANT_ID = "ebay_us"
BUCKET = (os.environ.get("CLOUDFLARE_R2_BUCKET") or "Buywhere-data").lower()
R2_ACCOUNT_ID = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY = os.environ.get("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_SEARCH = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope"

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


# ── eBay Browse API ──────────────────────────────────────────────────────────

def get_ebay_token(client_id: str, client_secret: str) -> str:
    """Obtain a client-credentials OAuth Bearer token."""
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        EBAY_TOKEN_URL,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=f"grant_type=client_credentials&scope={quote(EBAY_SCOPE)}",
        timeout=30,
        verify=False,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in response: {resp.text[:200]}")
    log.info("OAuth token obtained (expires in %ds)", resp.json().get("expires_in", 0))
    return token


def _extract_brand(title: str) -> str:
    tl = title.lower()
    for brand in KNOWN_BRANDS:
        bl = brand.lower()
        if tl.startswith(bl) or f" {bl} " in tl or f" {bl}-" in tl:
            return brand
    return ""


def search_ebay(token: str, query: str, category_name: str, limit: int = 200, offset: int = 0) -> list[dict]:
    """Call Browse API search and return transformed product dicts."""
    params = {
        "q": query,
        "limit": str(min(limit, 200)),
        "offset": str(offset),
        "fieldgroups": "MATCHING_ITEMS,ASPECT_REFINEMENTS",
    }
    resp = requests.get(
        EBAY_BROWSE_SEARCH,
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=30,
        verify=False,
    )

    if resp.status_code == 401:
        raise ValueError("Token expired or invalid — re-authenticate")
    if resp.status_code != 200:
        log.warning("Browse API %s for %r: %s", resp.status_code, query, resp.text[:200])
        return []

    data = resp.json()
    items = data.get("itemSummaries", [])
    products = []

    for item in items:
        title = item.get("title", "").strip()
        if not title or PLACEHOLDER_RE.match(title):
            continue

        price_obj = item.get("price", {})
        price = float(price_obj.get("value", 0) or 0)

        image_obj = item.get("image", {})
        image_url = image_obj.get("imageUrl", "") if isinstance(image_obj, dict) else ""

        item_url = item.get("itemWebUrl", "")
        item_id_m = re.search(r"/itm/(\d+)", item_url)
        item_id = item_id_m.group(1) if item_id_m else item.get("itemId", "").replace("|", "_")

        cats = item.get("categories", [])
        cat_name = cats[0].get("categoryName", "") if cats else ""

        condition = item.get("condition", "")
        seller = (item.get("seller") or {}).get("username", "")

        brand = _extract_brand(title)

        products.append({
            "sku": f"ebay_us_{item_id}",
            "merchant_id": MERCHANT_ID,
            "title": title,
            "description": f"Condition: {condition}" if condition else "",
            "price": price,
            "currency": price_obj.get("currency", "USD"),
            "url": item_url,
            "image_url": image_url,
            "category": category_name,
            "category_path": [category_name, cat_name],
            "brand": brand,
            "is_active": True,
            "is_available": True,
            "metadata": {
                "item_id": item_id,
                "source": "ebay_us_browse_api",
                "condition": condition,
                "seller": seller,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
        })

    return products


def scrape_all(client_id: str, client_secret: str, target: int, delay: float) -> list[dict]:
    """Scrape across all search queries until target is met."""
    token = get_ebay_token(client_id, client_secret)
    token_fetched_at = time.time()

    products: list[dict] = []
    seen: set = set()

    for cat_name, query in SEARCH_QUERIES:
        if len(products) >= target:
            break

        # Refresh token if older than 90 minutes
        if time.time() - token_fetched_at > 5400:
            token = get_ebay_token(client_id, client_secret)
            token_fetched_at = time.time()

        log.info("[%s] query=%r (total so far: %d/%d)", cat_name, query, len(products), target)
        offset = 0

        while len(products) < target:
            batch = search_ebay(token, query, cat_name, limit=200, offset=offset)
            if not batch:
                break

            added = 0
            for p in batch:
                if p["sku"] not in seen:
                    seen.add(p["sku"])
                    products.append(p)
                    added += 1

            log.info("  offset=%d → %d new items (total: %d)", offset, added, len(products))

            if added == 0 or len(batch) < 200:
                break
            offset += 200
            time.sleep(delay)

        time.sleep(delay)

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

    parser = argparse.ArgumentParser(description="eBay US Browse API scraper for BUY-30579")
    parser.add_argument("--target", type=int, default=5000, help="Target number of products")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Skip R2 upload, write locally only")
    args = parser.parse_args()

    client_id = os.environ.get("EBAY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        log.error(
            "Missing eBay API credentials.\n"
            "  Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET env vars.\n"
            "  Get free credentials at: https://developer.ebay.com/\n"
            "  Steps:\n"
            "    1. Sign in or create an eBay account\n"
            "    2. Go to My Account → Get API Keys\n"
            "    3. Create a new application\n"
            "    4. Copy the Client ID and Client Secret\n"
            "    5. Set EBAY_CLIENT_ID=<Client ID> EBAY_CLIENT_SECRET=<Client Secret>"
        )
        sys.exit(1)

    if not R2_ACCOUNT_ID or not R2_ACCESS_KEY or not R2_SECRET_KEY:
        log.error("Missing R2 credentials. Set CLOUDFLARE_R2_ACCOUNT_ID, CLOUDFLARE_R2_ACCESS_KEY_ID, CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        sys.exit(1)

    log.info("Starting eBay US Browse API scraper (target=%d)", args.target)
    start_ts = datetime.now(timezone.utc)

    products = scrape_all(client_id, client_secret, args.target, args.delay)
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
        log.error("Checkpoint B BLOCKED — not uploading to R2. Scrape with different params or investigate API response.")
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
        print(f"\nDry run complete. Local: {local_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Live non-emergency catalog scrape + ingest runner for BUY-29210 / BUY-29216 / BUY-29217.

Note (BUY-33089): this script scrapes merchant pages live and writes the
resulting products directly to the catalog DB — there is no on-disk
artifact file to mark. The per-file ``.ingested.json`` completion marker
pattern therefore does not apply here; the catalog upsert IS the durable
proof of ingest. Live-scrape output is in the DB, not in a file the
safe-data-cleanup.sh routine can reach. If a future caller wants per-run
audit markers, dump the batch to a temp file and call
``scripts.ingested_marker.finalize_marker`` against it after upsert.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ingestion_guard import assert_ingestion_allowed, configured_database_targets
from src.catalog_ingest import upsert_products
from src.scrapers.courts_sg import CourtsSGScraper
from src.scrapers.floor_and_decor import FloorAndDecorScraper
from src.scrapers.paper_source import PaperSourceScraper
from src.scrapers.the_body_shop import TheBodyShopScraper
from src.scrapers.woocommerce import WooCommerceScraper
from src.scrapers.shopify_store import ShopifyScraper
from src.scrapers.zalora_sg import ZaloraSGScraper
from src.scrapers.tokopedia import TokopediaScraper
from src.scrapers.eveandboy import EveandboyScraper


SCRAPER_CONFIG = {
    "paper_source": {
        "factory": lambda limit: PaperSourceScraper(max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "paper_source",
            "source": "paper_source",
            "platform": "shopify",
            "region": "US",
            "country_code": "US",
            "currency": "USD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "floor_and_decor": {
        "factory": lambda limit: FloorAndDecorScraper(max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "floor_and_decor",
            "source": "floor_and_decor",
            "platform": "custom",
            "region": "US",
            "country_code": "US",
            "currency": "USD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "the_body_shop": {
        "factory": lambda limit: TheBodyShopScraper(max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "the_body_shop",
            "source": "the_body_shop",
            "platform": "shopify",
            "region": "UK",
            "country_code": "GB",
            "currency": "GBP",
            "is_active": True,
            "in_stock": True,
        },
    },
    "courts_sg": {
        "factory": lambda limit: CourtsSGScraper(),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "courts_sg",
            "source": "courts_sg",
            "platform": "custom",
            "region": "SG",
            "country_code": "SG",
            "currency": "SGD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "woocommerce": {
        "factory": lambda limit, base_url: WooCommerceScraper(base_url=base_url, max_products=limit),
        "enabled_by_default": False,
        "disabled_reason": "requires --woocommerce-base-url or WOOCOMMERCE_BASE_URL",
        "defaults": {
            "merchant_id": "woocommerce",
            "source": "woocommerce",
            "platform": "woocommerce",
            "region": "US",
            "country_code": "US",
            "currency": "USD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "zalora_sg": {
        "factory": lambda limit: ZaloraSGScraper(max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "zalora_sg",
            "source": "zalora_sg",
            "platform": "custom",
            "region": "SG",
            "country_code": "SG",
            "currency": "SGD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "tokopedia": {
        "factory": lambda limit: TokopediaScraper(max_products=limit),
        "enabled_by_default": False,
        "disabled_reason": "Tokopedia is a protected domain on ScraperAPI (requires premium=true); BrightData proxy zone also unreachable",
        "defaults": {
            "merchant_id": "tokopedia",
            "source": "tokopedia",
            "platform": "custom",
            "region": "ID",
            "country_code": "ID",
            "currency": "IDR",
            "is_active": True,
            "in_stock": True,
        },
    },
    "newchapter": {
        "factory": lambda limit: ShopifyScraper(base_url="https://newchapter.com", max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "newchapter",
            "source": "newchapter",
            "platform": "shopify",
            "region": "US",
            "country_code": "US",
            "currency": "USD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "allbirds": {
        "factory": lambda limit: ShopifyScraper(base_url="https://www.allbirds.com", max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "allbirds",
            "source": "allbirds",
            "platform": "shopify",
            "region": "US",
            "country_code": "US",
            "currency": "USD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "muji_us": {
        "factory": lambda limit: ShopifyScraper(base_url="https://www.muji.us", max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "muji_us",
            "source": "muji_us",
            "platform": "shopify",
            "region": "US",
            "country_code": "US",
            "currency": "USD",
            "is_active": True,
            "in_stock": True,
        },
    },
    "eveandboy": {
        "factory": lambda limit: EveandboyScraper(max_products=limit),
        "enabled_by_default": True,
        "defaults": {
            "merchant_id": "eveandboy_th",
            "source": "eveandboy",
            "platform": "custom",
            "region": "TH",
            "country_code": "TH",
            "currency": "THB",
            "is_active": True,
            "in_stock": True,
        },
    },
}

DEFAULT_CONCURRENCY = 3
DEFAULT_ISSUE_TAG = os.environ.get("PAPERCLIP_TASK_ID", "BUY-29216")


def _default_all_merchants() -> list[str]:
    return sorted(
        key for key, config in SCRAPER_CONFIG.items() if config.get("enabled_by_default", True)
    )


def _default_all_skips() -> dict[str, str]:
    return {
        key: config["disabled_reason"]
        for key, config in SCRAPER_CONFIG.items()
        if not config.get("enabled_by_default", True)
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape live merchant pages and upsert directly into the canonical catalog DB pin."
    )
    parser.add_argument(
        "merchant_key",
        nargs="*",
        default=[],
        help="Merchant key(s). Omit or use --all for all configured merchants.",
    )
    parser.add_argument("--all", action="store_true", help="Run all configured merchants")
    parser.add_argument(
        "--limit", type=int, default=10, help="Max live products per merchant (default: 10)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent merchant runs (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Scrape only and print rows instead of writing"
    )
    parser.add_argument(
        "--issue-tag",
        default=DEFAULT_ISSUE_TAG,
        help=(
            "Writer metadata issue tag for DB traceability "
            f"(default: {DEFAULT_ISSUE_TAG})"
        ),
    )
    parser.add_argument(
        "--woocommerce-base-url",
        default=os.environ.get("WOOCOMMERCE_BASE_URL", "").strip(),
        help="Base URL for the WooCommerce merchant when running the `woocommerce` scraper.",
    )
    return parser.parse_args()


def _build_scraper(merchant_key: str, limit: int, args: argparse.Namespace):
    if merchant_key == "woocommerce":
        base_url = (args.woocommerce_base_url or "").strip().rstrip("/")
        if not base_url:
            raise ValueError(
                "woocommerce requires --woocommerce-base-url or WOOCOMMERCE_BASE_URL"
            )
        return SCRAPER_CONFIG[merchant_key]["factory"](limit, base_url)
    return SCRAPER_CONFIG[merchant_key]["factory"](limit)


async def _scrape_singlemerchant(
    merchant_key: str, limit: int, semaphore: asyncio.Semaphore, args: argparse.Namespace
) -> tuple[str, list[dict[str, Any]], str | None]:
    async with semaphore:
        try:
            scraper = _build_scraper(merchant_key, limit, args)
            async with scraper:
                products = await scraper.scrape()
            return merchant_key, [asdict(product) for product in products if product.sku], None
        except Exception as exc:  # noqa: BLE001
            return merchant_key, [], str(exc)


async def _scrape_all_merchants(
    merchant_keys: list[str], limit: int, concurrency: int, args: argparse.Namespace
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _scrape_singlemerchant(key, limit, semaphore, args) for key in merchant_keys
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    output: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str] = {}
    for result in results:
        if isinstance(result, Exception):
            errors[f"task_{len(errors) + 1}"] = str(result)
            continue
        merchant_key, products, error = result
        output[merchant_key] = products
        if error:
            errors[merchant_key] = error
    return output, errors


async def _main() -> int:
    args = _parse_args()
    targets = configured_database_targets()
    assert_ingestion_allowed(targets["active_database_url"])

    skipped_merchants: dict[str, str] = {}
    if args.all:
        merchant_keys = _default_all_merchants()
        skipped_merchants = _default_all_skips()
    elif args.merchant_key:
        merchant_keys = args.merchant_key
    else:
        print("Error: specify merchant key(s) or use --all", file=sys.stderr)
        return 1

    scraped, errors = await _scrape_all_merchants(
        merchant_keys, args.limit, args.concurrency, args
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "merchants": merchant_keys,
                    "scraped": {k: len(v) for k, v in scraped.items()},
                    "errors": errors,
                    "skipped_merchants": skipped_merchants,
                    "limit": args.limit,
                    "concurrency": args.concurrency,
                    "database_targets": targets,
                    "sample_skus": {
                        k: [p["sku"] for p in v[:5]] for k, v in scraped.items()
                    },
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return 0

    total_written = 0
    for merchant_key, products in scraped.items():
        if not products:
            continue
        defaults = SCRAPER_CONFIG[merchant_key]["defaults"]
        rows_written = upsert_products(
            products,
            source=defaults["source"],
            merchant_id=defaults["merchant_id"],
            defaults=defaults,
            metadata_tag={
                "issue": args.issue_tag,
                "merchant_key": merchant_key,
                "path": "scripts/catalog_live_ingest.py",
                "mode": "live_scrape",
            },
            db_url=targets["active_database_url"],
        )
        total_written += rows_written

    print(
        json.dumps(
                {
                    "merchants": merchant_keys,
                    "scraped": {k: len(v) for k, v in scraped.items()},
                    "errors": errors,
                    "skipped_merchants": skipped_merchants,
                    "total_written": total_written,
                    "limit": args.limit,
                    "concurrency": args.concurrency,
                "database_targets": targets,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

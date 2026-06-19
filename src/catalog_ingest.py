"""Canonical catalog ingestion helpers.

This module centralizes product upserts so repo-local writers target the pinned
catalog DB from ``data/.catalog_db_url`` rather than whichever harness DB URL
is present in the environment.
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ingestion_guard import assert_ingestion_allowed, database_url


def _decimal_or_zero(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid price value: {value!r}") from exc


# Noisy catch-all and placeholder values that do not represent real product categories.
# These are scraped fromShopify/WooCommerce product_type fields but carry no
# signal and inflate the blank/other buckets in the BUY-7547 scorecard.
_NOISY_CATEGORIES = frozenset({
    # Generic placeholders
    "other", "others", "uncategorized", "miscellaneous", "general",
    "default", "none", "n/a", "na", "null", "-",
    # Shopify catch-alls surfaced by BUY-7547 analysis
    "bundle builder", "interest check", "in stock", "end", "add-ons",
    "in production", "pre-order", "sold out", "new",
    # Garage-band / custom-keyboard noise (kbdfans)
    "60% assembled keyboard", "60% diy kit", "65% diy kit", "75% diy kit",
    "tkl diy kit", "full size diy kit",
    # Home-goods noise (ettitude)
    "greeting card",
    # Any single-char or very short placeholder
    "?",
})

# Category-path first-segment values that are noise and should be dropped.
_PATH_NOISE_VALUES = frozenset({
    "interest check", "in stock", "end", "add-ons", "in production",
    "pre-order", "sold out", "new", "bundle builder",
})


def _clean_category(value: Any) -> str | None:
    """Return a cleaned category string, or None if the value is garbage."""
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    # Drop known noisy placeholders
    if cleaned.lower() in _NOISY_CATEGORIES:
        return None
    return cleaned


def _normalize_category_path(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [_clean_category(part) for part in value]
        # Filter out None entries and re-split on ' > ' delimiters
        segments: list[str] = []
        for part in cleaned:
            if part is None:
                continue
            for segment in part.split(" > "):
                segment = segment.strip()
                if segment and segment.lower() not in _PATH_NOISE_VALUES:
                    segments.append(segment)
        return segments if segments else None
    if isinstance(value, tuple):
        return _normalize_category_path(list(value))
    return _normalize_category_path([value])


def _truncate_gtin(value: Any, max_len: int = 14) -> str | None:
    """Truncate GTIN to fit the varchar(N) DB column."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len]




def normalize_product_row(
    product: dict[str, Any],
    *,
    source: str | None = None,
    merchant_id: str | None = None,
    defaults: dict[str, Any] | None = None,
    metadata_tag: dict[str, Any] | None = None,
) -> tuple[Any, ...]:
    defaults = defaults or {}
    raw_data = product.get("raw_data") or {}
    offers = raw_data.get("offers") or {}
    metadata = dict(product.get("metadata") or raw_data or {})
    if metadata_tag:
        metadata["_writer"] = metadata_tag

    resolved_source = (
        source
        or product.get("source")
        or metadata.get("source")
        or defaults.get("source")
        or ""
    )
    resolved_merchant_id = merchant_id or product.get("merchant_id") or defaults.get(
        "merchant_id"
    )
    title = product.get("title") or product.get("name")
    description = product.get("description") or raw_data.get("description")
    currency = (
        product.get("currency")
        or offers.get("priceCurrency")
        or defaults.get("currency")
        or ""
    )
    url = product.get("url") or offers.get("url") or raw_data.get("url") or ""
    category_path = _normalize_category_path(product.get("category_path"))
    # Also clean the flat category field — it gets overwritten on every upsert
    category = _clean_category(product.get("category"))
    image_url = product.get("image_url")
    if not image_url:
        raw_image = raw_data.get("image")
        if isinstance(raw_image, list):
            image_url = raw_image[0] if raw_image else None
        else:
            image_url = raw_image

    is_active = product.get("is_active")
    if is_active is None:
        is_active = defaults.get("is_active", True)

    in_stock = product.get("in_stock")
    if in_stock is None:
        availability = offers.get("availability", "")
        if availability:
            in_stock = availability.endswith("/InStock") or availability.endswith(
                "InStock"
            )
        else:
            in_stock = defaults.get("in_stock", True)

    return (
        product["sku"],
        resolved_source,
        resolved_merchant_id,
        title,
        description,
        _decimal_or_zero(product.get("price")),
        currency,
        url,
        category,
        category_path,
        image_url,
        is_active,
        Json(metadata),
        product.get("brand"),
        product.get("region") or defaults.get("region"),
        product.get("country_code") or defaults.get("country_code"),
        product.get("platform") or defaults.get("platform"),
        in_stock,
        _truncate_gtin(product.get("gtin") or raw_data.get("gtin")),
    )


def upsert_product_rows(
    rows: list[tuple[Any, ...]],
    *,
    db_url: str | None = None,
) -> int:
    if not rows:
        return 0

    db_url = db_url or database_url()
    assert_ingestion_allowed(db_url)

    sql = """
        INSERT INTO public.products (
            sku,
            source,
            merchant_id,
            title,
            description,
            price,
            currency,
            url,
            category,
            category_path,
            image_url,
            is_active,
            metadata,
            brand,
            region,
            country_code,
            platform,
            in_stock,
            gtin
        ) VALUES %s
        ON CONFLICT (sku, source) DO UPDATE SET
            merchant_id = EXCLUDED.merchant_id,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            price = EXCLUDED.price,
            currency = EXCLUDED.currency,
            url = EXCLUDED.url,
            category = EXCLUDED.category,
            category_path = EXCLUDED.category_path,
            image_url = EXCLUDED.image_url,
            is_active = EXCLUDED.is_active,
            metadata = EXCLUDED.metadata,
            brand = EXCLUDED.brand,
            region = EXCLUDED.region,
            country_code = EXCLUDED.country_code,
            platform = EXCLUDED.platform,
            in_stock = EXCLUDED.in_stock,
            gtin = EXCLUDED.gtin,
            is_available = EXCLUDED.in_stock,
            updated_at = NOW(),
            last_checked = NOW(),
            data_updated_at = NOW()
    """
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows, page_size=200)
        conn.commit()
    return len(rows)


def upsert_products(
    products: list[dict[str, Any]],
    *,
    source: str | None = None,
    merchant_id: str | None = None,
    defaults: dict[str, Any] | None = None,
    metadata_tag: dict[str, Any] | None = None,
    db_url: str | None = None,
) -> int:
    rows = [
        normalize_product_row(
            product,
            source=source,
            merchant_id=merchant_id,
            defaults=defaults,
            metadata_tag=metadata_tag,
        )
        for product in products
    ]
    return upsert_product_rows(rows, db_url=db_url)

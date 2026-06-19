#!/usr/bin/env python3
"""Probe anti-bot targets through BrightData residential egress.

BUY-53492 needs a repeatable way to verify whether BrightData-backed
browser/HTTP traffic can reach Watsons MY / Sephora MY without hand-building
proxy usernames. This script exercises both the raw HTTP and Playwright paths
using the shared proxy helper and emits compact JSON evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
import urllib3
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.scrapers.proxy_config import Zone, proxy_config_for_playwright, proxy_url

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_URLS = [
    "https://www.watsons.com.my/",
    "https://api.watsons.com.my/",
    "https://www.sephora.my/",
    "https://api.sephora.sg/",
]


@dataclass
class ProbeResult:
    method: str
    url: str
    status: int | None
    final_url: str | None
    title: str | None
    server: str | None
    ok: bool
    elapsed_ms: int
    detail: str


def _http_probe(url: str, zone: Zone, country: str | None, session: str) -> ProbeResult:
    started = time.time()
    try:
        px = proxy_url(zone, country=country, session=session)
        response = requests.get(
            url,
            headers={"user-agent": _user_agent()},
            proxies={"http": px, "https": px},
            timeout=60,
            verify=False,
            allow_redirects=True,
        )
        body = response.text[:160].replace("\n", " ").strip()
        return ProbeResult(
            method="http",
            url=url,
            status=response.status_code,
            final_url=str(response.url),
            title=None,
            server=response.headers.get("server"),
            ok=response.ok,
            elapsed_ms=int((time.time() - started) * 1000),
            detail=body,
        )
    except Exception as exc:  # pragma: no cover - runtime probe
        return ProbeResult(
            method="http",
            url=url,
            status=None,
            final_url=None,
            title=None,
            server=None,
            ok=False,
            elapsed_ms=int((time.time() - started) * 1000),
            detail=repr(exc),
        )


async def _playwright_probe(
    url: str,
    zone: Zone,
    country: str | None,
    session: str,
    *,
    locale: str,
    timezone_id: str,
) -> ProbeResult:
    started = time.time()
    proxy = proxy_config_for_playwright(zone, country=country, session=session)
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                proxy=proxy,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                ignore_https_errors=True,
                user_agent=_user_agent(),
                viewport={"width": 1440, "height": 960},
                locale=locale,
                timezone_id=timezone_id,
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = await context.new_page()
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(2500)
            content = await page.content()
            title = await page.title()
            await context.close()
            await browser.close()
            return ProbeResult(
                method="playwright",
                url=url,
                status=response.status if response else None,
                final_url=page.url,
                title=title,
                server=response.headers.get("server") if response else None,
                ok=bool(response and response.ok),
                elapsed_ms=int((time.time() - started) * 1000),
                detail=content[:160].replace("\n", " ").strip(),
            )
    except Exception as exc:  # pragma: no cover - runtime probe
        return ProbeResult(
            method="playwright",
            url=url,
            status=None,
            final_url=None,
            title=None,
            server=None,
            ok=False,
            elapsed_ms=int((time.time() - started) * 1000),
            detail=repr(exc),
        )


def _user_agent() -> str:
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone", default="residential_proxy1", choices=[z.value for z in Zone])
    parser.add_argument("--country", default="my")
    parser.add_argument("--session", default="buy53492")
    parser.add_argument("--locale", default="en-MY")
    parser.add_argument("--timezone", default="Asia/Kuala_Lumpur")
    parser.add_argument("--output", default="")
    parser.add_argument("urls", nargs="*", default=DEFAULT_URLS)
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    zone = Zone(args.zone)
    results: list[ProbeResult] = []

    for url in args.urls:
        results.append(_http_probe(url, zone, args.country, args.session))
        results.append(
            await _playwright_probe(
                url,
                zone,
                args.country,
                args.session,
                locale=args.locale,
                timezone_id=args.timezone,
            )
        )

    payload: dict[str, Any] = {
        "zone": zone.value,
        "country": args.country,
        "session": args.session,
        "results": [asdict(r) for r in results],
    }

    rendered = json.dumps(payload, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

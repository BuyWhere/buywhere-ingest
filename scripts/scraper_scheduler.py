#!/usr/bin/env python3
"""
Scraper scheduler for SG merchant scrapers.

Schedules and runs the following scrapers on a configured cadence:
  - courts_sg  (module: src.scrapers.courts_sg)
  - forty_two  (module: src.scrapers.forty_two)
  - ikea_sg    (module: src.scrapers.ikea_sg)
  - nike_sg    (module: src.scrapers.nike_sg)
  - uniqlo_sg  (module: src.scrapers.uniqlo_sg)

Usage:
  python scripts/scraper_scheduler.py --scraper courts_sg          # single run
  python scripts/scraper_scheduler.py --continuous --interval 3600 # loop mode

Cron examples (run from _default/ directory):
  */30 * * * * cd /path/to/_default && python scripts/scraper_scheduler.py --scraper courts_sg
  0      * * * * cd /path/to/_default && python scripts/scraper_scheduler.py --scraper forty_two
"""

import argparse
import asyncio
import importlib.util
import types
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure Playwright system deps on the library path (BUY-37375)
_pw_deps = "/home/paperclip/playwright-deps/lib"
if _pw_deps not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = f"{_pw_deps}:{os.environ.get('LD_LIBRARY_PATH', '')}"

# Path to src/scrapers/ inside the project (_default/)
_SCRAPERS_DIR = Path(__file__).parent.parent / "src" / "scrapers"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Project root (_default/)
_ROOT = Path(__file__).parent.parent.resolve()

# Use importlib to load scraper modules directly, bypassing the
# src/scrapers/__init__.py which has a broken 'from scrapers.scraper_registry'
# import chain (lazada_my.py).  __init__.py is NOT executed this way.

def _load_scraper(name: str, class_name: str):
    """Load a scraper class from a file without triggering __init__."""
    module_path = _SCRAPERS_DIR / f"{name}.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Scraper module not found: {module_path}")

    # Stub packages so relative imports inside scraper files resolve.
    # We use types.ModuleType (not importlib) to avoid running __init__ files.
    for pkg_name, pkg_path in [("src", str(_SCRAPERS_DIR.parent)), ("src.scrapers", str(_SCRAPERS_DIR))]:
        if pkg_name not in sys.modules:
            pkg_mod = types.ModuleType(pkg_name)
            pkg_mod.__path__ = [pkg_path]
            pkg_mod.__package__ = pkg_name
            sys.modules[pkg_name] = pkg_mod

    # Stub 'scrapers' (top-level) to unblock lazada_my's broken import
    if "scrapers" not in sys.modules:
        scrapers_pkg = types.ModuleType("scrapers")
        scrapers_pkg.__path__ = []
        scrapers_pkg.__package__ = "scrapers"
        sys.modules["scrapers"] = scrapers_pkg

    # Load base_scraper so child scrapers can import it
    if "base_scraper" not in sys.modules:
        base_path = _SCRAPERS_DIR / "base_scraper.py"
        base_spec = importlib.util.spec_from_file_location("base_scraper", base_path)
        base_mod = importlib.util.module_from_spec(base_spec)
        sys.modules["base_scraper"] = base_mod
        base_spec.loader.exec_module(base_mod)

    # Use spec name = just the module name so Python treats it as a module,
    # not a package. Set __package__ so '.base_scraper' resolves to 'src.scrapers.base_scraper'.
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "src.scrapers"      # relative imports resolve via this
    spec.loader.exec_module(module)
    return getattr(module, class_name)


# Load each of the 5 scheduled scrapers
_CourtsSGScraper = _load_scraper("courts_sg", "CourtsSGScraper")
_FortyTwoScraper = _load_scraper("forty_two", "FortyTwoScraper")
_IKEAScraper     = _load_scraper("ikea_sg",   "IKEAScraper")
_NikeSGScraper   = _load_scraper("nike_sg",   "NikeSGScraper")
_UniqloSGScraper = _load_scraper("uniqlo_sg", "UniqloSGScraper")

SCRAPERS = {
    "courts_sg": _CourtsSGScraper,
    "forty_two": _FortyTwoScraper,
    "ikea_sg":   _IKEAScraper,
    "nike_sg":   _NikeSGScraper,
    "uniqlo_sg": _UniqloSGScraper,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("scraper_scheduler")


# -------------------------------------------------------------------
# Scraper registry: maps logical name → (SCRAPERS key, module path string)
# -------------------------------------------------------------------
SCHEDULED_SCRAPERS = {
    "courts_sg":  {"key": "courts_sg",  "module": "src.scrapers.courts_sg"},
    "forty_two":  {"key": "forty_two",  "module": "src.scrapers.forty_two"},
    "ikea_sg":    {"key": "ikea_sg",    "module": "src.scrapers.ikea_sg"},
    "nike_sg":    {"key": "nike_sg",    "module": "src.scrapers.nike_sg"},
    "uniqlo_sg":  {"key": "uniqlo_sg",  "module": "src.scrapers.uniqlo_sg"},
}

DATA_DIR = _ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def scraper_output_path(name: str) -> Path:
    return DATA_DIR / f"{name}_scheduler.jsonl"


async def run_scraper(name: str) -> dict:
    """Run a single scraper and return a result dict."""
    info = SCHEDULED_SCRAPERS[name]
    scraper_class = SCRAPERS.get(info["key"])
    if not scraper_class:
        return {
            "scraper": name,
            "module": info["module"],
            "status": "error",
            "error": f"Scraper key '{info['key']}' not found in SCRAPERS registry",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        async with scraper_class() as scraper:
            merchant_name = getattr(scraper, "merchant_name", name)
            logger.info(f"[{name}] Starting scrape of {merchant_name}")
            start = time.monotonic()
            products = await scraper.scrape()
            elapsed = time.monotonic() - start
            result = {
                "scraper": name,
                "module": info["module"],
                "status": "completed",
                "product_count": len(products),
                "elapsed_seconds": round(elapsed, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(
                f"[{name}] Completed: {len(products)} products in {result['elapsed_seconds']}s"
            )
            return result
    except Exception as exc:
        logger.exception(f"[{name}] Failed: {exc}")
        return {
            "scraper": name,
            "module": info["module"],
            "status": "failed",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def append_result(result: dict):
    """Append a JSON result line to the scraper's output file."""
    out_file = scraper_output_path(result["scraper"])
    with open(out_file, "a") as f:
        f.write(json.dumps(result) + "\n")


async def run_single(name: str):
    """Run one named scraper once and exit."""
    result = await run_scraper(name)
    append_result(result)
    return result


async def run_continuous(name: str, interval_seconds: int):
    """Run a named scraper on a repeating interval."""
    logger.info(f"[{name}] Continuous mode: every {interval_seconds}s")
    while True:
        result = await run_scraper(name)
        append_result(result)
        logger.info(f"[{name}] Sleeping {interval_seconds}s before next run")
        await asyncio.sleep(interval_seconds)


async def run_all_once():
    """Run all 5 scheduled scrapers once each."""
    logger.info("Running all scheduled scrapers (one-shot)")
    for name in SCHEDULED_SCRAPERS:
        result = await run_scraper(name)
        append_result(result)
    logger.info("All scrapers completed")


async def run_all_continuous(interval_seconds: int):
    """Run all 5 scrapers in a loop with a shared interval."""
    logger.info(f"Running all scrapers continuously every {interval_seconds}s")
    while True:
        for name in SCHEDULED_SCRAPERS:
            result = await run_scraper(name)
            append_result(result)
        logger.info(f"All scrapers done. Sleeping {interval_seconds}s")
        await asyncio.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="SG Merchant Scraper Scheduler")
    parser.add_argument(
        "--scraper",
        choices=list(SCHEDULED_SCRAPERS.keys()),
        help="Run a specific scraper (default: all)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Repeat on --interval (default: single run)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between runs in continuous mode (default: 3600)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 5 scheduled scrapers",
    )
    args = parser.parse_args()

    if args.scraper:
        if args.continuous:
            asyncio.run(run_continuous(args.scraper, args.interval))
        else:
            asyncio.run(run_single(args.scraper))
    elif args.all or args.continuous:
        # --all without --continuous: run all once; --continuous alone: run all continuously
        mode = args.all and not args.continuous
        if mode:
            asyncio.run(run_all_once())
        else:
            asyncio.run(run_all_continuous(args.interval))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

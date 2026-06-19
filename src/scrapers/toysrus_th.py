"""Scraper for Toys"R"Us Thailand (toysrus.co.th).

Salesforce Commerce Cloud (Demandware) store with category-based
product grids accessed via AJAX Search-ShowAjax endpoint.
"""

import asyncio
import logging
import re
from typing import List, Optional, Set
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, Product

logger = logging.getLogger(__name__)

TOYS_BASE = "https://www.toysrus.co.th"
TOYS_EN = "https://www.toysrus.co.th/en-th"

PAGE_SIZE = 48
MAX_CONCURRENT = 4
MAX_PRODUCTS = 50000

CATEGORIES = [
    ("action_figures_hero_play_th", "Action Figures & Hero Play"),
    ("barbie", "Barbie"),
    ("bikes_scooters_ride_ons_th", "Bikes, Scooters & Ride-Ons"),
    ("blind_box_th", "Blind Box"),
    ("building_blocks_lego_th", "Building Blocks & Lego"),
    ("cars_trucks_trains_rc_th", "Cars, Trucks, Trains & RC"),
    ("collectible_characters_th", "Collectible Characters"),
    ("craft_activities_th", "Craft & Activities"),
    ("dolls_collectibles_th", "Dolls & Collectibles"),
    ("electronics_th", "Electronics"),
    ("games_puzzles_th", "Games & Puzzles"),
    ("learning_toys_th", "Learning Toys"),
    ("outdoor_sports_th", "Outdoor & Sports"),
    ("party_th", "Party"),
    ("pretend_play_costumes_th", "Role Play & Costumes"),
    ("soft_toys_th", "Soft Toys"),
    ("toddler_and_baby_toys_th", "Toddler & Baby Toys"),
    ("baby_toddler_toys_th", "Baby & Toddler Toys"),
    ("maternity_th", "Maternity"),
    ("nursery_furniture_sleep_th", "Nursery Furniture & Sleep"),
    ("feeding_food_th", "Feeding & Food"),
    ("diapers_wipes_th", "Diapers & Wipes"),
    ("bath_toilet_training_th", "Bath & Toilet Training"),
    ("health_safet_th", "Health & Safety"),
    ("strollers_th", "Strollers"),
    ("car_seats_boosters_th", "Car Seats & Boosters"),
]


class ToysRUsTHScraper(BaseScraper):
    """Scrape Toys"R"Us Thailand through SFCC AJAX product grids."""

    REQUEST_TIMEOUT = 30

    def __init__(self):
        super().__init__("ToysRUs Thailand", TOYS_BASE)
        self._seen_urls: Set[str] = set()

    def _ajax_url(self, cgid: str, start: int = 0) -> str:
        """Build SFCC Search-ShowAjax URL for a category page."""
        return (
            f"{TOYS_BASE}/on/demandware.store/Sites-ToysRUs_TH-Site/en_TH"
            f"/Search-ShowAjax?cgid={cgid}&start={start}&sz={PAGE_SIZE}"
        )

    async def _fetch_grid(self, url: str) -> Optional[str]:
        """Fetch a product grid page via AJAX with retry."""
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.REQUEST_TIMEOUT),
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "text/html,*",
                    },
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    if len(response.text) > 1000:
                        return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
        return None

    def _parse_grid(self, html: str, category_name: str = "", seen_set: Set[str] = None) -> List[Product]:
        """Parse product tiles from a grid page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        products = []
        tiles = soup.select(".product-tile")
        for tile in tiles:
            pid = tile.get("data-pid", "")
            name_el = tile.select_one("[itemprop=\"name\"]")
            link_el = tile.select_one("a[href]")
            img_el = tile.select_one("img.tile-image")
            if not name_el:
                continue
            name = self._clean_text(name_el.get_text(strip=True))
            url = urljoin(TOYS_BASE, link_el.get("href", "")) if link_el else None
            img_url = img_el.get("data-src") or img_el.get("src") if img_el else None

            # Extract current price from SFCC price structure
            price = None
            sales_el = tile.select_one(".price .sales .value")
            if sales_el:
                pt = sales_el.get_text(strip=True)
                m = re.search(r"[0-9,]+(?:\.[0-9]+)?", pt)
                if m:
                    price = "\u0e3f" + m.group(0)
            if not price:
                fallback_el = tile.select_one(".price .value")
                if fallback_el:
                    pt = fallback_el.get_text(strip=True)
                    m = re.search(r"[0-9,]+(?:\.[0-9]+)?", pt)
                    if m:
                        price = "\u0e3f" + m.group(0)
            if url and url in (seen_set or set()):
                continue
            if url and seen_set is not None:
                seen_set.add(url)
            
            product = Product(
                name=name,
                price=price,
                url=url,
                sku=pid,
                image_url=img_url,
                brand="ToysRUs",
                category=category_name,
            )
            products.append(product)
        return products

    async def _scrape_category(self, cgid: str, name: str, category_name: str = "") -> List[Product]:
        """Scrape all products from a single category via paginated AJAX."""
        # Use a per-category URL dedup set to avoid cross-category filtering
        _cat_seen = set()
        products = []
        start = 0
        empty_pages = 0
        
        while empty_pages < 2 and len(products) < MAX_PRODUCTS:
            url = self._ajax_url(cgid, start)
            html = await self._fetch_grid(url)
            if not html:
                logger.warning(f"  [{name}] Empty response at start={start}")
                break
            
            page_products = self._parse_grid(html, category_name or name, _cat_seen)
            if not page_products:
                empty_pages += 1
                start += PAGE_SIZE
                continue
            
            products.extend(page_products)
            empty_pages = 0
            start += PAGE_SIZE
            
            if len(page_products) < PAGE_SIZE:
                logger.info(f"  [{name}] Last page ({len(products)} products)")
                break
            
            await asyncio.sleep(0.5)
        
        return products

    async def _scrape_impl(self, products: List[Product]) -> None:
        """Scrape all Toys"R"Us Thailand categories."""
        logger.info(f"ToysRUs Thailand: {len(CATEGORIES)} categories to scrape")
        
        for cgid, name in CATEGORIES:
            if len(products) >= MAX_PRODUCTS:
                break
            logger.info(f"Scraping category: {name} (cgid={cgid})")
            cat_products = await self._scrape_category(cgid, name, name)
            products.extend(cat_products)
            logger.info(f"  {name}: {len(cat_products)} products ({len(products)} total)")
        
        logger.info(f"ToysRUs Thailand total: {len(products)} products")


async def main():
    """Quick test."""
    logging.basicConfig(level=logging.INFO)
    scraper = ToysRUsTHScraper()
    async with scraper:
        products = await scraper.scrape()
        print(f"\nToysRUs Thailand: {len(products)} products")
        if products:
            for p in products[:10]:
                print(f"  {p.name} - {p.price} - {p.sku}")
        print(f"  ... ({len(products)} total)")


if __name__ == "__main__":
    asyncio.run(main())

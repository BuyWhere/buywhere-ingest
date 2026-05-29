"""Base scraper class for merchant product extraction."""

import httpx
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class Product:
    """Represents a scraped product."""
    name: str
    price: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class BaseScraper(ABC):
    """Base class for merchant-specific scrapers."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2
    REQUEST_TIMEOUT = 30

    def __init__(self, merchant_name: str, base_url: str):
        self.merchant_name = merchant_name
        self.base_url = base_url
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.REQUEST_TIMEOUT),
            headers=self._get_headers()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch a URL with retry logic."""
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                response = await self.session.get(url, follow_redirects=True)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
        return None

    async def scrape(self) -> List[Product]:
        """Main scraping entry point."""
        products = []
        try:
            await self._scrape_impl(products)
        except Exception as e:
            logger.error(f"Scraping failed for {self.merchant_name}: {e}")
        return products

    @abstractmethod
    async def _scrape_impl(self, products: List[Product]) -> None:
        """Merchant-specific scraping logic."""
        pass

    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean extracted text."""
        if not text:
            return None
        return " ".join(text.split()).strip()

    async def get_product_count(self) -> int:
        """Return total product count after scrape."""
        products = await self.scrape()
        return len(products)

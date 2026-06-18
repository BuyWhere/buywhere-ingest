"""Scrapers package for SG merchants."""

from .base_scraper import BaseScraper, Product
from .courts_sg import CourtsSGScraper
from .decathlon_sg import DecathlonSGScraper
from .harvey_norman_sg import HarveyNormanSGScraper
from .fairprice_sg import FairPriceScraper
from .uniqlo_sg import UniqloSGScraper
from .love_bonito import LoveBonitoScraper
from .charles_keith import CharlesKeithScraper
from .pedro import PedroScraper
from .nike_sg import NikeSGScraper
from .cotton_on_sg import CottonOnScraper
from .shein_sg import SheinSGScraper
from .editors_market import EditorsMarketScraper
from .tangs import TangsScraper
from .taka import TakaScraper
from .little_farms import LittleFarmsScraper
from .table_matters import TableMattersScraper
from .korianne import KorianneScraper
from .outdoor_life_sg import OutdoorLifeSGScraper
from .best_denki_sg import BestDenkiSGScraper
from .audio_house import AudioHouseScraper
from .gain_city import GainCityScraper
from .forty_two import FortyTwoScraper
from .cold_storage_sg import ColdStorageSGScraper
from .guardian_sg import GuardianSGScraper
from .summerhouse import SummerhouseScraper
from .paper_source import PaperSourceScraper
from .floor_and_decor import FloorAndDecorScraper
from .the_body_shop import TheBodyShopScraper
from .ikea_sg import IKEAScraper
from .woocommerce import WooCommerceScraper
from .shopify_store import ShopifyScraper
from .shopify_product_page import ShopifyProductPageScraper
from .zalora_sg import ZaloraSGScraper
from .tokopedia import TokopediaScraper
from .lazada_vn import LazadaVNScraper
from .lazada_my import LazadaMYScraper
from .shopee_sg import ShopeeSGScraper
from .shopee_my import ShopeeMYScraper
from .carousell_sg import CarousellSGScraper
from .qoo10_sg import Qoo10SGScraper
from .etsy_us import EtsyUSScraper
from .ebay_us import EbayUSScraper
from .ebay_us_api import EbayUSApiScraper

SCRAPERS = {
    "courts_sg": CourtsSGScraper,
    "decathlon_sg": DecathlonSGScraper,
    "harvey_norman_sg": HarveyNormanSGScraper,
    "fairprice_sg": FairPriceScraper,
    "uniqlo_sg": UniqloSGScraper,
    "love_bonito": LoveBonitoScraper,
    "charles_keith": CharlesKeithScraper,
    "pedro": PedroScraper,
    "nike_sg": NikeSGScraper,
    "cotton_on_sg": CottonOnScraper,
    "shein_sg": SheinSGScraper,
    "editors_market": EditorsMarketScraper,
    "tangs": TangsScraper,
    "taka": TakaScraper,
    "little_farms": LittleFarmsScraper,
    "table_matters": TableMattersScraper,
    "korianne": KorianneScraper,
    "outdoor_life_sg": OutdoorLifeSGScraper,
    "best_denki_sg": BestDenkiSGScraper,
    "audio_house": AudioHouseScraper,
    "gain_city": GainCityScraper,
    "forty_two": FortyTwoScraper,
    "cold_storage_sg": ColdStorageSGScraper,
    "guardian_sg": GuardianSGScraper,
    "summerhouse": SummerhouseScraper,
    "paper_source": PaperSourceScraper,
    "floor_and_decor": FloorAndDecorScraper,
    "the_body_shop": TheBodyShopScraper,
    "ikea_sg": IKEAScraper,
    "woocommerce": WooCommerceScraper,
    "zalora_sg": ZaloraSGScraper,
    "tokopedia": TokopediaScraper,
    "lazada_vn": LazadaVNScraper,
    "lazada_my": LazadaMYScraper,
    "shopee_sg": ShopeeSGScraper,
    "shopee_my": ShopeeMYScraper,
    "carousell_sg": CarousellSGScraper,
    "qoo10_sg": Qoo10SGScraper,
    "etsy_us": EtsyUSScraper,
    "ebay_us": EbayUSScraper,
    "ebay_us_api": EbayUSApiScraper,
}

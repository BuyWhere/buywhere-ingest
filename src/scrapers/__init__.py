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
}

# crawlers package
from .eprocurement import EProcurementCrawler
from .mertender import MerTenderCrawler
from .generic import (
    AddisZemenCrawler, EthiopianReporterCrawler,
    EthioTenderCrawler, MercatoCrawler, PPAACrawler, UNGMCrawler
)

SITE_CRAWLERS = {
    "eprocurement": EProcurementCrawler,
    "mertender": MerTenderCrawler,
    "ppaa": PPAACrawler,
    "ungm": UNGMCrawler,
    "addiszemen": AddisZemenCrawler,
    "ethiopianreporter": EthiopianReporterCrawler,
    "ethiotender": EthioTenderCrawler,
    "mercato": MercatoCrawler,
}

__all__ = ["SITE_CRAWLERS"]

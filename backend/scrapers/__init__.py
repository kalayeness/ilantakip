from scrapers.trendyol import TrendyolScraper
from scrapers.hepsiburada import HepsiburadaScraper
from scrapers.sahibinden import SahibindenScraper

SCRAPERS = {
    "trendyol": TrendyolScraper(),
    "hepsiburada": HepsiburadaScraper(),
    "sahibinden": SahibindenScraper(),
}


def search_all(query: str, platforms: list[str] | None = None, max_pages: int = 2):
    """Tüm platformlarda arama yap, fiyata göre sırala."""
    targets = platforms or list(SCRAPERS.keys())
    results = []
    for name in targets:
        scraper = SCRAPERS.get(name)
        if scraper:
            try:
                results.extend(scraper.search(query, max_pages=max_pages))
            except Exception:
                pass
    results.sort(key=lambda x: x.price)
    return results

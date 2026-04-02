import re
import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from scrapers.base import BaseScraper, ScrapedProduct

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
BASE_URL = "https://www.sahibinden.com"


class SahibindenScraper(BaseScraper):
    platform_name = "sahibinden"
    is_secondhand = True

    def search(self, query: str, max_pages: int = 3) -> list[ScrapedProduct]:
        products = []
        session = requests.Session()
        session.get(BASE_URL, headers=HEADERS, timeout=10)
        time.sleep(random.uniform(1, 2))

        for page in range(max_pages):
            offset = page * 20
            url = f"{BASE_URL}/arama?query={requests.utils.quote(query)}&pagingOffset={offset}"
            try:
                resp = session.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                page_products = self._parse_search(resp.text)
                if not page_products:
                    break
                products.extend(page_products)
                if page < max_pages - 1:
                    time.sleep(random.uniform(1.5, 3))
            except Exception as e:
                logger.error(f"Sahibinden arama hatası: {e}")
                break

        logger.info(f"Sahibinden '{query}': {len(products)} ilan.")
        return products

    def fetch_url(self, url: str, max_pages: int = 5) -> list[ScrapedProduct]:
        """Verilen URL'den ilanları çek (filtreli arama için)."""
        products = []
        session = requests.Session()
        session.get(BASE_URL, headers=HEADERS, timeout=10)
        time.sleep(random.uniform(1, 2))

        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("pagingOffset", None)
        page_size = int(params.get("pagingSize", ["20"])[0])
        base_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in params.items()})))

        for page in range(max_pages):
            offset = page * page_size
            params["pagingOffset"] = [str(offset)]
            page_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in params.items()})))
            if page == 0:
                page_url = base_url

            try:
                resp = session.get(page_url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                page_products = self._parse_search(resp.text)
                if not page_products:
                    break
                products.extend(page_products)
                if len(page_products) < page_size:
                    break
                if page < max_pages - 1:
                    time.sleep(random.uniform(1.5, 3))
            except Exception as e:
                logger.error(f"Sahibinden URL hatası: {e}")
                break

        return products

    def _parse_search(self, html: str) -> list[ScrapedProduct]:
        products = []
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table", id="searchResultsTable") or \
                soup.find("table", {"class": re.compile(r"searchResultsTable")})
        if not table:
            return []

        rows = table.find_all("tr", {"class": re.compile(r"searchResultsItem")})
        for row in rows:
            p = self._parse_row(row)
            if p:
                products.append(p)

        return products

    def _parse_row(self, row) -> ScrapedProduct | None:
        try:
            listing_id = row.get("data-id", "")
            if not listing_id:
                link = row.find("a", href=re.compile(r"/ilan/"))
                if link:
                    m = re.search(r"/(\d+)$", link.get("href", ""))
                    listing_id = m.group(1) if m else ""

            if not listing_id:
                return None

            title_elem = row.find("td", {"class": re.compile(r"searchResultsTitleValue")})
            title, url = "", ""
            if title_elem:
                link = title_elem.find("a")
                if link:
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    url = BASE_URL + href if href.startswith("/") else href

            price_elem = row.find("td", {"class": re.compile(r"searchResultsPriceValue")})
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price_digits = re.sub(r"[^\d]", "", price_text)
            price = float(price_digits) if price_digits else 0.0

            location_elem = row.find("td", {"class": re.compile(r"searchResultsLocationValue")})
            location = ""
            if location_elem:
                parts = [s.get_text(strip=True) for s in location_elem.find_all("span")]
                location = " / ".join(filter(None, parts))

            img = row.find("img")
            image_url = img.get("src") if img else None

            return ScrapedProduct(
                platform="sahibinden",
                external_id=str(listing_id),
                title=title or "Başlık yok",
                price=price,
                currency="TRY",
                url=url,
                image_url=image_url,
                is_secondhand=True,
                in_stock=True,
                location=location,
            )
        except Exception as e:
            logger.debug(f"Satır parse hatası: {e}")
            return None

    def get_product(self, url: str) -> ScrapedProduct | None:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title = soup.find("h1", {"class": re.compile(r"classifiedDetailTitle|title")})
            title = title.get_text(strip=True) if title else ""

            price_elem = soup.find(class_=re.compile(r"classifiedPrice|price"))
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = float(re.sub(r"[^\d]", "", price_text) or 0)

            listing_id = re.search(r"/(\d+)$", url.split("?")[0])
            listing_id = listing_id.group(1) if listing_id else url

            return ScrapedProduct(
                platform="sahibinden",
                external_id=listing_id,
                title=title,
                price=price,
                currency="TRY",
                url=url,
                image_url=None,
                is_secondhand=True,
                in_stock=True,
            )
        except Exception as e:
            logger.error(f"Sahibinden ürün hatası: {e}")
        return None

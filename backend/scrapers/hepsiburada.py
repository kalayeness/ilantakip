import re
import json
import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, ScrapedProduct

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


class HepsiburadaScraper(BaseScraper):
    platform_name = "hepsiburada"
    is_secondhand = False
    BASE_URL = "https://www.hepsiburada.com"

    def search(self, query: str, max_pages: int = 3) -> list[ScrapedProduct]:
        products = []
        session = requests.Session()

        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/ara?q={requests.utils.quote(query)}&sayfa={page}"
            try:
                resp = session.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                page_products = self._parse_search(resp.text)
                if not page_products:
                    break
                products.extend(page_products)
                if page < max_pages:
                    time.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.error(f"Hepsiburada arama hatası sayfa {page}: {e}")
                break

        logger.info(f"Hepsiburada '{query}': {len(products)} ürün.")
        return products

    def _parse_search(self, html: str) -> list[ScrapedProduct]:
        products = []
        soup = BeautifulSoup(html, "html.parser")

        # JSON data dene
        scripts = soup.find_all("script", type="application/json")
        for script in scripts:
            if script.string and "productList" in script.string:
                try:
                    data = json.loads(script.string)
                    items = data.get("productList", {}).get("products", [])
                    for item in items:
                        p = self._parse_json_item(item)
                        if p:
                            products.append(p)
                    if products:
                        return products
                except Exception:
                    pass

        # Fallback HTML
        cards = soup.find_all("li", {"class": re.compile(r"productListContent")})
        for card in cards:
            p = self._parse_card(card)
            if p:
                products.append(p)

        return products

    def _parse_json_item(self, item: dict) -> ScrapedProduct | None:
        try:
            price = item.get("finalPrice") or item.get("originalPrice", 0)
            product_id = str(item.get("sku", item.get("id", "")))
            slug = item.get("url", "")
            url = self.BASE_URL + slug if slug.startswith("/") else slug

            return ScrapedProduct(
                platform="hepsiburada",
                external_id=product_id,
                title=item.get("name", ""),
                price=float(price),
                currency="TRY",
                url=url,
                image_url=item.get("imageUrl"),
                is_secondhand=False,
                in_stock=item.get("availabilityStatus") != "OutOfStock",
                seller=item.get("merchantName"),
            )
        except Exception:
            return None

    def _parse_card(self, card) -> ScrapedProduct | None:
        try:
            link = card.find("a", href=True)
            if not link:
                return None
            url = self.BASE_URL + link["href"] if link["href"].startswith("/") else link["href"]
            product_id = re.search(r"-(\w+)$", link["href"].split("?")[0])
            product_id = product_id.group(1) if product_id else ""

            title_elem = card.find(attrs={"data-bind": re.compile(r"text.*title|name")})
            title = title_elem.get_text(strip=True) if title_elem else card.find("h3", recursive=True)
            if hasattr(title, "get_text"):
                title = title.get_text(strip=True)
            title = str(title) if title else ""

            price_elem = card.find(attrs={"class": re.compile(r"price|Price")})
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = float(re.sub(r"[^\d,]", "", price_text).replace(",", ".") or 0)

            img = card.find("img")
            image_url = img.get("src") if img else None

            return ScrapedProduct(
                platform="hepsiburada",
                external_id=product_id,
                title=title,
                price=price,
                currency="TRY",
                url=url,
                image_url=image_url,
                is_secondhand=False,
                in_stock=True,
            )
        except Exception:
            return None

    def get_product(self, url: str) -> ScrapedProduct | None:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_elem = soup.find("h1", {"class": re.compile(r"product-name|title")})
            title = title_elem.get_text(strip=True) if title_elem else ""

            price_elem = soup.find(attrs={"class": re.compile(r"finalPrice|price-value")})
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = float(re.sub(r"[^\d,]", "", price_text).replace(",", ".") or 0)

            product_id = re.search(r"-(\w+?)(?:\?|$)", url)
            product_id = product_id.group(1) if product_id else ""

            return ScrapedProduct(
                platform="hepsiburada",
                external_id=product_id,
                title=title,
                price=price,
                currency="TRY",
                url=url,
                image_url=None,
                is_secondhand=False,
                in_stock=True,
            )
        except Exception as e:
            logger.error(f"Hepsiburada ürün hatası: {e}")
        return None

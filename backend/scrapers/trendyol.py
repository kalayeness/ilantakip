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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.trendyol.com",
}


class TrendyolScraper(BaseScraper):
    platform_name = "trendyol"
    is_secondhand = False
    BASE_URL = "https://www.trendyol.com"

    def search(self, query: str, max_pages: int = 3) -> list[ScrapedProduct]:
        products = []
        session = requests.Session()

        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/sr?q={requests.utils.quote(query)}&pi={page}"
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
                logger.error(f"Trendyol arama hatası sayfa {page}: {e}")
                break

        logger.info(f"Trendyol '{query}': {len(products)} ürün bulundu.")
        return products

    def _parse_search(self, html: str) -> list[ScrapedProduct]:
        products = []
        soup = BeautifulSoup(html, "html.parser")

        # Trendyol JSON data içindeki ürünler
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "window.__SEARCH_APP_INITIAL_STATE__" in script.string:
                try:
                    json_str = re.search(
                        r"window\.__SEARCH_APP_INITIAL_STATE__\s*=\s*({.*?});",
                        script.string,
                        re.DOTALL,
                    )
                    if json_str:
                        data = json.loads(json_str.group(1))
                        items = (
                            data.get("productListingPage", {})
                            .get("products", [])
                        )
                        for item in items:
                            p = self._parse_product_json(item)
                            if p:
                                products.append(p)
                        return products
                except Exception as e:
                    logger.debug(f"JSON parse hatası: {e}")

        # Fallback: HTML parse
        cards = soup.find_all("div", {"class": re.compile(r"p-card-wrppr|product-card")})
        for card in cards:
            p = self._parse_product_card(card)
            if p:
                products.append(p)

        return products

    def _parse_product_json(self, item: dict) -> ScrapedProduct | None:
        try:
            price_data = item.get("price", {})
            price = price_data.get("discountedPrice", {}).get("value") or \
                    price_data.get("originalPrice", {}).get("value", 0)
            product_id = str(item.get("id", ""))
            url = self.BASE_URL + item.get("url", "")
            images = item.get("images", [])
            image_url = f"https://cdn.dsmcdn.com{images[0]}" if images else None

            return ScrapedProduct(
                platform="trendyol",
                external_id=product_id,
                title=item.get("name", ""),
                price=float(price),
                currency="TRY",
                url=url,
                image_url=image_url,
                is_secondhand=False,
                in_stock=True,
                seller=item.get("brand", {}).get("name"),
            )
        except Exception as e:
            logger.debug(f"Ürün parse hatası: {e}")
            return None

    def _parse_product_card(self, card) -> ScrapedProduct | None:
        try:
            link = card.find("a", href=True)
            if not link:
                return None
            url = self.BASE_URL + link["href"]
            product_id = re.search(r"-p-(\d+)", link["href"])
            product_id = product_id.group(1) if product_id else link["href"]

            title_elem = card.find(class_=re.compile(r"product-title|prdct-desc"))
            title = title_elem.get_text(strip=True) if title_elem else ""

            price_elem = card.find(class_=re.compile(r"prc-box-dscntd|discounted-price|price"))
            if not price_elem:
                price_elem = card.find(class_=re.compile(r"prc-box-sllng|selling-price"))
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price = float(re.sub(r"[^\d,]", "", price_text).replace(",", ".") or 0)

            img = card.find("img")
            image_url = img.get("src") or img.get("data-src") if img else None

            return ScrapedProduct(
                platform="trendyol",
                external_id=str(product_id),
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

            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "window.__PRODUCT_DETAIL_APP_INITIAL_STATE__" in script.string:
                    json_str = re.search(
                        r"window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*({.*?});",
                        script.string,
                        re.DOTALL,
                    )
                    if json_str:
                        data = json.loads(json_str.group(1))
                        product = data.get("product", {})
                        price = (
                            product.get("priceInfo", {}).get("discountedPrice") or
                            product.get("priceInfo", {}).get("price", 0)
                        )
                        product_id = str(product.get("id", ""))
                        images = product.get("images", [])
                        image_url = f"https://cdn.dsmcdn.com{images[0]}" if images else None

                        return ScrapedProduct(
                            platform="trendyol",
                            external_id=product_id,
                            title=product.get("name", ""),
                            price=float(price),
                            currency="TRY",
                            url=url,
                            image_url=image_url,
                            is_secondhand=False,
                            in_stock=product.get("inStock", True),
                        )
        except Exception as e:
            logger.error(f"Trendyol ürün hatası: {e}")
        return None

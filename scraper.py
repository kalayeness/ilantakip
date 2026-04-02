import re
import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

logger = logging.getLogger(__name__)

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.8,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
]

SAHIBINDEN_BASE = "https://www.sahibinden.com"


def validate_sahibinden_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return "sahibinden.com" in parsed.netloc
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Sayfalama parametrelerini kaldır, sadece ilk sayfayı tara."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("pagingOffset", None)
    params.pop("pagingSize", None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


def make_page_url(base_url: str, offset: int, page_size: int = 20) -> str:
    """Sayfa URL'si oluştur."""
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["pagingOffset"] = [str(offset)]
    params["pagingSize"] = [str(page_size)]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


def fetch_listings(url: str, max_pages: int = 5, page_size: int = 50) -> list[dict]:
    """Sahibinden.com'dan birden fazla sayfa ilanı çek."""
    base_url = normalize_url(url)
    headers = random.choice(HEADERS_LIST)
    all_listings = []

    try:
        session = requests.Session()
        session.get(SAHIBINDEN_BASE, headers=headers, timeout=15)
        time.sleep(random.uniform(1, 2))

        for page in range(max_pages):
            offset = page * page_size
            page_url = make_page_url(base_url, offset, page_size) if page > 0 else base_url

            try:
                response = session.get(page_url, headers=headers, timeout=20)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    logger.warning(f"Sayfa {page + 1}: Erişim engellendi (403).")
                elif e.response.status_code == 503:
                    logger.warning(f"Sayfa {page + 1}: Geçici olarak kullanılamıyor (503).")
                else:
                    logger.error(f"Sayfa {page + 1} HTTP hatası: {e}")
                break

            page_listings = parse_listings(response.text, page_url)

            if not page_listings:
                logger.info(f"Sayfa {page + 1}: İlan yok, durduruldu.")
                break

            all_listings.extend(page_listings)
            logger.info(f"Sayfa {page + 1}: {len(page_listings)} ilan, toplam: {len(all_listings)}")

            # Son sayfaya ulaşıldıysa dur
            if len(page_listings) < page_size:
                logger.info("Son sayfaya ulaşıldı.")
                break

            # Sayfalar arası bekleme (rate limit için)
            if page < max_pages - 1:
                time.sleep(random.uniform(1.5, 3))

        return all_listings

    except requests.exceptions.ConnectionError:
        logger.error("Bağlantı hatası.")
        return []
    except requests.exceptions.Timeout:
        logger.error("Zaman aşımı.")
        return []
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}")
        return []


def parse_listings(html: str, base_url: str) -> list[dict]:
    """HTML'den ilan bilgilerini parse et."""
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    # Sahibinden.com'un listing tablosu
    table = soup.find("table", {"class": re.compile(r"searchResultsTable|result-list")})
    if not table:
        # Alternatif selector dene
        table = soup.find("table", id="searchResultsTable")

    if not table:
        logger.warning("İlan tablosu bulunamadı. Sayfa yapısı değişmiş olabilir.")
        logger.debug(f"Sayfa başlığı: {soup.title.string if soup.title else 'Yok'}")
        return []

    rows = table.find_all("tr", {"class": re.compile(r"searchResultsItem|.*result.*")})

    for row in rows:
        try:
            listing = parse_row(row)
            if listing:
                listings.append(listing)
        except Exception as e:
            logger.debug(f"Satır parse hatası: {e}")
            continue

    logger.info(f"{len(listings)} ilan bulundu: {base_url[:60]}...")
    return listings


def parse_row(row) -> dict | None:
    """Tek bir ilan satırını parse et."""
    # İlan ID'sini al
    listing_id = row.get("data-id") or row.get("id", "")
    if not listing_id:
        # class içinden id bulmaya çalış
        link = row.find("a", href=re.compile(r"/ilan/"))
        if link:
            match = re.search(r"/(\d+)$", link.get("href", ""))
            if match:
                listing_id = match.group(1)

    if not listing_id or listing_id == "searchResultsTable":
        return None

    # Başlık
    title_elem = (
        row.find("td", {"class": re.compile(r"searchResultsTitleValue|title")}) or
        row.find("a", {"class": re.compile(r"classifiedTitle|title")})
    )
    title = ""
    listing_url = ""
    if title_elem:
        link = title_elem.find("a") if title_elem.name != "a" else title_elem
        if link:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            listing_url = SAHIBINDEN_BASE + href if href.startswith("/") else href

    # Fiyat
    price_elem = row.find("td", {"class": re.compile(r"searchResultsPriceValue|price")})
    price = price_elem.get_text(strip=True) if price_elem else "Belirtilmemiş"

    # Konum
    location_elem = row.find("td", {"class": re.compile(r"searchResultsLocationValue|location")})
    location = ""
    if location_elem:
        location_parts = [span.get_text(strip=True) for span in location_elem.find_all("span")]
        location = " / ".join(filter(None, location_parts)) or location_elem.get_text(strip=True)

    # Tarih
    date_elem = row.find("td", {"class": re.compile(r"searchResultsDateValue|date")})
    date = date_elem.get_text(strip=True) if date_elem else ""

    # Açıklama snippet'i (arama sonuçlarında varsa)
    desc_elem = row.find("td", {"class": re.compile(r"searchResultsTagAttributeValue|description|snippet")})
    description = desc_elem.get_text(" ", strip=True) if desc_elem else ""

    if not title and not listing_url:
        return None

    return {
        "id": str(listing_id),
        "title": title or "Başlık yok",
        "description": description,
        "price": price,
        "location": location,
        "url": listing_url,
        "date": date,
    }


def parse_price_value(price_str: str) -> int | None:
    """Fiyat metninden sayısal değer çıkar. '34.500 TL' → 34500"""
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits) if digits else None


def apply_local_filters(
    listings: list[dict],
    keywords: str = "",
    min_price: int | None = None,
    max_price: int | None = None,
) -> list[dict]:
    """
    İlanları anahtar kelime ve fiyat filtrelerine göre filtrele.
    keywords: virgülle ayrılmış kelimeler (örn: 'gök mavisi, uzay grisi')
    Kelimelerden EN AZ BİRİ başlıkta geçiyorsa ilan dahil edilir.
    """
    result = listings

    # Anahtar kelime filtresi
    if keywords and keywords.strip():
        keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        if keyword_list:
            filtered = []
            for listing in result:
                search_text = (listing["title"] + " " + listing.get("description", "")).lower()
                if any(kw in search_text for kw in keyword_list):
                    filtered.append(listing)
            result = filtered

    # Fiyat filtresi
    if min_price is not None or max_price is not None:
        filtered = []
        for listing in result:
            price_val = parse_price_value(listing["price"])
            if price_val is None:
                # Fiyatı çözülemeyenleri dahil et
                filtered.append(listing)
                continue
            if min_price is not None and price_val < min_price:
                continue
            if max_price is not None and price_val > max_price:
                continue
            filtered.append(listing)
        result = filtered

    return result


def format_listing_message(listing: dict, filter_name: str) -> str:
    """İlan bilgisini Telegram mesajı formatına çevir."""
    lines = [
        f"🏠 *Yeni İlan - {filter_name}*",
        f"",
        f"📌 {listing['title']}",
        f"💰 {listing['price']}",
    ]
    if listing.get("location"):
        lines.append(f"📍 {listing['location']}")
    if listing.get("date"):
        lines.append(f"📅 {listing['date']}")
    if listing.get("url"):
        lines.append(f"")
        lines.append(f"🔗 [İlana Git]({listing['url']})")

    return "\n".join(lines)

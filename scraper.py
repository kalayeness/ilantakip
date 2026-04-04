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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
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
    """Sayfalama offset'ini kaldır ama pagingSize'ı koru."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("pagingOffset", None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


def make_page_url(base_url: str, offset: int) -> str:
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["pagingOffset"] = [str(offset)]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


def _is_blocked_or_error(html: str, response) -> bool:
    """Sayfanın engellenip engellenmediğini ya da hata olup olmadığını kontrol et."""
    if response.status_code in (403, 503, 429):
        return True
    if response.status_code in (403, 503, 429, 503):
        logger.warning(f"HTTP {response.status_code} — engellendi.")
        return True
    if len(html) < 2000:
        logger.warning(f"Yanıt çok kısa ({len(html)} byte) — engellendi veya boş sayfa.")
        return True
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").lower() if soup.title else ""
    logger.debug(f"Sayfa başlığı: {title[:80]}")
    if any(w in title for w in ["403", "captcha", "robot", "hata", "error", "engel", "erişim"]):
        logger.warning(f"Engel başlığı tespit edildi: {title[:80]}")
        return True
    if soup.find("input", {"name": re.compile(r"password|sifre", re.I)}):
        logger.warning("Giriş sayfasına yönlendirildi.")
        return True
    return False


# Çalışan proxy önbelleği — her seferinde yeniden arama yapma
_proxy_cache: dict | None = None
_proxy_fail_count: int = 0


def _get_proxy() -> dict | None:
    """Çalışan bir proxy döndür. 3 farklı proxy dener, önbelleğe alır."""
    global _proxy_cache, _proxy_fail_count

    # Önbellekteki proxy hâlâ geçerliyse kullan
    if _proxy_cache and _proxy_fail_count < 3:
        return _proxy_cache

    try:
        from fp.fp import FreeProxy
        # Farklı ülke grupları dene
        country_groups = [
            ["DE", "NL", "FR"],
            ["PL", "CZ", "AT", "RO"],
            None,  # Tüm ülkeler
        ]
        for countries in country_groups:
            try:
                kwargs = {"timeout": 2, "rand": True, "anonym": True}
                if countries:
                    kwargs["country_id"] = countries
                proxy_url = FreeProxy(**kwargs).get()
                if proxy_url:
                    logger.info(f"Proxy bulundu: {proxy_url}")
                    _proxy_cache = {"http": proxy_url, "https": proxy_url}
                    _proxy_fail_count = 0
                    return _proxy_cache
            except Exception:
                continue
    except ImportError:
        logger.warning("free-proxy kurulu değil: pip install free-proxy")
    except Exception as e:
        logger.debug(f"Proxy alınamadı: {e}")

    _proxy_cache = None
    return None


def _invalidate_proxy():
    """Mevcut proxy çalışmıyor, önbelleği temizle."""
    global _proxy_cache, _proxy_fail_count
    _proxy_cache = None
    _proxy_fail_count += 1


async def _fetch_with_playwright_async(url: str) -> str | None:
    """async_playwright ile Cloudflare'ı geçerek sayfayı çek. Greenlet gerektirmez."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=random.choice(HEADERS_LIST)["User-Agent"],
                viewport={"width": 1920, "height": 1080},
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
            )
            page = await context.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            await page.goto(url, wait_until="networkidle", timeout=30000)
            import asyncio as _asyncio
            await _asyncio.sleep(3)
            html = await page.content()
            await browser.close()
            logger.info(f"Playwright async: {len(html)} byte alındı.")
            return html
    except Exception as e:
        logger.error(f"Playwright async hatası: {e}")
        return None


def _fetch_with_playwright(url: str) -> str | None:
    """Thread içinden async Playwright çağrısı (greenlet yok)."""
    import asyncio
    try:
        return asyncio.run(_fetch_with_playwright_async(url))
    except Exception as e:
        logger.error(f"Playwright çalıştırma hatası: {e}")
        return None


def _make_session(use_proxy: bool = False) -> tuple:
    headers = random.choice(HEADERS_LIST)
    session = requests.Session()
    if use_proxy:
        proxy = _get_proxy()
        if proxy:
            session.proxies.update(proxy)
    return session, headers


def fetch_listings(url: str, max_pages: int = 5) -> list[dict] | None:
    """
    Sahibinden.com'dan ilanları çek.
    Engellenirsе free-proxy ile otomatik tekrar dener (3 proxy dener).
    Returns:
        None  → engellenemedi / bağlantı hatası
        []    → sayfa açıldı ama ilan bulunamadı
        [..] → başarılı
    """
    # Önce Playwright ile dene (Cloudflare'ı geçer)
    logger.info(f"Playwright ile çekiliyor: {url[:60]}")
    html = _fetch_with_playwright(url)
    if html:
        listings = parse_listings(html, url)
        if listings is not None:
            return listings

    # Playwright başarısız — direkt requests dene
    logger.info("Playwright başarısız, direkt bağlantı deneniyor...")
    result = _fetch_with_session(url, max_pages, use_proxy=False)
    if result is not None:
        return result

    # Son çare — proxy ile dene
    logger.info("Direkt bağlantı engellendi, proxy deneniyor...")
    for attempt in range(2):
        result = _fetch_with_session(url, max_pages, use_proxy=True)
        if result is not None:
            return result
        _invalidate_proxy()

    logger.warning("Tüm yöntemler başarısız.")
    return None


def _fetch_with_session(url: str, max_pages: int, use_proxy: bool) -> list[dict] | None:
    base_url = normalize_url(url)
    all_listings = []

    parsed_params = parse_qs(urlparse(url).query)
    page_size = int(parsed_params.get("pagingSize", ["20"])[0])

    try:
        session, headers = _make_session(use_proxy=use_proxy)

        try:
            r0 = session.get(SAHIBINDEN_BASE, headers=headers, timeout=15)
            logger.debug(f"Ana sayfa: status={r0.status_code}, {len(r0.text)} byte")
        except Exception as e:
            logger.debug(f"Ana sayfa alınamadı: {e}")
        time.sleep(random.uniform(3, 6))

        for page in range(max_pages):
            offset = page * page_size
            page_url = make_page_url(base_url, offset) if page > 0 else base_url

            try:
                response = session.get(page_url, headers=headers, timeout=20)
            except requests.exceptions.ConnectionError:
                logger.error("Bağlantı hatası.")
                return None
            except requests.exceptions.Timeout:
                logger.error("Zaman aşımı.")
                return None

            if _is_blocked_or_error(response.text, response):
                logger.warning(f"Sayfa {page + 1}: Engellendi (status={response.status_code}).")
                if use_proxy:
                    _invalidate_proxy()  # Bu proxy çalışmıyor, bir sonrakini dene
                if page == 0:
                    return None
                break

            page_listings = parse_listings(response.text, page_url)

            if page_listings is None:
                # Parse hatası — ilk sayfada ise hata, sonrakinde dur
                logger.warning(f"Sayfa {page + 1}: Parse başarısız.")
                if page == 0:
                    return None
                break

            if not page_listings:
                logger.info(f"Sayfa {page + 1}: İlan yok, durduruldu.")
                break

            all_listings.extend(page_listings)
            logger.info(f"Sayfa {page + 1}: {len(page_listings)} ilan, toplam: {len(all_listings)}")

            if len(page_listings) < page_size:
                logger.info("Son sayfaya ulaşıldı.")
                break

            if page < max_pages - 1:
                time.sleep(random.uniform(1.5, 3))

        return all_listings

    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}")
        return None


def parse_listings(html: str, base_url: str) -> list[dict] | None:
    """
    HTML'den ilan listesini parse et.
    Returns:
        None  → sayfa yapısı tanınamadı (muhtemelen hata/engel sayfası)
        []    → geçerli sayfa ama ilan yok
        [..] → ilanlar
    """
    soup = BeautifulSoup(html, "html.parser")

    # --- Yöntem 1: Standart arama sonuçları tablosu ---
    table = (
        soup.find("table", {"class": re.compile(r"searchResultsTable|result-list")}) or
        soup.find("table", id="searchResultsTable")
    )
    if table:
        rows = table.find_all("tr", {"class": re.compile(r"searchResultsItem|.*result.*")})
        listings = []
        for row in rows:
            try:
                listing = _parse_table_row(row)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Satır parse hatası: {e}")
        logger.info(f"Tablo parser: {len(listings)} ilan — {base_url[:60]}")
        return listings

    # --- Yöntem 2: Galeri / vitrin / kart görünümü ---
    gallery_listings = _parse_gallery(soup, base_url)
    if gallery_listings is not None:
        return gallery_listings

    # --- Sayfa sahibinden'e ait mi kontrol et ---
    if not _looks_like_sahibinden(soup):
        logger.warning(f"Sahibinden sayfası tanınamadı: {base_url[:60]}")
        return None

    logger.info(f"Geçerli sayfa ama ilan yok: {base_url[:60]}")
    return []


def _looks_like_sahibinden(soup) -> bool:
    """Sayfanın gerçekten sahibinden.com sayfası olup olmadığını kontrol et."""
    # Meta, link veya script içinde sahibinden referansı
    for tag in soup.find_all(["meta", "link", "script"], limit=30):
        content = str(tag)
        if "sahibinden" in content.lower():
            return True
    # Başlık kontrolü
    title = (soup.title.string or "").lower() if soup.title else ""
    return "sahibinden" in title


def _parse_gallery(soup, base_url: str) -> list[dict] | None:
    """Galeri/vitrin/kart görünümü için ilan parse et."""
    seen_ids: set[str] = set()
    listings = []

    # --- Yöntem A: data-id attribute taşıyan herhangi bir element ---
    candidates = soup.find_all(attrs={"data-id": re.compile(r"^\d+$")})
    for elem in candidates:
        listing_id = elem.get("data-id", "").strip()
        if not listing_id or listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        link = (
            elem.find("a", href=re.compile(r"/ilan/")) or
            elem.find("a", class_=re.compile(r"classifiedTitle|title", re.I)) or
            elem.find("a", href=True)
        )
        title = ""
        listing_url = ""
        if link:
            title = link.get("title") or link.get_text(strip=True)
            href = link.get("href", "")
            listing_url = SAHIBINDEN_BASE + href if href.startswith("/") else href

        price_elem = elem.find(class_=re.compile(r"price|fiyat", re.I))
        price = price_elem.get_text(strip=True) if price_elem else "Belirtilmemiş"

        location_elem = elem.find(class_=re.compile(r"location|konum|city|sehir", re.I))
        location = location_elem.get_text(strip=True) if location_elem else ""

        date_elem = elem.find(class_=re.compile(r"date|tarih", re.I))
        date = date_elem.get_text(strip=True) if date_elem else ""

        listings.append({
            "id": listing_id,
            "title": title or "Başlık yok",
            "description": "",
            "price": price,
            "location": location,
            "url": listing_url,
            "date": date,
        })

    if listings:
        logger.info(f"Galeri parser (data-id): {len(listings)} ilan — {base_url[:60]}")
        return listings

    # --- Yöntem B: /ilan/ URL pattern içeren tüm linkler ---
    for link in soup.find_all("a", href=re.compile(r"/ilan/")):
        href = link.get("href", "")
        id_match = re.search(r"/(\d{6,})", href)  # En az 6 haneli ID
        if not id_match:
            continue
        listing_id = id_match.group(1)
        if listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        title = link.get("title") or link.get_text(strip=True)
        listing_url = SAHIBINDEN_BASE + href if href.startswith("/") else href

        listings.append({
            "id": listing_id,
            "title": title or "Başlık yok",
            "description": "",
            "price": "Belirtilmemiş",
            "location": "",
            "url": listing_url,
            "date": "",
        })

    if listings:
        logger.info(f"Galeri parser (/ilan/ links): {len(listings)} ilan — {base_url[:60]}")
        return listings

    # Hiçbir yöntem sonuç vermedi — sayfa sahibinden ama ilan yok
    return None


def _parse_table_row(row) -> dict | None:
    """Tek bir ilan satırını parse et (tablo görünümü)."""
    listing_id = row.get("data-id") or row.get("id", "")
    if not listing_id:
        link = row.find("a", href=re.compile(r"/ilan/"))
        if link:
            match = re.search(r"/(\d+)$", link.get("href", ""))
            if match:
                listing_id = match.group(1)

    if not listing_id or listing_id == "searchResultsTable":
        return None

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

    price_elem = row.find("td", {"class": re.compile(r"searchResultsPriceValue|price")})
    price = price_elem.get_text(strip=True) if price_elem else "Belirtilmemiş"

    location_elem = row.find("td", {"class": re.compile(r"searchResultsLocationValue|location")})
    location = ""
    if location_elem:
        parts = [s.get_text(strip=True) for s in location_elem.find_all("span")]
        location = " / ".join(filter(None, parts)) or location_elem.get_text(strip=True)

    date_elem = row.find("td", {"class": re.compile(r"searchResultsDateValue|date")})
    date = date_elem.get_text(strip=True) if date_elem else ""

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
    result = listings

    if keywords and keywords.strip():
        keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        if keyword_list:
            filtered = []
            for listing in result:
                search_text = (listing["title"] + " " + listing.get("description", "")).lower()
                if any(kw in search_text for kw in keyword_list):
                    filtered.append(listing)
            result = filtered

    if min_price is not None or max_price is not None:
        filtered = []
        for listing in result:
            price_val = parse_price_value(listing["price"])
            if price_val is None:
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
    lines = [
        f"🔔 *Yeni İlan — {filter_name}*",
        "",
        f"📌 {listing['title']}",
        f"💰 {listing['price']}",
    ]
    if listing.get("location"):
        lines.append(f"📍 {listing['location']}")
    if listing.get("date"):
        lines.append(f"📅 {listing['date']}")
    if listing.get("url"):
        lines.append("")
        lines.append(f"🔗 [İlana Git]({listing['url']})")
    return "\n".join(lines)

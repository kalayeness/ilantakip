from scraper import _fetch_with_playwright, parse_listings

# Vitrin yerine gerçek arama sayfaları dene
urls = [
    "https://www.sahibinden.com/otomobil",
    "https://www.sahibinden.com/kiralik-daire/istanbul",
    "https://www.sahibinden.com/kategori-vitrin?viewType=Gallery&category=3530&sorting=date_desc",
]

for url in urls:
    print(f"\n{'='*60}")
    print(f"Test: {url[:70]}")
    html = _fetch_with_playwright(url)

    if not html:
        print("HATA: Sayfa alinamadi.")
        continue

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    baslik = soup.title.string if soup.title else "BOS"
    print(f"Baslik: {baslik}")
    print(f"Boyut: {len(html)} byte")

    listings = parse_listings(html, url)
    if listings is None:
        print("Parse hatasi: sayfa yapisi taninamadi.")
        print(f"HTML baslangici:\n{html[:300]}")
    elif len(listings) == 0:
        print("Sayfa acildi ama ilan bulunamadi.")
    else:
        print(f"BASARILI! {len(listings)} ilan:")
        for i in listings[:3]:
            print(f"  [{i['id']}] {i['title'][:60]} | {i['price']}")

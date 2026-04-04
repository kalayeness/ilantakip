from scraper import _fetch_with_playwright, parse_listings, _is_blocked_or_error

url = "https://www.sahibinden.com/kategori-vitrin?viewType=Gallery&category=3530&sorting=date_desc"

print("Playwright ile cekiliyor...")
html = _fetch_with_playwright(url)

if not html:
    print("HATA: Playwright sayfa alamadi.")
else:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    baslik = soup.title.string if soup.title else "YOK"
    print(f"Baslik: {baslik}")
    print(f"Boyut: {len(html)} byte")

    listings = parse_listings(html, url)
    if listings is None:
        print("Parse hatasi: ilan tablosu bulunamadi.")
        print(f"HTML baslangici:\n{html[:400]}")
    elif len(listings) == 0:
        print("Sayfa acildi ama ilan bulunamadi.")
    else:
        print(f"Basarili! {len(listings)} ilan bulundu:")
        for i in listings[:3]:
            print(f"  - [{i['id']}] {i['title']} | {i['price']}")

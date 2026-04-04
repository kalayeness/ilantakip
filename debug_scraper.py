from scraper import _fetch_with_playwright
from bs4 import BeautifulSoup

url = "https://www.sahibinden.com/otomobil"
html = _fetch_with_playwright(url)

if not html:
    print("Sayfa alinamadi.")
else:
    soup = BeautifulSoup(html, "html.parser")
    # Sayfadaki tüm metni göster
    print("=== GORUNEN METIN ===")
    print(soup.get_text(separator="\n", strip=True)[:1000])
    print("\n=== TUM HTML (ilk 2000 karakter) ===")
    print(html[:2000])

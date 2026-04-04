import time
import random
import cloudscraper
from scraper import _is_blocked_or_error, HEADERS_LIST
from bs4 import BeautifulSoup

headers = random.choice(HEADERS_LIST)
session = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

print("Ana sayfaya baglaniliyor...")
r0 = session.get("https://www.sahibinden.com", headers=headers, timeout=15)
print(f"Ana sayfa: status={r0.status_code}, {len(r0.text)} byte")
time.sleep(4)

url = "https://www.sahibinden.com/kategori-vitrin?viewType=Gallery&category=3530&sorting=date_desc"
print("Hedef sayfaya baglaniliyor...")
r = session.get(url, headers=headers, timeout=20)
print(f"Hedef sayfa: status={r.status_code}, {len(r.text)} byte")
print(f"Engellendi mi: {_is_blocked_or_error(r.text, r)}")

soup = BeautifulSoup(r.text, "html.parser")
baslik = soup.title.string if soup.title else "YOK"
print(f"Baslik: {baslik}")
print(f"HTML baslangici:\n{r.text[:300]}")

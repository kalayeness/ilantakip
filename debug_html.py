"""ScraperAPI'den gelen HTML'i kaydeder, parser ne görüyor gösterir."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import SCRAPERAPI_KEY
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.sahibinden.com/opel-astra-1.6-cdti-design?pagingSize=50&sorting=date_desc"

print(f"ScraperAPI ile çekiliyor (render=false)...")
r = requests.get("http://api.scraperapi.com", params={
    "api_key": SCRAPERAPI_KEY,
    "url": URL,
    "render": "false",
}, timeout=90)

print(f"HTTP {r.status_code} — {len(r.text)} byte")

# Dosyaya kaydet
with open("debug_page.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("debug_page.html dosyasına kaydedildi.")

# Parser ne buluyor?
soup = BeautifulSoup(r.text, "html.parser")
print(f"\nSayfa başlığı: {soup.title.string if soup.title else 'YOK'}")

# Tablo var mı?
table = soup.find("table", {"class": re.compile(r"searchResultsTable|result-list")}) or soup.find("table", id="searchResultsTable")
print(f"searchResultsTable: {'BULUNDU' if table else 'YOK'}")

# Tüm table'lar
tables = soup.find_all("table")
print(f"Toplam <table> sayısı: {len(tables)}")
for t in tables[:5]:
    print(f"  - id={t.get('id')} class={t.get('class')}")

# data-id olan elementler
data_ids = soup.find_all(attrs={"data-id": True})
print(f"\ndata-id olan element sayısı: {len(data_ids)}")
for d in data_ids[:5]:
    print(f"  - tag={d.name} data-id={d.get('data-id')} class={d.get('class')}")

# /ilan/ linkleri
ilan_links = soup.find_all("a", href=re.compile(r"/ilan/"))
print(f"\n/ilan/ içeren link sayısı: {len(ilan_links)}")
for l in ilan_links[:5]:
    print(f"  - href={l.get('href', '')[:60]} title={l.get('title', '')[:40]}")

# searchResult class'lı elementler
search_results = soup.find_all(class_=re.compile(r"searchResult", re.I))
print(f"\nsearchResult class'lı element: {len(search_results)}")
for s in search_results[:5]:
    print(f"  - tag={s.name} class={s.get('class')}")

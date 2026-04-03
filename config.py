import os
from dotenv import load_dotenv

# Script'in bulunduğu klasör — nereden çalıştırılırsa çalıştırılsın sabit
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "50"))
# Veritabanı her zaman bot.py'nin yanındaki data/ klasöründe
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "data", "ilantakip.db"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN ortam değişkeni ayarlanmamış!")


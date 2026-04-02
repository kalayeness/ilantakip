import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "3"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/ilantakip.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN ortam değişkeni ayarlanmamış!")

import aiosqlite
import os

# Backend klasörünün bir üstündeki data/ klasörü — Telegram botu ile aynı DB
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "data", "ilantakip.db"))


async def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                fcm_token TEXT,
                telegram_chat_id TEXT,
                notifications_enabled INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER,
                search_url TEXT,
                search_name TEXT,
                keywords TEXT,
                min_price REAL,
                max_price REAL,
                target_price REAL,
                platforms TEXT,
                active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


async def db_fetch(sql: str, params: tuple = ()) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def db_execute(sql: str, params: tuple = ()) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(sql, params)
        await db.commit()
        return cursor.lastrowid


async def get_db():
    """FastAPI dependency — artık kullanılmıyor ama uyumluluk için bırakıldı."""
    yield None

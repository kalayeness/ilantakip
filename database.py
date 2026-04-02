import aiosqlite
import os
from config import DATABASE_PATH


async def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                keywords TEXT DEFAULT '',
                min_price INTEGER DEFAULT NULL,
                max_price INTEGER DEFAULT NULL,
                active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Mevcut DB'ye yeni sütunlar ekle (migration)
        for col, definition in [
            ("keywords", "TEXT DEFAULT ''"),
            ("min_price", "INTEGER DEFAULT NULL"),
            ("max_price", "INTEGER DEFAULT NULL"),
        ]:
            try:
                await db.execute(f"ALTER TABLE filters ADD COLUMN {col} {definition}")
            except Exception:
                pass  # Sütun zaten varsa geç

        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filter_id INTEGER NOT NULL,
                listing_id TEXT NOT NULL,
                title TEXT,
                price TEXT,
                location TEXT,
                url TEXT,
                seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(filter_id, listing_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                notifications_enabled INTEGER DEFAULT 1,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def upsert_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))
        await db.commit()


async def add_filter(
    user_id: int,
    name: str,
    url: str,
    keywords: str = "",
    min_price: int | None = None,
    max_price: int | None = None,
) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO filters (user_id, name, url, keywords, min_price, max_price) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, url, keywords, min_price, max_price)
        )
        await db.commit()
        return cursor.lastrowid


async def get_filters(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM filters WHERE user_id = ? AND active = 1 ORDER BY created_at DESC",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_active_filters() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT f.*, u.notifications_enabled FROM filters f "
            "JOIN users u ON f.user_id = u.user_id "
            "WHERE f.active = 1 AND u.notifications_enabled = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def remove_filter(filter_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE filters SET active = 0 WHERE id = ? AND user_id = ?",
            (filter_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_seen_listing_ids(filter_id: int) -> set[str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT listing_id FROM seen_listings WHERE filter_id = ?",
            (filter_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0] for row in rows}


async def mark_listings_seen(filter_id: int, listings: list[dict]):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executemany(
            """INSERT OR IGNORE INTO seen_listings
               (filter_id, listing_id, title, price, location, url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(filter_id, l["id"], l["title"], l["price"], l["location"], l["url"]) for l in listings]
        )
        await db.commit()


async def toggle_notifications(user_id: int, enabled: bool):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET notifications_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE notifications_enabled = 1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

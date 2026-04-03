from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models.database import db_fetch, db_execute
from api.auth import get_current_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistCreate(BaseModel):
    search_name: str
    search_url: str | None = None
    keywords: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    target_price: float | None = None
    platforms: str | None = None


class WatchlistResponse(BaseModel):
    id: int
    search_name: str
    search_url: str | None
    keywords: str | None
    min_price: float | None
    max_price: float | None
    target_price: float | None
    platforms: str | None
    active: bool


@router.get("", response_model=list[WatchlistResponse])
async def get_watchlist(current_user: dict = Depends(get_current_user)):
    rows = await db_fetch(
        "SELECT * FROM watchlist WHERE user_id = ? AND active = 1 ORDER BY created_at DESC",
        (current_user["id"],)
    )
    return [WatchlistResponse(**{**r, "active": bool(r["active"])}) for r in rows]


@router.post("", response_model=WatchlistResponse)
async def add_to_watchlist(item: WatchlistCreate, current_user: dict = Depends(get_current_user)):
    item_id = await db_execute(
        """INSERT INTO watchlist (user_id, search_name, search_url, keywords, min_price, max_price, target_price, platforms)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (current_user["id"], item.search_name, item.search_url, item.keywords,
         item.min_price, item.max_price, item.target_price, item.platforms)
    )
    rows = await db_fetch("SELECT * FROM watchlist WHERE id = ?", (item_id,))
    r = rows[0]
    return WatchlistResponse(**{**r, "active": bool(r["active"])})


@router.delete("/{item_id}")
async def remove_from_watchlist(item_id: int, current_user: dict = Depends(get_current_user)):
    rows = await db_fetch(
        "SELECT id FROM watchlist WHERE id = ? AND user_id = ?",
        (item_id, current_user["id"])
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    await db_execute("UPDATE watchlist SET active = 0 WHERE id = ?", (item_id,))
    return {"ok": True}

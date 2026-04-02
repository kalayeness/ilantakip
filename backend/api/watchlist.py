from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db
from models.tables import WatchlistItem, User
from api.auth import get_current_user

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistCreate(BaseModel):
    search_name: str
    search_url: str | None = None
    query: str | None = None
    platforms: str | None = None
    keywords: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    target_price: float | None = None


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

    class Config:
        from_attributes = True


@router.get("", response_model=list[WatchlistResponse])
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.active == True,
        )
    )
    return result.scalars().all()


@router.post("", response_model=WatchlistResponse)
async def add_to_watchlist(
    item: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    watchlist_item = WatchlistItem(
        user_id=current_user.id,
        search_name=item.search_name,
        search_url=item.search_url,
        keywords=item.keywords,
        min_price=item.min_price,
        max_price=item.max_price,
        target_price=item.target_price,
        platforms=item.platforms,
    )
    db.add(watchlist_item)
    await db.commit()
    await db.refresh(watchlist_item)
    return watchlist_item


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    item.active = False
    await db.commit()
    return {"ok": True}

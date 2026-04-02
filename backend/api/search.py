from fastapi import APIRouter, Query
from pydantic import BaseModel
from scrapers import search_all

router = APIRouter(prefix="/search", tags=["search"])


class ProductResult(BaseModel):
    platform: str
    external_id: str
    title: str
    price: float
    currency: str
    url: str
    image_url: str | None
    is_secondhand: bool
    in_stock: bool
    seller: str | None = None
    location: str | None = None


@router.get("", response_model=list[ProductResult])
async def search_products(
    q: str = Query(..., min_length=2, description="Arama kelimesi"),
    platforms: str = Query(None, description="Virgülle ayrılmış platform listesi: trendyol,hepsiburada,sahibinden"),
    secondhand_only: bool = Query(False, description="Sadece 2. el"),
    new_only: bool = Query(False, description="Sadece sıfır ürün"),
    max_price: float = Query(None),
    min_price: float = Query(None),
    max_pages: int = Query(2, ge=1, le=5),
):
    platform_list = [p.strip() for p in platforms.split(",")] if platforms else None
    results = search_all(q, platforms=platform_list, max_pages=max_pages)

    # Filtrele
    if secondhand_only:
        results = [r for r in results if r.is_secondhand]
    if new_only:
        results = [r for r in results if not r.is_secondhand]
    if max_price:
        results = [r for r in results if r.price <= max_price]
    if min_price:
        results = [r for r in results if r.price >= min_price]

    return [ProductResult(**r.__dict__) for r in results]

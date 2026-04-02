from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ScrapedProduct:
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
    description: str | None = None


class BaseScraper(ABC):
    platform_name: str = ""
    is_secondhand: bool = False

    @abstractmethod
    def search(self, query: str, max_pages: int = 3) -> list[ScrapedProduct]:
        """Ürün ara."""
        pass

    @abstractmethod
    def get_product(self, url: str) -> ScrapedProduct | None:
        """Tek ürün bilgisi çek."""
        pass

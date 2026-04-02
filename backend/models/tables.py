from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    watchlist: Mapped[list["WatchlistItem"]] = relationship(back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(64))        # trendyol, hepsiburada, sahibinden...
    external_id: Mapped[str] = mapped_column(String(255))    # platformdaki ID
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_secondhand: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prices: Mapped[list["PriceHistory"]] = relationship(back_populates="product")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="product")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="TRY")
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship(back_populates="prices")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    # Genel URL takibi (sahibinden filtresi gibi)
    search_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    keywords: Mapped[str | None] = mapped_column(String(512), nullable=True)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # şu fiyata düşünce bildir
    platforms: Mapped[str | None] = mapped_column(String(256), nullable=True)  # virgülle ayrılmış
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="watchlist")
    product: Mapped["Product | None"] = relationship(back_populates="watchlist_items")

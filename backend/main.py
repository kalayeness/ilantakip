import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from api.auth import router as auth_router
from api.search import router as search_router
from api.watchlist import router as watchlist_router
from notifications.push import init_firebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_firebase()
    logger.info("Backend hazır.")
    yield


app = FastAPI(
    title="İlan Takip API",
    description="Fiyat karşılaştırma ve ilan takip servisi",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(search_router)
app.include_router(watchlist_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

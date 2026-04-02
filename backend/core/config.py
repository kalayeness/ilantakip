from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ilantakip.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-this-secret"
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"
    CHECK_INTERVAL_MINUTES: int = 5
    MAX_PAGES: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

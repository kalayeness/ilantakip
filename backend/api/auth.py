from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from models.database import db_fetch, db_execute
from core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token")

    rows = await db_fetch("SELECT * FROM users WHERE id = ?", (user_id,))
    if not rows:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı")
    return rows[0]


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    existing = await db_fetch("SELECT id FROM users WHERE email = ?", (req.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")

    hashed = pwd_context.hash(req.password)
    user_id = await db_execute(
        "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
        (req.email, hashed)
    )
    return TokenResponse(access_token=create_token(user_id))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    rows = await db_fetch("SELECT * FROM users WHERE email = ?", (req.email,))
    if not rows or not pwd_context.verify(req.password, rows[0]["hashed_password"]):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")
    return TokenResponse(access_token=create_token(rows[0]["id"]))


@router.post("/fcm-token")
async def update_fcm_token(body: dict, current_user: dict = Depends(get_current_user)):
    await db_execute(
        "UPDATE users SET fcm_token = ? WHERE id = ?",
        (body.get("token"), current_user["id"])
    )
    return {"ok": True}

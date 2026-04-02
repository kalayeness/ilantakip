import logging
import os
from core.config import settings

logger = logging.getLogger(__name__)

_firebase_initialized = False

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    _firebase_available = True
except ImportError:
    _firebase_available = False
    logger.info("firebase_admin yüklü değil, push bildirimleri devre dışı.")


def init_firebase():
    global _firebase_initialized
    if not _firebase_available or _firebase_initialized:
        return
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase başlatıldı.")
    else:
        logger.info("Firebase credentials yok, push bildirimleri devre dışı.")


def send_push(fcm_token: str, title: str, body: str, data: dict | None = None) -> bool:
    if not _firebase_initialized:
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))
            ),
        )
        messaging.send(message)
        return True
    except Exception as e:
        logger.error(f"Push gönderilemedi: {e}")
        return False


def send_price_alert(fcm_token: str, product_title: str, old_price: float, new_price: float, url: str):
    drop_pct = int((old_price - new_price) / old_price * 100)
    send_push(fcm_token, title=f"💰 Fiyat Düştü! %{drop_pct}",
              body=f"{product_title[:60]}\n{old_price:,.0f} TL → {new_price:,.0f} TL",
              data={"url": url, "type": "price_alert"})


def send_new_listing_alert(fcm_token: str, title: str, price: float, url: str, platform: str):
    send_push(fcm_token, title=f"🆕 Yeni İlan - {platform.capitalize()}",
              body=f"{title[:60]}\n{price:,.0f} TL",
              data={"url": url, "type": "new_listing"})

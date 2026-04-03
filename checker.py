import asyncio
import logging
from functools import partial
from database import get_all_active_filters, get_seen_listing_ids, mark_listings_seen
from scraper import fetch_listings, format_listing_message, apply_local_filters
import config

logger = logging.getLogger(__name__)


async def check_filter(filter_record: dict) -> list[dict] | None:
    """
    Tek bir filtre için yeni ilanları kontrol et.
    Returns:
        None  → fetch başarısız (bağlantı hatası / engellendi)
        []    → başarılı ama yeni ilan yok
        [..] → yeni ilanlar
    """
    filter_id = filter_record["id"]
    filter_name = filter_record["name"]
    url = filter_record["url"]

    logger.info(f"Filtre kontrol ediliyor: '{filter_name}' (ID: {filter_id})")

    # fetch_listings senkron (requests) — event loop'u bloke etmemek için thread'de çalıştır
    loop = asyncio.get_event_loop()
    current_listings = await loop.run_in_executor(
        None, partial(fetch_listings, url, config.MAX_PAGES)
    )

    if current_listings is None:
        logger.warning(f"Filtre '{filter_name}': İlan listesi alınamadı (bağlantı/engel sorunu).")
        return None

    keywords = filter_record.get("keywords") or ""
    min_price = filter_record.get("min_price")
    max_price = filter_record.get("max_price")
    current_listings = apply_local_filters(current_listings, keywords, min_price, max_price)

    seen_ids = await get_seen_listing_ids(filter_id)
    new_listings = [l for l in current_listings if l["id"] not in seen_ids]

    await mark_listings_seen(filter_id, current_listings)

    if new_listings:
        logger.info(f"Filtre '{filter_name}': {len(new_listings)} yeni ilan bulundu.")
    else:
        logger.info(f"Filtre '{filter_name}': Yeni ilan yok. (Toplam taranan: {len(current_listings)})")

    return new_listings


async def run_all_checks(bot) -> dict[int, dict]:
    filters = await get_all_active_filters()

    if not filters:
        logger.info("Aktif filtre bulunamadı.")
        return {}

    results: dict[int, dict] = {}

    for f in filters:
        user_id = f["user_id"]
        filter_name = f["name"]

        new_listings = await check_filter(f)

        if user_id not in results:
            results[user_id] = {"new": [], "no_new": [], "error": []}

        if new_listings is None:
            results[user_id]["error"].append(filter_name)
        elif new_listings:
            results[user_id]["new"].append({
                "filter_name": filter_name,
                "listings": new_listings,
            })
        else:
            results[user_id]["no_new"].append(filter_name)

    for user_id, data in results.items():
        await send_check_results(bot, user_id, data)

    return results


async def send_check_results(bot, user_id: int, data: dict):
    try:
        # Yeni ilanları bildir
        for filter_data in data["new"]:
            filter_name = filter_data["filter_name"]
            listings = filter_data["listings"]

            for listing in listings[:10]:
                msg = format_listing_message(listing, filter_name)
                await bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    parse_mode="Markdown",
                    disable_web_page_preview=False,
                )

            if len(listings) > 10:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"ℹ️ *{filter_name}*: {len(listings)} yeni ilan var, ilk 10'u gösterildi.",
                    parse_mode="Markdown",
                )

        # Yeni ilan yok bildirimi
        if data.get("no_new"):
            no_new_lines = [f"🔍 *{name}*: Yeni ilan yok" for name in data["no_new"]]
            await bot.send_message(
                chat_id=user_id,
                text="📊 *Kontrol Sonucu*\n\n" + "\n".join(no_new_lines),
                parse_mode="Markdown",
            )

        # Hata bildirimi (opsiyonel — engel durumunda spam yapmasın diye sadece logluyoruz)
        # Hata olan filtreler sessizce geçilir, kullanıcıya bildirim gönderilmez

    except Exception as e:
        logger.error(f"Kullanıcı {user_id}'e mesaj gönderilemedi: {e}")

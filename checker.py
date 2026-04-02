import logging
from database import get_all_active_filters, get_seen_listing_ids, mark_listings_seen
from scraper import fetch_listings, format_listing_message

logger = logging.getLogger(__name__)


async def check_filter(filter_record: dict) -> list[dict]:
    """
    Tek bir filtre için yeni ilanları kontrol et.
    Yeni ilanların listesini döndürür.
    """
    filter_id = filter_record["id"]
    filter_name = filter_record["name"]
    url = filter_record["url"]

    logger.info(f"Filtre kontrol ediliyor: '{filter_name}' (ID: {filter_id})")

    # Mevcut ilanları çek
    current_listings = fetch_listings(url)
    if not current_listings:
        logger.info(f"Filtre '{filter_name}': İlan listesi alınamadı veya boş.")
        return []

    # Daha önce görülen ilanları al
    seen_ids = await get_seen_listing_ids(filter_id)

    # Yeni ilanları bul
    new_listings = [l for l in current_listings if l["id"] not in seen_ids]

    # Tüm mevcut ilanları "görüldü" olarak işaretle
    await mark_listings_seen(filter_id, current_listings)

    if new_listings:
        logger.info(f"Filtre '{filter_name}': {len(new_listings)} yeni ilan bulundu.")
    else:
        logger.info(f"Filtre '{filter_name}': Yeni ilan yok.")

    return new_listings


async def run_all_checks(bot) -> dict[int, dict]:
    """
    Tüm aktif filtreleri kontrol et.
    Kullanıcı ID'sine göre sonuçları döndürür.
    """
    filters = await get_all_active_filters()

    if not filters:
        logger.info("Aktif filtre bulunamadı.")
        return {}

    # Kullanıcı bazında sonuçları grupla
    results: dict[int, dict] = {}

    for f in filters:
        user_id = f["user_id"]
        filter_name = f["name"]

        new_listings = await check_filter(f)

        if user_id not in results:
            results[user_id] = {"new": [], "no_new": []}

        if new_listings:
            results[user_id]["new"].append({
                "filter_name": filter_name,
                "listings": new_listings,
            })
        else:
            results[user_id]["no_new"].append(filter_name)

    # Telegram mesajlarını gönder
    for user_id, data in results.items():
        await send_check_results(bot, user_id, data)

    return results


async def send_check_results(bot, user_id: int, data: dict):
    """Kullanıcıya kontrol sonuçlarını bildir."""
    try:
        # Yeni ilanları bildir
        for filter_data in data["new"]:
            filter_name = filter_data["filter_name"]
            listings = filter_data["listings"]

            for listing in listings[:10]:  # Fazla spam olmasın diye max 10
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

        # Yeni ilan olmayan filtreleri bildir
        if data["no_new"]:
            no_new_lines = [f"🔍 *{name}*: Yeni ilan yok" for name in data["no_new"]]
            msg = "📊 *Kontrol Sonucu*\n\n" + "\n".join(no_new_lines)
            await bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(f"Kullanıcı {user_id}'e mesaj gönderilemedi: {e}")

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from database import (
    init_db, upsert_user, add_filter, get_filters,
    remove_filter, toggle_notifications,
)
from checker import run_all_checks
from scraper import validate_sahibinden_url

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL),
)
logger = logging.getLogger(__name__)

# Konuşma durumları
WAITING_FILTER_NAME, WAITING_FILTER_URL = range(2)

# Geçici kullanıcı verisi
user_states: dict[int, dict] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username or "", user.first_name or "")

    text = (
        f"👋 Merhaba *{user.first_name}*!\n\n"
        f"Ben *İlan Takip Botu*'yum. Sahibinden.com'daki ilanları {config.CHECK_INTERVAL_MINUTES} dakikada "
        f"bir kontrol eder ve yeni ilanları sana bildiririm.\n\n"
        f"📋 *Komutlar:*\n"
        f"/filtre\\_ekle — Yeni arama filtresi ekle\n"
        f"/filtrelerim — Aktif filtrelerini listele\n"
        f"/filtre\\_sil — Filtre sil\n"
        f"/simdi\\_kontrol — Hemen kontrol et\n"
        f"/bildirimleri\\_durdur — Bildirimleri durdur\n"
        f"/bildirimleri\\_baslat — Bildirimleri başlat\n"
        f"/yardim — Yardım mesajı\n\n"
        f"🚀 Başlamak için /filtre\\_ekle komutunu kullan!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Nasıl Kullanılır?*\n\n"
        "1️⃣ Sahibinden.com'a git\n"
        "2️⃣ Arama filtrelerini ayarla (il, ilçe, fiyat, m² vb.)\n"
        "3️⃣ Arama sonuçları sayfasının URL'sini kopyala\n"
        "4️⃣ /filtre\\_ekle komutunu kullan ve URL'yi yapıştır\n\n"
        "✅ Bot artık o filtreyle her "
        f"{config.CHECK_INTERVAL_MINUTES} dakikada bir sahibinden.com'u kontrol eder!\n\n"
        "📌 *Örnek URL:*\n"
        "`https://www.sahibinden.com/kiralik-daire/istanbul?`\n"
        "`price_min=5000&price_max=15000`\n\n"
        "⚠️ *Not:* Sahibinden.com zaman zaman bot erişimini engelleyebilir. "
        "Bu durumda kontrol atlanır ve tekrar denenir."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def filtre_ekle_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {}
    await update.message.reply_text(
        "📝 Filtren için bir isim gir:\n_(örn: İstanbul Kiralik 2+1)_",
        parse_mode="Markdown",
    )
    return WAITING_FILTER_NAME


async def filtre_isim_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()

    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("❌ İsim 2-50 karakter arasında olmalı. Tekrar dene:")
        return WAITING_FILTER_NAME

    user_states[user_id]["name"] = name
    await update.message.reply_text(
        f"✅ İsim: *{name}*\n\n"
        "🔗 Şimdi sahibinden.com arama URL'sini yapıştır:\n"
        "_(Sahibinden.com'da filtreleri ayarlayıp adres çubuğundaki URL'yi kopyala)_",
        parse_mode="Markdown",
    )
    return WAITING_FILTER_URL


async def filtre_url_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()

    if not validate_sahibinden_url(url):
        await update.message.reply_text(
            "❌ Geçersiz URL! Sahibinden.com adresi olmalı.\n"
            "_(örn: https://www.sahibinden.com/kiralik-daire/istanbul)_\n\n"
            "Tekrar dene:",
            parse_mode="Markdown",
        )
        return WAITING_FILTER_URL

    name = user_states[user_id]["name"]
    await upsert_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    filter_id = await add_filter(user_id, name, url)

    user_states.pop(user_id, None)

    await update.message.reply_text(
        f"✅ *Filtre eklendi!*\n\n"
        f"📌 İsim: {name}\n"
        f"🔗 URL: `{url[:80]}{'...' if len(url) > 80 else ''}`\n\n"
        f"Bot artık her {config.CHECK_INTERVAL_MINUTES} dakikada bir bu filtreyi kontrol edecek.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def filtre_ekle_iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states.pop(user_id, None)
    await update.message.reply_text("❌ Filtre ekleme iptal edildi.")
    return ConversationHandler.END


async def filtrelerim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await upsert_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    filters_list = await get_filters(user_id)

    if not filters_list:
        await update.message.reply_text(
            "📭 Henüz aktif filtren yok.\n/filtre\\_ekle ile yeni filtre ekle!",
            parse_mode="Markdown",
        )
        return

    lines = [f"📋 *Aktif Filtreler ({len(filters_list)} adet):*\n"]
    for f in filters_list:
        url_short = f['url'][:60] + "..." if len(f['url']) > 60 else f['url']
        lines.append(f"*{f['id']}* — {f['name']}\n`{url_short}`\n")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


async def filtre_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    filters_list = await get_filters(user_id)

    if not filters_list:
        await update.message.reply_text(
            "📭 Silinecek aktif filtren yok.",
            parse_mode="Markdown",
        )
        return

    keyboard = []
    for f in filters_list:
        keyboard.append([InlineKeyboardButton(
            f"🗑 {f['name']} (ID: {f['id']})",
            callback_data=f"del_{f['id']}"
        )])
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="del_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hangi filtreyi silmek istiyorsun?",
        reply_markup=reply_markup,
    )


async def filtre_sil_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "del_cancel":
        await query.edit_message_text("❌ İptal edildi.")
        return

    filter_id = int(query.data.replace("del_", ""))
    success = await remove_filter(filter_id, user_id)

    if success:
        await query.edit_message_text(f"✅ Filtre (ID: {filter_id}) silindi.")
    else:
        await query.edit_message_text("❌ Filtre silinemedi. Geçersiz ID veya filtre sana ait değil.")


async def simdi_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await upsert_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
    filters_list = await get_filters(user_id)

    if not filters_list:
        await update.message.reply_text(
            "📭 Kontrol edilecek aktif filtren yok.\n/filtre\\_ekle ile filtre ekle!",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text("🔍 Kontrol ediliyor, lütfen bekle...")

    from checker import check_filter, send_check_results
    data = {"new": [], "no_new": []}

    for f in filters_list:
        new_listings = await check_filter(f)
        if new_listings:
            data["new"].append({"filter_name": f["name"], "listings": new_listings})
        else:
            data["no_new"].append(f["name"])

    await msg.delete()

    if not data["new"] and not data["no_new"]:
        await update.message.reply_text("⚠️ Filtrelerden sonuç alınamadı.")
        return

    await send_check_results(context.bot, user_id, data)


async def bildirimleri_durdur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await toggle_notifications(user_id, False)
    await update.message.reply_text(
        "🔕 Bildirimler durduruldu.\n"
        "Tekrar başlatmak için /bildirimleri\\_baslat komutunu kullan.",
        parse_mode="Markdown",
    )


async def bildirimleri_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await toggle_notifications(user_id, True)
    await update.message.reply_text(
        f"🔔 Bildirimler açıldı!\n"
        f"Her {config.CHECK_INTERVAL_MINUTES} dakikada bir kontrol edilecek.",
        parse_mode="Markdown",
    )


async def scheduled_check(application):
    """Zamanlanmış kontrol - tüm filtreler için çalışır."""
    logger.info("Zamanlanmış kontrol başlıyor...")
    try:
        await run_all_checks(application.bot)
    except Exception as e:
        logger.error(f"Zamanlanmış kontrol hatası: {e}")


def main():
    asyncio.run(run_bot())


async def run_bot():
    # Veritabanını başlat
    await init_db()
    logger.info("Veritabanı hazır.")

    # Bot uygulamasını oluştur
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Filtre ekleme konuşma işleyicisi
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("filtre_ekle", filtre_ekle_baslat)],
        states={
            WAITING_FILTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_isim_al)
            ],
            WAITING_FILTER_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_url_al)
            ],
        },
        fallbacks=[CommandHandler("iptal", filtre_ekle_iptal)],
    )

    # Komutları ekle
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("yardim", yardim))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("filtrelerim", filtrelerim))
    application.add_handler(CommandHandler("filtre_sil", filtre_sil))
    application.add_handler(CommandHandler("simdi_kontrol", simdi_kontrol))
    application.add_handler(CommandHandler("bildirimleri_durdur", bildirimleri_durdur))
    application.add_handler(CommandHandler("bildirimleri_baslat", bildirimleri_baslat))
    application.add_handler(CallbackQueryHandler(filtre_sil_callback, pattern=r"^del_"))

    # Zamanlanmış kontrol - APScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_check,
        trigger=IntervalTrigger(minutes=config.CHECK_INTERVAL_MINUTES),
        args=[application],
        id="listing_check",
        name=f"Her {config.CHECK_INTERVAL_MINUTES} dk ilan kontrolü",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Zamanlayıcı başlatıldı: {config.CHECK_INTERVAL_MINUTES} dakikada bir kontrol.")

    # Botu başlat
    logger.info("Bot başlatılıyor...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot çalışıyor! Durdurmak için Ctrl+C.")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    main()

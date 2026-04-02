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
from scraper import parse_price_value
from checker import run_all_checks
from scraper import validate_sahibinden_url

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL),
)
logger = logging.getLogger(__name__)

# Konuşma durumları
WAITING_FILTER_NAME, WAITING_FILTER_URL, WAITING_FILTER_KEYWORDS, WAITING_FILTER_PRICE = range(4)

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
        f"/filtre\\_detay — Filtre detayını gör (tam URL, kelimeler, fiyat)\n"
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

    user_states[user_id]["url"] = url
    await update.message.reply_text(
        "🎨 *Anahtar kelime filtresi* _(isteğe bağlı)_\n\n"
        "İlan başlığında aranacak kelimeleri virgülle yaz:\n"
        "_(örn: `gök mavisi, uzay grisi, silver`)_\n\n"
        "Atlamak için `-` yaz veya `/atla` kullan.",
        parse_mode="Markdown",
    )
    return WAITING_FILTER_KEYWORDS


async def filtre_keywords_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    keywords = "" if text in ("-", "/atla") else text
    user_states[user_id]["keywords"] = keywords

    await update.message.reply_text(
        "💰 *Fiyat filtresi* _(isteğe bağlı)_\n\n"
        "Fiyat aralığını belirt:\n"
        "• Sadece maksimum: `35000`\n"
        "• Aralık: `10000-35000`\n\n"
        "Atlamak için `-` yaz veya `/atla` kullan.",
        parse_mode="Markdown",
    )
    return WAITING_FILTER_PRICE


async def filtre_price_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    min_price = None
    max_price = None

    if text not in ("-", "/atla"):
        if "-" in text:
            parts = text.split("-", 1)
            min_price = parse_price_value(parts[0]) if parts[0].strip() else None
            max_price = parse_price_value(parts[1]) if parts[1].strip() else None
        else:
            max_price = parse_price_value(text)

        if text not in ("-", "/atla") and min_price is None and max_price is None:
            await update.message.reply_text(
                "❌ Geçersiz fiyat formatı. Örnekler: `35000` veya `10000-35000`\n"
                "Atlamak için `-` yaz.",
                parse_mode="Markdown",
            )
            return WAITING_FILTER_PRICE

    user_id_val = update.effective_user.id
    await upsert_user(user_id_val, update.effective_user.username or "", update.effective_user.first_name or "")

    state = user_states[user_id]
    filter_id = await add_filter(
        user_id_val,
        state["name"],
        state["url"],
        keywords=state.get("keywords", ""),
        min_price=min_price,
        max_price=max_price,
    )
    user_states.pop(user_id, None)

    # Özet mesajı
    lines = [
        "✅ *Filtre eklendi!*\n",
        f"📌 İsim: {state['name']}",
        f"🔗 URL: `{state['url'][:70]}{'...' if len(state['url']) > 70 else ''}`",
    ]
    if state.get("keywords"):
        lines.append(f"🎨 Kelimeler: `{state['keywords']}`")
    if min_price or max_price:
        fiyat_str = f"{min_price or 0:,} - {max_price:,} TL" if max_price else f"{min_price:,}+ TL"
        lines.append(f"💰 Fiyat: {fiyat_str}")
    lines.append(f"\nBot her {config.CHECK_INTERVAL_MINUTES} dakikada bir kontrol edecek.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
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
        entry = f"*{f['id']}* — {f['name']}\n`{url_short}`"
        if f.get("keywords"):
            entry += f"\n🎨 Kelimeler: `{f['keywords']}`"
        if f.get("min_price") or f.get("max_price"):
            mn, mx = f.get("min_price"), f.get("max_price")
            if mn and mx:
                entry += f"\n💰 Fiyat: {mn:,} - {mx:,} TL"
            elif mx:
                entry += f"\n💰 Max fiyat: {mx:,} TL"
            elif mn:
                entry += f"\n💰 Min fiyat: {mn:,} TL"
        lines.append(entry + "\n")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


async def filtre_detay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    filters_list = await get_filters(user_id)

    if not filters_list:
        await update.message.reply_text("📭 Aktif filtren yok.")
        return

    # Argüman verilmişse o filtreyi göster, yoksa hepsini listele
    args = context.args
    if args:
        try:
            filter_id = int(args[0])
            target = next((f for f in filters_list if f["id"] == filter_id), None)
            if not target:
                await update.message.reply_text(f"❌ ID {filter_id} bulunamadı.")
                return
            targets = [target]
        except ValueError:
            await update.message.reply_text("❌ Kullanım: /filtre\\_detay <id>", parse_mode="Markdown")
            return
    else:
        targets = filters_list

    for f in targets:
        mn, mx = f.get("min_price"), f.get("max_price")
        if mn and mx:
            fiyat = f"{mn:,} - {mx:,} TL"
        elif mx:
            fiyat = f"Max {mx:,} TL"
        elif mn:
            fiyat = f"Min {mn:,} TL"
        else:
            fiyat = "Yok"

        text = (
            f"🔍 *Filtre Detayı*\n\n"
            f"🆔 ID: `{f['id']}`\n"
            f"📌 İsim: {f['name']}\n"
            f"🎨 Anahtar Kelimeler: {f.get('keywords') or 'Yok'}\n"
            f"💰 Fiyat Filtresi: {fiyat}\n"
            f"📅 Eklenme: {f.get('created_at', '-')}\n\n"
            f"🔗 *Tam URL:*\n`{f['url']}`"
        )
        await update.message.reply_text(text, parse_mode="Markdown")



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
            WAITING_FILTER_KEYWORDS: [
                CommandHandler("atla", filtre_keywords_al),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_keywords_al)
            ],
            WAITING_FILTER_PRICE: [
                CommandHandler("atla", filtre_price_al),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_price_al)
            ],
        },
        fallbacks=[CommandHandler("iptal", filtre_ekle_iptal)],
    )

    # Komutları ekle
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("yardim", yardim))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("filtrelerim", filtrelerim))
    application.add_handler(CommandHandler("filtre_detay", filtre_detay))
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

import json
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
(WAITING_FILTER_NAME, WAITING_FILTER_URL, WAITING_FILTER_KEYWORDS,
 WAITING_FILTER_PRICE, WAITING_CATEGORY, WAITING_CATEGORY_FILTER) = range(6)

# Geçici kullanıcı verisi
user_states: dict[int, dict] = {}

# Kategori tanımları
CATEGORIES = {
    "araba": {
        "label": "🚗 Araba",
        "filters": [
            {"key": "min_year", "label": "Minimum yıl", "hint": "örn: 2018"},
            {"key": "max_year", "label": "Maksimum yıl", "hint": "örn: 2024"},
            {"key": "max_km", "label": "Maksimum kilometre", "hint": "örn: 100000"},
            {"key": "fuel_type", "label": "Yakıt tipi", "hint": "benzin / dizel / elektrik / hybrid / LPG"},
            {"key": "gear_type", "label": "Vites", "hint": "manuel / otomatik / yarı otomatik"},
            {"key": "color", "label": "Renk", "hint": "örn: beyaz, siyah, gümüş"},
            {"key": "body_type", "label": "Kasa tipi", "hint": "sedan / SUV / hatchback / pickup / minivan"},
        ],
    },
    "ev": {
        "label": "🏠 Ev / Daire",
        "filters": [
            {"key": "min_m2", "label": "Minimum metrekare", "hint": "örn: 80"},
            {"key": "max_m2", "label": "Maksimum metrekare", "hint": "örn: 200"},
            {"key": "room_count", "label": "Oda sayısı", "hint": "örn: 2+1, 3+1, 4+1"},
            {"key": "max_building_age", "label": "Maksimum bina yaşı (yıl)", "hint": "örn: 10"},
            {"key": "floor", "label": "Bulunduğu kat", "hint": "örn: 3, zemin, çatı katı"},
            {"key": "heating", "label": "Isıtma tipi", "hint": "doğalgaz / merkezi / kombi / klima / soba"},
            {"key": "furnished", "label": "Eşya durumu", "hint": "eşyalı / eşyasız / yarı eşyalı"},
            {"key": "site", "label": "Site içinde mi?", "hint": "evet / hayır"},
        ],
    },
    "motosiklet": {
        "label": "🏍 Motosiklet",
        "filters": [
            {"key": "min_year", "label": "Minimum yıl", "hint": "örn: 2019"},
            {"key": "max_year", "label": "Maksimum yıl", "hint": "örn: 2024"},
            {"key": "max_km", "label": "Maksimum kilometre", "hint": "örn: 20000"},
            {"key": "engine_cc", "label": "Motor hacmi (cc)", "hint": "örn: 125, 300, 650, 1000"},
            {"key": "moto_type", "label": "Tip", "hint": "naked / enduro / scooter / sport / touring / chopper"},
            {"key": "color", "label": "Renk", "hint": "örn: kırmızı, siyah"},
        ],
    },
    "elektronik": {
        "label": "📱 Elektronik",
        "filters": [
            {"key": "brand", "label": "Marka", "hint": "örn: Apple, Samsung, Sony"},
            {"key": "storage", "label": "Depolama", "hint": "örn: 128GB, 256GB, 512GB, 1TB"},
            {"key": "ram", "label": "RAM", "hint": "örn: 8GB, 16GB, 32GB"},
            {"key": "color", "label": "Renk", "hint": "örn: uzay grisi, gök mavisi, siyah"},
            {"key": "condition", "label": "Durum", "hint": "sıfır / ikinci el / teşhir / yenilmiş"},
        ],
    },
    "tekne": {
        "label": "⛵ Tekne / Yat",
        "filters": [
            {"key": "boat_type", "label": "Tip", "hint": "yelkenli / motorlu / sürat / karavela / katamaran"},
            {"key": "min_year", "label": "Minimum yıl", "hint": "örn: 2010"},
            {"key": "max_year", "label": "Maksimum yıl", "hint": "örn: 2024"},
            {"key": "min_length", "label": "Minimum uzunluk (m)", "hint": "örn: 7"},
            {"key": "max_length", "label": "Maksimum uzunluk (m)", "hint": "örn: 20"},
            {"key": "engine_hp", "label": "Motor gücü (HP)", "hint": "örn: 150, 300"},
        ],
    },
    "is_makinesi": {
        "label": "🚜 İş Makinesi",
        "filters": [
            {"key": "machine_type", "label": "Makine tipi", "hint": "kepçe / forklift / traktör / vinç / kamyon"},
            {"key": "min_year", "label": "Minimum yıl", "hint": "örn: 2015"},
            {"key": "max_year", "label": "Maksimum yıl", "hint": "örn: 2024"},
            {"key": "max_hours", "label": "Maksimum çalışma saati", "hint": "örn: 5000"},
        ],
    },
    "genel": {
        "label": "🌐 Genel (Kategori Yok)",
        "filters": [],
    },
}


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
    user_states[user_id] = {"category_filters": {}}
    await update.message.reply_text(
        "📝 Filtren için bir isim gir:\n_(örn: Kırmızı Ferrari, MacBook M2, İstanbul Kiralık)_",
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

    # Kategori seçim klavyesi
    keyboard = []
    row = []
    for key, cat in CATEGORIES.items():
        row.append(InlineKeyboardButton(cat["label"], callback_data=f"cat_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        f"✅ İsim: *{name}*\n\n"
        "📂 Kategori seç:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return WAITING_CATEGORY


async def kategori_sec_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category_key = query.data.replace("cat_", "")
    category = CATEGORIES.get(category_key, CATEGORIES["genel"])
    user_states[user_id]["category"] = category_key

    await query.edit_message_text(
        f"✅ Kategori: *{category['label']}*\n\n"
        "🔗 Sahibinden.com arama URL'sini yapıştır:\n"
        "_(Sahibinden.com'da filtreleri ayarlayıp adres çubuğundaki URL'yi kopyala)_",
        parse_mode="Markdown",
    )
    return WAITING_FILTER_URL


async def _ask_next_category_filter(update_or_query, user_id: int, context) -> int:
    """Sıradaki kategori filtresini sor veya bitir."""
    state = user_states[user_id]
    category_key = state.get("category", "genel")
    cat_filters = CATEGORIES[category_key]["filters"]
    asked = state.get("cat_filter_index", 0)

    if asked >= len(cat_filters):
        # Tüm kategori filtreleri bitti, anahtar kelimeye geç
        msg = (
            "🎨 *Anahtar kelime filtresi* _(isteğe bağlı)_\n\n"
            "İlan başlığında aranacak kelimeleri virgülle yaz:\n"
            "_(örn: `kırmızı, metalik, full paket`)_\n\n"
            "Atlamak için `-` yaz veya `/atla` kullan."
        )
        if hasattr(update_or_query, "message") and update_or_query.message:
            await update_or_query.message.reply_text(msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(user_id, msg, parse_mode="Markdown")
        return WAITING_FILTER_KEYWORDS

    f = cat_filters[asked]
    msg = (
        f"*{f['label']}* _(isteğe bağlı)_\n"
        f"_{f['hint']}_\n\n"
        "Atlamak için `-` yaz veya `/atla` kullan."
    )
    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(msg, parse_mode="Markdown")
    else:
        await context.bot.send_message(user_id, msg, parse_mode="Markdown")
    return WAITING_CATEGORY_FILTER


async def kategori_filtre_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_states[user_id]
    category_key = state.get("category", "genel")
    cat_filters = CATEGORIES[category_key]["filters"]
    idx = state.get("cat_filter_index", 0)

    if idx < len(cat_filters) and text not in ("-", "/atla"):
        f = cat_filters[idx]
        state["category_filters"][f["key"]] = text

    state["cat_filter_index"] = idx + 1
    return await _ask_next_category_filter(update, user_id, context)


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
    user_states[user_id]["cat_filter_index"] = 0
    return await _ask_next_category_filter(update, user_id, context)


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
    category_key = state.get("category", "genel")
    cat_filters_json = json.dumps(state.get("category_filters", {}), ensure_ascii=False)
    filter_id = await add_filter(
        user_id_val,
        state["name"],
        state["url"],
        keywords=state.get("keywords", ""),
        min_price=min_price,
        max_price=max_price,
        category=category_key,
        category_filters=cat_filters_json,
    )
    user_states.pop(user_id, None)

    # Özet mesajı
    cat_label = CATEGORIES.get(category_key, CATEGORIES["genel"])["label"]
    lines = [
        "✅ *Filtre eklendi!*\n",
        f"📌 İsim: {state['name']}",
        f"📂 Kategori: {cat_label}",
        f"🔗 URL: `{state['url'][:70]}{'...' if len(state['url']) > 70 else ''}`",
    ]
    cat_filters_data = state.get("category_filters", {})
    if cat_filters_data:
        cat_filters_list = CATEGORIES.get(category_key, {}).get("filters", [])
        for cf in cat_filters_list:
            if cf["key"] in cat_filters_data:
                lines.append(f"   • {cf['label']}: `{cat_filters_data[cf['key']]}`")
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
        cat_key = f.get("category", "genel")
        cat_label = CATEGORIES.get(cat_key, CATEGORIES["genel"])["label"]
        entry = f"*{f['id']}* — {f['name']} [{cat_label}]\n`{url_short}`"
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

        cat_key = f.get("category", "genel")
        cat_label = CATEGORIES.get(cat_key, CATEGORIES["genel"])["label"]

        # Kategori filtrelerini göster
        cat_filters_text = ""
        try:
            cat_filters_data = json.loads(f.get("category_filters") or "{}")
            cat_filter_defs = CATEGORIES.get(cat_key, {}).get("filters", [])
            for cf in cat_filter_defs:
                if cf["key"] in cat_filters_data:
                    cat_filters_text += f"   • {cf['label']}: `{cat_filters_data[cf['key']]}`\n"
        except Exception:
            pass

        text = (
            f"🔍 *Filtre Detayı*\n\n"
            f"🆔 ID: `{f['id']}`\n"
            f"📌 İsim: {f['name']}\n"
            f"📂 Kategori: {cat_label}\n"
        )
        if cat_filters_text:
            text += cat_filters_text
        text += (
            f"🎨 Anahtar Kelimeler: {f.get('keywords') or 'Yok'}\n"
            f"💰 Fiyat Filtresi: {fiyat}\n"
            f"📅 Eklenme: {f.get('created_at', '-')}\n\n"
            f"🔗 *Tam URL:*\n`{f['url']}`"
        )
        await update.message.reply_text(text, parse_mode="Markdown")


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
            WAITING_CATEGORY: [
                CallbackQueryHandler(kategori_sec_callback, pattern=r"^cat_")
            ],
            WAITING_FILTER_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filtre_url_al)
            ],
            WAITING_CATEGORY_FILTER: [
                CommandHandler("atla", kategori_filtre_al),
                MessageHandler(filters.TEXT & ~filters.COMMAND, kategori_filtre_al)
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

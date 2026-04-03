import json
import os
import aiosqlite
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["admin"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOT_DB_PATH = os.path.join(BASE_DIR, "data", "ilantakip.db")

CATEGORY_LABELS = {
    "araba": "🚗 Araba",
    "ev": "🏠 Ev/Daire",
    "motosiklet": "🏍 Motosiklet",
    "elektronik": "📱 Elektronik",
    "tekne": "⛵ Tekne/Yat",
    "is_makinesi": "🚜 İş Makinesi",
    "genel": "🌐 Genel",
}

CATEGORY_FILTER_LABELS = {
    "min_year": "Min Yıl", "max_year": "Max Yıl", "max_km": "Max KM",
    "fuel_type": "Yakıt", "gear_type": "Vites", "color": "Renk",
    "body_type": "Kasa", "min_m2": "Min m²", "max_m2": "Max m²",
    "room_count": "Oda", "max_building_age": "Bina Yaşı", "floor": "Kat",
    "heating": "Isıtma", "furnished": "Eşya", "site": "Site İçi",
    "engine_cc": "Motor cc", "moto_type": "Tip", "brand": "Marka",
    "storage": "Depolama", "ram": "RAM", "condition": "Durum",
    "boat_type": "Tekne Tipi", "min_length": "Min Uzunluk",
    "max_length": "Max Uzunluk", "engine_hp": "Motor HP",
    "machine_type": "Makine Tipi", "max_hours": "Max Saat",
}


async def bot_db_query(sql: str, params: tuple = ()) -> list[dict]:
    try:
        async with aiosqlite.connect(BOT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception:
        return []


@router.get("", response_class=HTMLResponse)
async def admin_panel():
    users = await bot_db_query("""
        SELECT u.user_id, u.username, u.first_name, u.notifications_enabled, u.joined_at,
               COUNT(f.id) as filter_count
        FROM users u
        LEFT JOIN filters f ON f.user_id = u.user_id AND f.active = 1
        GROUP BY u.user_id
        ORDER BY u.joined_at DESC
    """)

    filters = await bot_db_query("""
        SELECT f.*, u.username, u.first_name,
               COUNT(s.id) as seen_count,
               MAX(s.seen_at) as last_seen_at
        FROM filters f
        JOIN users u ON f.user_id = u.user_id
        LEFT JOIN seen_listings s ON s.filter_id = f.id
        WHERE f.active = 1
        GROUP BY f.id
        ORDER BY f.created_at DESC
    """)

    # Kategori istatistikleri
    cat_stats = {}
    for f in filters:
        cat = f.get("category") or "genel"
        cat_stats[cat] = cat_stats.get(cat, 0) + 1

    user_rows = ""
    for u in users:
        notif = '<span class="badge-green">✅ Açık</span>' if u["notifications_enabled"] else '<span class="badge-red">🔕 Kapalı</span>'
        name = f"@{u['username']}" if u["username"] else u["first_name"] or "?"
        user_rows += f"""
        <tr>
            <td><code>{u['user_id']}</code></td>
            <td><strong>{name}</strong></td>
            <td>{u['first_name'] or '-'}</td>
            <td>{notif}</td>
            <td><span class="pill">{u['filter_count']}</span></td>
            <td>{u['joined_at'] or '-'}</td>
        </tr>"""

    filter_rows = ""
    for f in filters:
        owner = f"@{f['username']}" if f["username"] else f["first_name"] or "?"
        keywords = f['keywords'] or "-"
        price_range = "-"
        if f.get("min_price") or f.get("max_price"):
            mn = f"{f['min_price']:,}" if f.get("min_price") else "0"
            mx = f"{f['max_price']:,}" if f.get("max_price") else "∞"
            price_range = f"{mn} – {mx} TL"
        url_short = f['url'][:55] + "..." if len(f['url']) > 55 else f['url']
        cat_key = f.get("category") or "genel"
        cat_label = CATEGORY_LABELS.get(cat_key, "🌐 Genel")

        # Kategori filtrelerini satır içinde göster
        cat_details = ""
        try:
            cat_filters_data = json.loads(f.get("category_filters") or "{}")
            if cat_filters_data:
                items = []
                for k, v in cat_filters_data.items():
                    label = CATEGORY_FILTER_LABELS.get(k, k)
                    items.append(f"<span class='tag'>{label}: {v}</span>")
                cat_details = "<br>" + " ".join(items) if items else ""
        except Exception:
            pass

        filter_rows += f"""
        <tr>
            <td><code>{f['id']}</code></td>
            <td>{owner}</td>
            <td><strong>{f['name']}</strong></td>
            <td>{cat_label}{cat_details}</td>
            <td title="{f['url']}"><a href="{f['url']}" target="_blank">{url_short}</a></td>
            <td>{keywords}</td>
            <td>{price_range}</td>
            <td><span class="pill">{f['seen_count']}</span></td>
            <td>{(f.get('last_seen_at') or '-')[:16]}</td>
            <td>{(f.get('created_at') or '-')[:16]}</td>
        </tr>"""

    # Kategori dağılımı HTML
    cat_chart = ""
    for cat_key, count in sorted(cat_stats.items(), key=lambda x: -x[1]):
        label = CATEGORY_LABELS.get(cat_key, cat_key)
        pct = int(count / len(filters) * 100) if filters else 0
        cat_chart += f"""
        <div class="bar-row">
          <span class="bar-label">{label}</span>
          <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
          <span class="bar-num">{count}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>İlan Takip - Admin Panel</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#333}}
  .header{{background:linear-gradient(135deg,#6C63FF,#3b35c7);color:white;padding:20px 32px}}
  .header h1{{font-size:22px}} .header p{{opacity:.8;font-size:13px;margin-top:4px}}
  .container{{padding:24px 32px;max-width:1500px;margin:0 auto}}
  .stats{{display:flex;gap:16px;margin-bottom:28px;flex-wrap:wrap}}
  .stat-card{{background:white;border-radius:12px;padding:20px 28px;flex:1;min-width:140px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .stat-card .num{{font-size:32px;font-weight:700;color:#6C63FF}}
  .stat-card .label{{font-size:13px;color:#888;margin-top:4px}}
  .row2{{display:flex;gap:20px;margin-bottom:24px;flex-wrap:wrap}}
  .section{{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:24px;overflow:hidden}}
  .section-half{{flex:1;min-width:300px;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden}}
  .section-header{{padding:14px 22px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;gap:10px}}
  .section-header h2{{font-size:15px;font-weight:600}}
  .badge{{background:#6C63FF;color:white;border-radius:20px;padding:2px 10px;font-size:12px}}
  .badge-green{{background:#e6f7ee;color:#27ae60;border-radius:20px;padding:2px 8px;font-size:12px;font-weight:600}}
  .badge-red{{background:#fdecea;color:#e74c3c;border-radius:20px;padding:2px 8px;font-size:12px;font-weight:600}}
  .pill{{background:#f0eeff;color:#6C63FF;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600}}
  .tag{{background:#f5f5f5;color:#555;border-radius:6px;padding:2px 7px;font-size:11px;display:inline-block;margin:1px}}
  .table-wrap{{overflow-x:auto}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{background:#fafafa;padding:9px 14px;text-align:left;font-weight:600;color:#555;border-bottom:1px solid #eee;white-space:nowrap}}
  td{{padding:9px 14px;border-bottom:1px solid #f5f5f5;vertical-align:top}}
  tr:last-child td{{border-bottom:none}} tr:hover td{{background:#fafafe}}
  a{{color:#6C63FF;text-decoration:none}} a:hover{{text-decoration:underline}}
  code{{background:#f0eeff;color:#6C63FF;padding:1px 6px;border-radius:4px;font-size:12px}}
  .empty{{padding:40px;text-align:center;color:#aaa}}
  .refresh{{margin-left:auto;background:#6C63FF;color:white;border:none;border-radius:8px;padding:7px 14px;cursor:pointer;font-size:13px}}
  .refresh:hover{{background:#5a52e0}}
  .bar-row{{display:flex;align-items:center;gap:10px;padding:7px 0}}
  .bar-label{{width:130px;font-size:13px;flex-shrink:0}}
  .bar-track{{flex:1;height:10px;background:#eee;border-radius:10px;overflow:hidden}}
  .bar-fill{{height:100%;background:linear-gradient(90deg,#6C63FF,#a89cff);border-radius:10px;transition:width .5s}}
  .bar-num{{width:30px;text-align:right;font-size:13px;font-weight:600;color:#6C63FF}}
  .chart-body{{padding:16px 22px}}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 İlan Takip — Admin Panel</h1>
  <p>Telegram Bot Kullanıcıları, Filtreleri ve İstatistikleri</p>
</div>
<div class="container">

  <div class="stats">
    <div class="stat-card"><div class="num">{len(users)}</div><div class="label">Toplam Kullanıcı</div></div>
    <div class="stat-card"><div class="num">{sum(1 for u in users if u['notifications_enabled'])}</div><div class="label">Bildirim Açık</div></div>
    <div class="stat-card"><div class="num">{len(filters)}</div><div class="label">Aktif Filtre</div></div>
    <div class="stat-card"><div class="num">{sum(f['seen_count'] for f in filters):,}</div><div class="label">Taranan İlan</div></div>
  </div>

  <div class="row2">
    <div class="section-half">
      <div class="section-header"><h2>📊 Kategori Dağılımı</h2><button class="refresh" onclick="location.reload()">↻ Yenile</button></div>
      <div class="chart-body">
        {"".join([f'<div class="bar-row"><span class="bar-label">{CATEGORY_LABELS.get(k,"?")}</span><div class="bar-track"><div class="bar-fill" style="width:{int(v/len(filters)*100) if filters else 0}%"></div></div><span class="bar-num">{v}</span></div>' for k,v in sorted(cat_stats.items(), key=lambda x:-x[1])]) or '<div class="empty">Veri yok</div>'}
      </div>
    </div>
    <div class="section-half">
      <div class="section-header"><h2>👥 Kullanıcılar</h2><span class="badge">{len(users)}</span></div>
      <div class="table-wrap">
        {"<table><thead><tr><th>ID</th><th>Kullanıcı</th><th>İsim</th><th>Bildirim</th><th>Filtre</th><th>Kayıt</th></tr></thead><tbody>" + user_rows + "</tbody></table>" if users else '<div class="empty">Henüz kullanıcı yok</div>'}
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header"><h2>🔍 Aktif Filtreler</h2><span class="badge">{len(filters)}</span></div>
    <div class="table-wrap">
      {"<table><thead><tr><th>ID</th><th>Kullanıcı</th><th>Filtre Adı</th><th>Kategori & Detaylar</th><th>URL</th><th>Anahtar Kelimeler</th><th>Fiyat</th><th>Taranan</th><th>Son Tarama</th><th>Oluşturulma</th></tr></thead><tbody>" + filter_rows + "</tbody></table>" if filters else '<div class="empty">Henüz aktif filtre yok</div>'}
    </div>
  </div>

</div>
</body>
</html>"""
    return HTMLResponse(content=html)

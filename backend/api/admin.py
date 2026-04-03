import os
import aiosqlite
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["admin"])

# Telegram botunun veritabanı — her zaman sabit mutlak yol
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOT_DB_PATH = os.path.join(BASE_DIR, "data", "ilantakip.db")


async def bot_db_query(sql: str, params: tuple = ()) -> list[dict]:
    try:
        async with aiosqlite.connect(BOT_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        return []


@router.get("", response_class=HTMLResponse)
async def admin_panel():
    """Admin paneli HTML arayüzü."""
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
               COUNT(s.id) as seen_count
        FROM filters f
        JOIN users u ON f.user_id = u.user_id
        LEFT JOIN seen_listings s ON s.filter_id = f.id
        WHERE f.active = 1
        GROUP BY f.id
        ORDER BY f.created_at DESC
    """)

    user_rows = ""
    for u in users:
        notif = "✅" if u["notifications_enabled"] else "🔕"
        name = f"@{u['username']}" if u["username"] else u["first_name"] or "?"
        user_rows += f"""
        <tr>
            <td>{u['user_id']}</td>
            <td>{name}</td>
            <td>{u['first_name'] or '-'}</td>
            <td>{notif}</td>
            <td>{u['filter_count']}</td>
            <td>{u['joined_at'] or '-'}</td>
        </tr>"""

    filter_rows = ""
    for f in filters:
        name = f"@{f['username']}" if f["username"] else f["first_name"] or "?"
        keywords = f['keywords'] or "-"
        price_range = "-"
        if f.get("min_price") or f.get("max_price"):
            mn = f"{f['min_price']:,}" if f.get("min_price") else "0"
            mx = f"{f['max_price']:,}" if f.get("max_price") else "∞"
            price_range = f"{mn} - {mx} TL"
        url_short = f['url'][:60] + "..." if len(f['url']) > 60 else f['url']
        filter_rows += f"""
        <tr>
            <td>{f['id']}</td>
            <td>{name}</td>
            <td><strong>{f['name']}</strong></td>
            <td title="{f['url']}"><a href="{f['url']}" target="_blank">{url_short}</a></td>
            <td>{keywords}</td>
            <td>{price_range}</td>
            <td>{f['seen_count']}</td>
            <td>{f['created_at'] or '-'}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>İlan Takip - Admin Panel</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; }}
  .header {{ background: linear-gradient(135deg, #6C63FF, #3b35c7); color: white; padding: 20px 32px; }}
  .header h1 {{ font-size: 22px; }}
  .header p {{ opacity: 0.8; font-size: 13px; margin-top: 4px; }}
  .container {{ padding: 24px 32px; max-width: 1400px; margin: 0 auto; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .stat-card {{ background: white; border-radius: 12px; padding: 20px 28px; flex: 1; min-width: 140px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .stat-card .num {{ font-size: 32px; font-weight: 700; color: #6C63FF; }}
  .stat-card .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .section {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
              margin-bottom: 24px; overflow: hidden; }}
  .section-header {{ padding: 16px 24px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 10px; }}
  .section-header h2 {{ font-size: 16px; font-weight: 600; }}
  .section-header .badge {{ background: #6C63FF; color: white; border-radius: 20px;
                             padding: 2px 10px; font-size: 12px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #fafafa; padding: 10px 16px; text-align: left; font-weight: 600;
        color: #555; border-bottom: 1px solid #eee; white-space: nowrap; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #f5f5f5; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafafe; }}
  a {{ color: #6C63FF; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .empty {{ padding: 40px; text-align: center; color: #aaa; }}
  .refresh {{ float: right; background: #6C63FF; color: white; border: none; border-radius: 8px;
              padding: 8px 16px; cursor: pointer; font-size: 13px; }}
  .refresh:hover {{ background: #5a52e0; }}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 İlan Takip - Admin Panel</h1>
  <p>Telegram Bot Kullanıcıları ve Filtreleri</p>
</div>
<div class="container">
  <div class="stats">
    <div class="stat-card">
      <div class="num">{len(users)}</div>
      <div class="label">Toplam Kullanıcı</div>
    </div>
    <div class="stat-card">
      <div class="num">{sum(1 for u in users if u['notifications_enabled'])}</div>
      <div class="label">Aktif Bildirim</div>
    </div>
    <div class="stat-card">
      <div class="num">{len(filters)}</div>
      <div class="label">Aktif Filtre</div>
    </div>
    <div class="stat-card">
      <div class="num">{sum(f['seen_count'] for f in filters)}</div>
      <div class="label">Taranan İlan</div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2>👥 Kullanıcılar</h2>
      <span class="badge">{len(users)}</span>
      <button class="refresh" onclick="location.reload()">↻ Yenile</button>
    </div>
    <div class="table-wrap">
      {"<table><thead><tr><th>User ID</th><th>Kullanıcı Adı</th><th>İsim</th><th>Bildirim</th><th>Filtre Sayısı</th><th>Kayıt Tarihi</th></tr></thead><tbody>" + user_rows + "</tbody></table>" if users else '<div class="empty">Henüz kullanıcı yok</div>'}
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2>🔍 Aktif Filtreler</h2>
      <span class="badge">{len(filters)}</span>
    </div>
    <div class="table-wrap">
      {"<table><thead><tr><th>ID</th><th>Kullanıcı</th><th>Filtre Adı</th><th>URL</th><th>Anahtar Kelimeler</th><th>Fiyat Aralığı</th><th>Taranan İlan</th><th>Oluşturulma</th></tr></thead><tbody>" + filter_rows + "</tbody></table>" if filters else '<div class="empty">Henüz aktif filtre yok</div>'}
    </div>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)

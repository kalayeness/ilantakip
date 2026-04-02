# İlan Takip Botu

Sahibinden.com ilanlarını Telegram üzerinden takip eden bot. Her 5 dakikada bir belirlediğin filtrelere uyan yeni ilanları bildirir.

## Kurulum

### 1. Bot Token Al
1. Telegram'da [@BotFather](https://t.me/botfather)'a mesaj at
2. `/newbot` komutu ile yeni bot oluştur
3. Token'ı kopyala

### 2. Ortam Değişkenlerini Ayarla
```bash
cp .env.example .env
# .env dosyasını düzenle ve TELEGRAM_BOT_TOKEN'ı ayarla
```

### 3a. Docker ile Çalıştır (Önerilen)
```bash
docker-compose up -d
```

### 3b. Manuel Kurulum
```bash
pip install -r requirements.txt
python bot.py
```

## Kullanım

Bot komutları:

| Komut | Açıklama |
|-------|----------|
| `/start` | Botu başlat |
| `/filtre_ekle` | Yeni sahibinden.com filtresi ekle |
| `/filtrelerim` | Aktif filtrelerini listele |
| `/filtre_sil` | Filtre sil |
| `/simdi_kontrol` | Hemen kontrol et |
| `/bildirimleri_durdur` | Bildirimleri durdur |
| `/bildirimleri_baslat` | Bildirimleri tekrar başlat |
| `/yardim` | Yardım mesajı |

## Nasıl Filtre Eklenir?

1. [sahibinden.com](https://www.sahibinden.com)'a git
2. İstediğin filtreleri uygula (şehir, fiyat, m², oda sayısı vb.)
3. Arama sonuçları sayfasının URL'sini kopyala
4. `/filtre_ekle` komutunu kullan ve URL'yi yapıştır

## Önemli Notlar

- Sahibinden.com zaman zaman bot erişimini engelleyebilir. Bu durumda kontrol atlanır.
- Çok sık istek atmamak için kontrol aralığı minimum 5 dakika önerilir.
- Veriler `data/ilantakip.db` SQLite dosyasında saklanır.

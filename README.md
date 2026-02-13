# Akıllı Pano Sistemi

Okullar için geliştirilmiş, Telegram entegrasyonlu dijital pano sistemi.

## 📁 Proje Yapısı

```
akilli_pano/
├── config.py              # Merkezi yapılandırma (Token, Pathler)
├── run_web.py             # Web sunucusunu başlatan script
├── run_bot.py             # Telegram botunu başlatan script
├── data/
│   └── data.json          # Ders programı ve nöbetçi verileri
└── src/
    ├── bot/               # Bot kodları
    └── web/               # Web/Flask kodları (HTML/CSS/JS dahil)
```

## 🚀 Kurulum

1. Gereklilikleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

2. Yapılandırma:
   `config.py` dosyasını açın ve `BOT_TOKEN` ile `ADMIN_IDS` alanlarını düzenleyin. Alternatif olarak `.env` dosyası kullanabilirsiniz.

## 🖥️ Çalıştırma

Sistemi çalıştırmak için iki ayrı terminalde şu komutları girin:

**Terminal 1 (Web Arayüzü):**
```bash
python run_web.py
```

**Terminal 2 (Telegram Botu):**
```bash
python run_bot.py
```

## 📝 Veri Güncelleme
`data/data.json` dosyasını düzenleyerek ders programını ve nöbetçileri güncelleyebilirsiniz.

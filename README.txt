# Dijital Okul Panosu Kurulum ve Kullanım Kılavuzu

Proje dosyaları başarıyla oluşturuldu. Çalıştırmak için aşağıdaki adımları izleyin:

## 1. Kurulum

Öncelikle gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

## 2. Telegram Bot Ayarları

`bot.py` dosyasını açın ve aşağıdaki satırları kendi bilgilerinizle güncelleyin:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # BotFather'dan aldığınız token
ADMIN_IDS = [123456789]            # Kendi Telegram ID'niz (userinfobot ile öğrenebilirsiniz)
```

## 3. Çalıştırma

İki ayrı terminal penceresi açın.

**Terminal 1 (Web Sunucusu):**
```bash
python app.py
```
Tarayıcınızda `http://localhost:5000` adresine gidin ve F11 ile tam ekran yapın.

**Terminal 2 (Telegram Botu):**
```bash
python bot.py
```
Bot çalışırken yetkili ID'lerden gönderilen fotoğraf ve videolar `static/slideshow` klasörüne iner ve panoda otomatik gösterilir.

## 4. Veri Güncelleme

Ders programı, nöbetçi öğretmenler ve mesajları güncellemek için `data.json` dosyasını düzenleyebilirsiniz. Değişiklikler sayfayı yenilemeden 30 saniye içinde yansır.

import os
import logging
import uuid
import sys
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Import config from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Data Helpers ---

def load_data():
    """Load data.json"""
    if not os.path.exists(config.DATA_FILE):
        return {}
    try:
        with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading data.json: {e}")
        return {}

def save_data(data):
    """Save data.json"""
    try:
        os.makedirs(os.path.dirname(config.DATA_FILE), exist_ok=True)
        with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving data.json: {e}")
        return False

def load_allowed_users():
    if not os.path.exists(config.ALLOWED_USERS_FILE):
        return []
    try:
        with open(config.ALLOWED_USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading allowed users: {e}")
        return []

def save_allowed_user(user_id):
    users = load_allowed_users()
    if user_id not in users:
        users.append(user_id)
        with open(config.ALLOWED_USERS_FILE, 'w') as f:
            json.dump(users, f)

def is_authorized(user_id):
    if user_id in config.ADMIN_IDS:
        return True
    allowed_users = load_allowed_users()
    return user_id in allowed_users

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

# --- Menu ---

MENU_TEXT_AUTHORIZED = (
    "📋 **Kullanılabilir Komutlar:**\n\n"
    "📸 **Medya Yükleme** — Fotoğraf veya video gönderin\n"
    "✏️ `/mesaj <metin>` — Kayan yazıyı değiştir\n"
    "📝 `/mesajekle <metin>` — Kayan yazıya yeni satır ekle\n"
    "📖 `/mesajlar` — Mevcut kayan yazıları göster\n"
    "🏫 `/okul <isim>` — Okul adını değiştir\n"
    "⏳ `/gerisayim <etiket> | <tarih>` — Geri sayımı ayarla\n"
    "📊 `/durum` — Pano durumunu göster\n"
    "🆔 `/id` — Telegram ID'nizi göster\n"
)

MENU_TEXT_UNAUTHORIZED = (
    "📋 **Kullanılabilir Komutlar:**\n\n"
    "🔑 `/giris <şifre>` — Öğretmen girişi\n"
    "🆔 `/id` — Telegram ID'nizi göster\n"
    "\n⚠️ Diğer komutları kullanmak için önce giriş yapmalısınız."
)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    if is_authorized(user_id):
        role = "👑 Admin" if is_admin(user_id) else "✅ Yetkili Kullanıcı"
        text = (
            f"Merhaba **{first_name}**! 👋\n\n"
            f"Rolünüz: {role}\n\n"
            f"{MENU_TEXT_AUTHORIZED}"
        )
    else:
        text = (
            f"Merhaba **{first_name}**! 👋\n\n"
            "Bu bot okul panosunu yönetmek için kullanılır.\n\n"
            f"{MENU_TEXT_UNAUTHORIZED}"
        )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode='Markdown'
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Zaten yetkiniz var.")
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Kullanım: `/giris <şifre>`\nÖrnek: `/giris okulpanosu`",
            parse_mode='Markdown'
        )
        return

    password = context.args[0]
    
    current_password = config.BOT_ACCESS_CODE
    try:
        if os.path.exists(config.DATA_FILE):
            with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_password = data.get('bot_access_code', config.BOT_ACCESS_CODE)
    except Exception as e:
        logging.error(f"Error reading data.json for password: {e}")

    if password == current_password:
        save_allowed_user(user_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="✅ Giriş başarılı! Artık tüm komutları kullanabilirsiniz.\n\nKomutları görmek için herhangi bir mesaj yazın."
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Hatalı şifre.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"🆔 Sizin ID'niz: `{update.effective_user.id}`",
        parse_mode='Markdown'
    )

# --- Kayan Yazı (Marquee) Commands ---

async def mesaj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Replace all marquee messages with a single new one"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok. Önce `/giris <şifre>` ile giriş yapın.", parse_mode='Markdown')
        return
    
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Kullanım: `/mesaj <yeni kayan yazı metni>`\nÖrnek: `/mesaj Yarın okul tatildir.`",
            parse_mode='Markdown'
        )
        return
    
    new_message = ' '.join(context.args)
    data = load_data()
    data['messages'] = [new_message]
    
    if save_data(data):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Kayan yazı güncellendi:\n\n📢 _{new_message}_",
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Kaydetme hatası oluştu.")

async def mesaj_ekle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new marquee message to existing ones"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.", parse_mode='Markdown')
        return
    
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Kullanım: `/mesajekle <ek kayan yazı metni>`",
            parse_mode='Markdown'
        )
        return
    
    new_message = ' '.join(context.args)
    data = load_data()
    if 'messages' not in data:
        data['messages'] = []
    data['messages'].append(new_message)
    
    if save_data(data):
        count = len(data['messages'])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Kayan yazıya eklendi (toplam {count} mesaj):\n\n📢 _{new_message}_",
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Kaydetme hatası.")

async def mesajlar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all current marquee messages"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.")
        return
    
    data = load_data()
    messages = data.get('messages', [])
    
    if not messages:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📭 Kayan yazı boş.")
        return
    
    text = "📝 **Mevcut Kayan Yazılar:**\n\n"
    for i, msg in enumerate(messages, 1):
        text += f"  {i}. _{msg}_\n"
    text += f"\nSilmek için: `/mesajsil <numara>`"
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode='Markdown'
    )

async def mesaj_sil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a specific marquee message by index"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.")
        return
    
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Kullanım: `/mesajsil <numara>`\nÖrnek: `/mesajsil 2`",
            parse_mode='Markdown'
        )
        return
    
    try:
        index = int(context.args[0]) - 1
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Geçerli bir numara girin.")
        return
    
    data = load_data()
    messages = data.get('messages', [])
    
    if index < 0 or index >= len(messages):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Geçersiz numara. 1-{len(messages)} arası seçin.")
        return
    
    removed = messages.pop(index)
    data['messages'] = messages
    
    if save_data(data):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🗑️ Silindi: _{removed}_",
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Kaydetme hatası.")

# --- School & Countdown Commands ---

async def okul_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change school name"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.")
        return
    
    if not context.args:
        data = load_data()
        current = data.get('school_name', 'Belirtilmemiş')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🏫 Mevcut okul adı: **{current}**\n\nDeğiştirmek için: `/okul <yeni isim>`",
            parse_mode='Markdown'
        )
        return
    
    new_name = ' '.join(context.args)
    data = load_data()
    data['school_name'] = new_name
    
    if save_data(data):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Okul adı güncellendi: **{new_name}**",
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Kaydetme hatası.")

async def gerisayim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set countdown label and date"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.")
        return
    
    if not context.args:
        data = load_data()
        cd = data.get('countdown', {})
        label = cd.get('label', '-')
        target = cd.get('target_date', '-')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⏳ Mevcut geri sayım:\n🏷️ Etiket: **{label}**\n📅 Tarih: **{target}**\n\n"
                 "Değiştirmek için:\n`/gerisayim Yaz Tatili | 2026-06-13T09:00`",
            parse_mode='Markdown'
        )
        return
    
    text = ' '.join(context.args)
    
    if '|' in text:
        parts = text.split('|', 1)
        label = parts[0].strip()
        target_date = parts[1].strip()
    else:
        label = text
        target_date = ""
    
    data = load_data()
    data['countdown'] = {
        'label': label,
        'target_date': target_date
    }
    
    if save_data(data):
        msg = f"✅ Geri sayım güncellendi:\n🏷️ {label}"
        if target_date:
            msg += f"\n📅 {target_date}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Kaydetme hatası.")

# --- Status Command ---

async def durum_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current panel status"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.")
        return
    
    data = load_data()
    
    school = data.get('school_name', '-')
    messages = data.get('messages', [])
    msg_count = len(messages)
    msg_preview = messages[0][:50] + '...' if messages and len(messages[0]) > 50 else (messages[0] if messages else '-')
    
    # Count slides
    slide_count = 0
    if os.path.exists(config.SLIDESHOW_DIR):
        valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm']
        slide_count = sum(1 for f in os.listdir(config.SLIDESHOW_DIR) if os.path.splitext(f)[1].lower() in valid_exts)
    
    cd = data.get('countdown', {})
    cd_label = cd.get('label', '-')
    cd_date = cd.get('target_date', '-') or '-'
    
    birthday_count = len(data.get('birthdays', []))
    
    text = (
        "📊 **Pano Durumu**\n\n"
        f"🏫 Okul: {school}\n"
        f"📢 Kayan yazı: {msg_count} mesaj\n"
        f"   └ _{msg_preview}_\n"
        f"🖼️ Slayt: {slide_count} dosya\n"
        f"🎂 Doğum günü: {birthday_count} kayıt\n"
        f"⏳ Geri sayım: {cd_label} ({cd_date})\n"
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode='Markdown'
    )

# --- Media Upload ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Yetkiniz yok. Önce `/giris <şifre>` ile giriş yapın.",
            parse_mode='Markdown'
        )
        return

    file = None
    file_name = f"{uuid.uuid4()}"
    
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_name += ".jpg"
    elif update.message.video:
        file = await update.message.video.get_file()
        file_name += ".mp4"
    elif update.message.document:
        mime = update.message.document.mime_type
        if mime and mime.startswith('image/'):
            file_name += ".jpg"
        elif mime and mime.startswith('video/'):
            file_name += ".mp4"
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Sadece fotoğraf veya video kabul edilir.")
            return
        file = await update.message.document.get_file()
    else:
        return

    file_path = os.path.join(config.SLIDESHOW_DIR, file_name)
    await file.download_to_drive(file_path)
    
    # Count total slides
    valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm']
    slide_count = sum(1 for f in os.listdir(config.SLIDESHOW_DIR) if os.path.splitext(f)[1].lower() in valid_exts)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Panoya eklendi! (Toplam {slide_count} slayt)"
    )

# --- Text Handler (Show Menu) ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_authorized(user_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MENU_TEXT_AUTHORIZED,
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MENU_TEXT_UNAUTHORIZED,
            parse_mode='Markdown'
        )

# --- Main ---

def main():
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Lütfen config.py veya .env dosyasındaki BOT_TOKEN ve ADMIN_IDS alanlarını düzenleyin.")
        return
        
    builder = ApplicationBuilder().token(config.BOT_TOKEN)
    
    # Custom Network Configuration
    if config.BOT_API_URL:
        builder.base_url(config.BOT_API_URL)
        print(f"Özel API URL kullanılıyor: {config.BOT_API_URL}")

    # SSL Verification Handling
    if not config.BOT_SSL_VERIFY:
        try:
            from telegram.request import HTTPXRequest
            
            class InsecureHTTPXRequest(HTTPXRequest):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                
                def _create_client(self, **kwargs):
                    kwargs["verify"] = False
                    return super()._create_client(**kwargs)

            request_instance = InsecureHTTPXRequest()
            builder.request(request_instance)
            print("⚠️ UYARI: SSL Sertifika doğrulaması devre dışı bırakıldı (Okul Ağı Modu).")
        except ImportError:
            print("HATA: HTTPXRequest import edilemedi. SSL ayarı yapılamadı.")

    application = builder.build()
    
    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('giris', login_command))
    application.add_handler(CommandHandler('id', id_command))
    application.add_handler(CommandHandler('mesaj', mesaj_command))
    application.add_handler(CommandHandler('mesajekle', mesaj_ekle_command))
    application.add_handler(CommandHandler('mesajlar', mesajlar_command))
    application.add_handler(CommandHandler('mesajsil', mesaj_sil_command))
    application.add_handler(CommandHandler('okul', okul_command))
    application.add_handler(CommandHandler('gerisayim', gerisayim_command))
    application.add_handler(CommandHandler('durum', durum_command))
    
    # Media handler (photos, videos, documents)
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO, 
        handle_document
    ))
    
    # Text handler (show menu for any non-command text)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print(f"Bot çalışıyor (Admin IDs: {config.ADMIN_IDS})...")
    application.run_polling()

if __name__ == '__main__':
    main()

import os
import logging
import uuid
import sys
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Import config from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_authorized(user_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Merhaba! Yetkili kullanıcı olarak tanındınız. Fotoğraf veya video gönderirseniz slayta eklerim."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Merhaba! Bu bot okul panosunu yönetir.\n"
                 "Fotoğraf gönderebilmek için yetkiniz yok.\n"
                 "Eğer öğretmenseniz, `/giris <sifre>` komutu ile giriş yapabilirsiniz.",
            parse_mode='Markdown'
        )

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

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Zaten yetkiniz var.")
        return

    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Lütfen şifreyi girin: `/giris <sifre>`", parse_mode='Markdown')
        return

    password = context.args[0]
    
    if password == config.BOT_ACCESS_CODE:
        save_allowed_user(user_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Giriş başarılı! Artık fotoğraf ve video gönderebilirsiniz.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hatalı şifre.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Sizin ID'niz: `{update.effective_user.id}`", parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check authorization
    # Check authorization
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Yetkiniz yok.")
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
        # Verify mime type if needed, for now accept common images/videos
        mime = update.message.document.mime_type
        if mime and mime.startswith('image/'):
            file_name += ".jpg" # Simplification
        elif mime and mime.startswith('video/'):
            file_name += ".mp4"
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Sadece fotoğraf veya video kabul edilir.")
            return
        file = await update.message.document.get_file()
    else:
        return

    file_path = os.path.join(config.SLIDESHOW_DIR, file_name)
    await file.download_to_drive(file_path)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Dosya başarıyla yüklendi ve panoya eklendi! ({file_name})"
    )

def main():
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Lütfen config.py veya .env dosyasındaki BOT_TOKEN ve ADMIN_IDS alanlarını düzenleyin.")
        return
        
    # Configure Application Builder
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
                
                # Override to disable SSL check
                def _create_client(self, **kwargs):
                    # Inject verify=False to the httpx client
                    kwargs["verify"] = False
                    return super()._create_client(**kwargs)

            request_instance = InsecureHTTPXRequest()
            builder.request(request_instance)
            print("⚠️ UYARI: SSL Sertifika doğrulaması devre dışı bırakıldı (Okul Ağı Modu).")
        except ImportError:
            print("HATA: HTTPXRequest import edilemedi. SSL ayarı yapılamadı.")

    application = builder.build()
    
    start_handler = CommandHandler('start', start)
    # Handle photos and videos
    media_handler = MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO, handle_document)
    
    login_handler = CommandHandler('giris', login_command)
    id_handler = CommandHandler('id', id_command)

    application.add_handler(start_handler)
    application.add_handler(login_handler)
    application.add_handler(id_handler)
    application.add_handler(media_handler)
    
    print(f"Bot çalışıyor (Admin IDs: {config.ADMIN_IDS})...")
    application.run_polling()

if __name__ == '__main__':
    main()

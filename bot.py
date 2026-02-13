import os
import logging
import uuid
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # User must replace this
ADMIN_IDS = [123456789] # User must replace this with their Telegram ID
DOWNLOAD_DIR = os.path.join('static', 'slideshow')

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Merhaba! Ben Okul Panosu Botuyum. Bana fotoğraf veya video gönderirsen slayta eklerim."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
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
        if mime.startswith('image/'):
            file_name += ".jpg" # Simplification
        elif mime.startswith('video/'):
            file_name += ".mp4"
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Sadece fotoğraf veya video kabul edilir.")
            return
        file = await update.message.document.get_file()
    else:
        return

    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    await file.download_to_drive(file_path)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Dosya başarıyla yüklendi ve panoya eklendi! ({file_name})"
    )

if __name__ == '__main__':
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Lütfen bot.py dosyasındaki BOT_TOKEN ve ADMIN_IDS alanlarını düzenleyin.")
        exit()
        
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    # Handle photos and videos
    media_handler = MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO, handle_document)
    
    application.add_handler(start_handler)
    application.add_handler(media_handler)
    
    print("Bot çalışıyor...")
    application.run_polling()

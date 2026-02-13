import os
import logging
import uuid
import sys
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Merhaba! Ben Okul Panosu Botuyum. Bana fotoğraf veya video gönderirsen slayta eklerim."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check authorization
    if user_id not in config.ADMIN_IDS:
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
        
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    # Handle photos and videos
    media_handler = MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO, handle_document)
    
    application.add_handler(start_handler)
    application.add_handler(media_handler)
    
    print(f"Bot çalışıyor (Admin IDs: {config.ADMIN_IDS})...")
    application.run_polling()

if __name__ == '__main__':
    main()

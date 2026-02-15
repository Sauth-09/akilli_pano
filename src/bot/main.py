import os
import logging
import uuid
import sys
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

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

# --- State Management ---
user_states = {}

# State Constants
STATE_NONE = 0
STATE_WAITING_MARQUEE = 1
STATE_WAITING_MARQUEE_ADD = 2
STATE_WAITING_QUOTE = 3
STATE_WAITING_QUOTE_ADD = 4
STATE_WAITING_RIDDLE = 5

# --- Keyboards ---

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📜 Kayan Yazıyı Değiştir"), KeyboardButton("➕ Kayan Yazıya Ekle")],
        [KeyboardButton("📖 Kayan Yazıyı Göster"), KeyboardButton("❓ Bilmece/Soru Yükle")],
        [KeyboardButton("📢 Günün Sözünü Değiştir"), KeyboardButton("➕ Günün Sözü Ekle")],
        [KeyboardButton("📖 Günün Sözünü Göster"), KeyboardButton("📊 Durum")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    if is_authorized(user_id):
        role = "👑 Admin" if is_admin(user_id) else "✅ Yetkili Kullanıcı"
        text = (
            f"Merhaba **{first_name}**! 👋\n\n"
            f"Rolünüz: {role}\n"
            "Aşağıdaki menüden işlem yapabilirsiniz."
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    else:
        text = (
            f"Merhaba **{first_name}**! 👋\n\n"
            "Bu bot okul panosunu yönetmek için kullanılır.\n"
            "Lütfen giriş yapın: `/giris <şifre>`"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode='Markdown'
        )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_authorized(user_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="✅ Zaten yetkiniz var.",
            reply_markup=get_main_keyboard()
        )
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
            text="✅ Giriş başarılı! Artık butonları kullanabilirsiniz.",
            reply_markup=get_main_keyboard()
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Hatalı şifre.")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"🆔 Sizin ID'niz: `{update.effective_user.id}`",
        parse_mode='Markdown'
    )

# --- Standard Commands (Still avail via slash) ---

async def mesaj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Replace all marquee messages with a single new one"""
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Kullanım: `/mesaj <metin>`")
        return
    
    new_message = ' '.join(context.args)
    data = load_data()
    data['messages'] = [new_message]
    if save_data(data):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Kayan yazı güncellendi:\n📢 _{new_message}_", parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Hata.")

async def mesaj_ekle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    if not context.args: return
    new_message = ' '.join(context.args)
    data = load_data()
    if 'messages' not in data: data['messages'] = []
    data['messages'].append(new_message)
    if save_data(data):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Eklendi. Toplam: {len(data['messages'])}")

async def mesajlar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    data = load_data()
    messages = data.get('messages', [])
    if not messages:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📭 Mesaj yok.")
        return
    text = "📝 **Mesajlar:**\n" + "\n".join([f"{i+1}. {m}" for i, m in enumerate(messages)])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='Markdown')

async def mesaj_sil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Keep functionality for manual slash command users
    pass 

async def soz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    if not context.args: return
    new_quote = ' '.join(context.args)
    data = load_data()
    data['quotes'] = [new_quote]
    save_data(data)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Günün sözü: {new_quote}")

async def sozekle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    if not context.args: return
    new_quote = ' '.join(context.args)
    data = load_data()
    if 'quotes' not in data: data['quotes'] = []
    data['quotes'].append(new_quote)
    save_data(data)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Söz eklendi. Toplam: {len(data['quotes'])}")

async def sozler_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    data = load_data()
    quotes = data.get('quotes', [])
    text = "📢 **Sözler:**\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(quotes)]) if quotes else "📭 Söz yok."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='Markdown')

async def sozsil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def durum_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id): return
    data = load_data()
    text = f"🏫 Okul: {data.get('school_name', '-')}\n📢 Kayan Yazı: {len(data.get('messages', []))}\n💬 Sözler: {len(data.get('quotes', []))}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

# --- Media Upload ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Yetkiniz yok.")
        return
    
    current_state = user_states.get(user_id, STATE_NONE)
    target_dir = config.SLIDESHOW_DIR
    success_msg = "✅ Slayt eklendi!"
    
    if current_state == STATE_WAITING_RIDDLE:
        target_dir = config.RIDDLES_DIR
        success_msg = "✅ Bilmece/Soru eklendi! (Başka gönderebilirsiniz)"
        if not os.path.exists(config.RIDDLES_DIR):
            os.makedirs(config.RIDDLES_DIR, exist_ok=True)
    
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
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Sadece fotoğraf/video.")
            return
        file = await update.message.document.get_file()
    else:
        return

    file_path = os.path.join(target_dir, file_name)
    await file.download_to_drive(file_path)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=success_msg)

# --- Text Handler (Interactive State Machine) ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not is_authorized(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Önce giriş yapın: `/giris <şifre>`")
        return

    # Check Cancel
    if text.lower() == 'iptal':
        user_states[user_id] = STATE_NONE
        await context.bot.send_message(chat_id=update.effective_chat.id, text="🚫 İşlem iptal edildi.", reply_markup=get_main_keyboard())
        return

    # Check Current State
    current_state = user_states.get(user_id, STATE_NONE)

    if current_state == STATE_WAITING_MARQUEE:
        # Process New Marquee Message
        data = load_data()
        data['messages'] = [text]
        if save_data(data):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Kayan yazı değiştirildi:\n📢 {text}", reply_markup=get_main_keyboard())
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Hata oluştu.", reply_markup=get_main_keyboard())
        user_states[user_id] = STATE_NONE
        return

    elif current_state == STATE_WAITING_MARQUEE_ADD:
        data = load_data()
        if 'messages' not in data: data['messages'] = []
        data['messages'].append(text)
        if save_data(data):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Kayan yazıya eklendi.\n📢 {text}", reply_markup=get_main_keyboard())
        user_states[user_id] = STATE_NONE
        return

    elif current_state == STATE_WAITING_QUOTE:
        data = load_data()
        data['quotes'] = [text]
        save_data(data)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Günün sözü değiştirildi:\n💬 {text}", reply_markup=get_main_keyboard())
        user_states[user_id] = STATE_NONE
        return

    elif current_state == STATE_WAITING_QUOTE_ADD:
        data = load_data()
        if 'quotes' not in data: data['quotes'] = []
        data['quotes'].append(text)
        save_data(data)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Söz eklendi:\n💬 {text}", reply_markup=get_main_keyboard())
        user_states[user_id] = STATE_NONE
        return

    # Handle Helper Buttons (Commands)
    if text == "📜 Kayan Yazıyı Değiştir":
        user_states[user_id] = STATE_WAITING_MARQUEE
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✏️ Lütfen yeni kayan yazıyı gönderin:\n(İptal için 'iptal' yazın)")
        return
    
    elif text == "➕ Kayan Yazıya Ekle":
        user_states[user_id] = STATE_WAITING_MARQUEE_ADD
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📝 Lütfen eklenecek yazıyı gönderin:\n(İptal için 'iptal' yazın)")
        return

    elif text == "📢 Günün Sözünü Değiştir":
        user_states[user_id] = STATE_WAITING_QUOTE
        await context.bot.send_message(chat_id=update.effective_chat.id, text="💬 Lütfen yeni günün sözünü gönderin:\n(İptal için 'iptal' yazın)")
        return
    
    elif text == "➕ Günün Sözü Ekle":
        user_states[user_id] = STATE_WAITING_QUOTE_ADD
        await context.bot.send_message(chat_id=update.effective_chat.id, text="➕ Lütfen eklenecek sözü gönderin:\n(İptal için 'iptal' yazın)")
        return
    
    elif text == "📖 Kayan Yazıyı Göster":
        await mesajlar_command(update, context)
        return

    elif text == "📖 Günün Sözünü Göster":
        await sozler_command(update, context)
        return

    elif text == "📊 Durum":
        await durum_command(update, context)
        return
    
    elif text == "🆔 Telegram ID'niz":
        await id_command(update, context)
        return

    elif text == "❓ Bilmece/Soru Yükle":
        user_states[user_id] = STATE_WAITING_RIDDLE
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📸 Lütfen bilmece/soru fotoğrafını veya videosunu gönderin:\n(İptal için 'iptal' yazın)")
        return

    # Unknown Text
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="❓ Menüden bir işlem seçin veya komut gönderin.",
        reply_markup=get_main_keyboard()
    )


# --- Post Init (Command Menu) ---

async def post_init(application):
    commands = [
        ("giris", "Giriş yap"),
        ("id", "Telegram ID'nizi göster")
    ]
    await application.bot.set_my_commands(commands)

# --- Main ---

def main():
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Lütfen config.py veya .env dosyasındaki BOT_TOKEN ve ADMIN_IDS alanlarını düzenleyin.")
        return
        
    builder = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init)
    
    # Custom Network Configuration
    if config.BOT_API_URL:
        builder.base_url(config.BOT_API_URL)

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
            builder.request(InsecureHTTPXRequest())
        except ImportError:
            pass

    application = builder.build()
    
    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('giris', login_command))
    application.add_handler(CommandHandler('id', id_command))
    application.add_handler(CommandHandler('mesaj', mesaj_command))
    application.add_handler(CommandHandler('mesajekle', mesaj_ekle_command))
    application.add_handler(CommandHandler('mesajlar', mesajlar_command))
    application.add_handler(CommandHandler('mesajsil', mesaj_sil_command))
    application.add_handler(CommandHandler('soz', soz_command))
    application.add_handler(CommandHandler('sozekle', sozekle_command))
    application.add_handler(CommandHandler('sozler', sozler_command))
    application.add_handler(CommandHandler('sozsil', sozsil_command))
    application.add_handler(CommandHandler('durum', durum_command))
    
    # Media & Text Handlers
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    print(f"Bot çalışıyor (Admin IDs: {config.ADMIN_IDS})...")
    application.run_polling()

if __name__ == '__main__':
    main()

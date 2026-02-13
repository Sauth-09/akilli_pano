import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'data.json')

# Web Configuration
WEB_STATIC_DIR = os.path.join(BASE_DIR, 'src', 'web', 'static')
WEB_TEMPLATE_DIR = os.path.join(BASE_DIR, 'src', 'web', 'templates')
SLIDESHOW_DIR = os.path.join(WEB_STATIC_DIR, 'slideshow')

# Bot Configuration
# User should set these in .env or here
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# Admin IDs as a list of integers
try:
    admin_ids_str = os.getenv("ADMIN_IDS", "123456789")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
except ValueError:
    ADMIN_IDS = []

# Ensure directories exist
os.makedirs(SLIDESHOW_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

import os
from dotenv import load_dotenv

import sys

load_dotenv()

if getattr(sys, 'frozen', False):
    # PyInstaller Bundle
    # sys.executable -> Path to the executable being run
    # sys._MEIPASS -> Path to the temporary folder containing bundled files (onefile)
    #                 OR path to the directory containing the executable (onedir, usually)
    
    # For user data (data.json), we want it next to the executable
    USER_DATA_DIR = os.path.dirname(sys.executable)
    
    # For application resources (templates, static), we use the internal path
    # In onefile mode: sys._MEIPASS
    # In onedir mode: sys._MEIPASS is not always set, usually resources are relative to exe in `_internal` or root.
    # However, PyInstaller sets sys._MEIPASS even for onedir in recent versions for consistency if using --onedir
    # Let's check if _MEIPASS exists, otherwise fall back to executable dir.
    if hasattr(sys, '_MEIPASS'):
        RESOURCE_DIR = sys._MEIPASS
    else:
        # For onedir without _MEIPASS (older versions or specific configs), resources are usually in . (root of dist) or _internal
        # Our spec says: datas=[('src/web/templates', 'src/web/templates')]
        # This puts them in `dist/AkilliPano/src/web/templates`
        RESOURCE_DIR = os.path.dirname(sys.executable)
        
else:
    # Development Mode
    USER_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = USER_DATA_DIR

DATA_DIR = os.path.join(USER_DATA_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'data.json')

# Web Configuration
# Templates and static files are always at the same relative path
WEB_STATIC_DIR = os.path.join(RESOURCE_DIR, 'src', 'web', 'static')
WEB_TEMPLATE_DIR = os.path.join(RESOURCE_DIR, 'src', 'web', 'templates')

SLIDESHOW_DIR = os.path.join(WEB_STATIC_DIR, 'slideshow')

# Network Configuration
WEB_PORT = int(os.getenv("WEB_PORT", 7000))

# Bot Configuration
# User should set these in .env or here
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# Admin IDs as a list of integers
try:
    admin_ids_str = os.getenv("ADMIN_IDS", "123456789")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
except ValueError:
    ADMIN_IDS = []

# Teacher Access Configuration
BOT_ACCESS_CODE = os.getenv("BOT_ACCESS_CODE", "okulpanosu")
ALLOWED_USERS_FILE = os.path.join(DATA_DIR, 'allowed_users.json')

# Network Configuration (School Network Support)
BOT_API_URL = os.getenv("BOT_API_URL", None)
# Default to True unless explicitly set to False/0
BOT_SSL_VERIFY = os.getenv("BOT_SSL_VERIFY", "True").lower() in ("true", "1", "yes")

# Ensure directories exist
os.makedirs(SLIDESHOW_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

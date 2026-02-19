import os
from dotenv import load_dotenv
import sys

# Determine Base Directory
if getattr(sys, 'frozen', False):
    # Frozen (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else BASE_DIR
else:
    # Development
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

# Load .env from Base Directory
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

USER_DATA_DIR = BASE_DIR
DATA_DIR = os.path.join(USER_DATA_DIR, 'data')
# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, 'data.json')

# Web Configuration
# Templates and static files are always at the same relative path
WEB_STATIC_DIR = os.path.join(RESOURCE_DIR, 'src', 'web', 'static')
WEB_TEMPLATE_DIR = os.path.join(RESOURCE_DIR, 'src', 'web', 'templates')

SLIDESHOW_DIR = os.path.join(WEB_STATIC_DIR, 'slideshow')
RIDDLES_DIR = os.path.join(WEB_STATIC_DIR, 'riddles')

# Network Configuration
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
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

def update_env_file(updates):
    """
    Updates the .env file with the given key-value pairs.
    Preserves comments and structure.
    """
    if not os.path.exists(ENV_PATH):
        # Create if not exists
        with open(ENV_PATH, 'w', encoding='utf-8') as f:
            for k, v in updates.items():
                f.write(f"{k}={v}\n")
        return

    # Read existing lines
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    keys_updated = set()

    for line in lines:
        stripped = line.strip()
        # Check if line is a key assignment (and not a comment)
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                keys_updated.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append new keys that weren't in the file
    for k, v in updates.items():
        if k not in keys_updated:
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f"{k}={v}\n")

    # Write back
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

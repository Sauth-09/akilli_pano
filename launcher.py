import subprocess
import threading
import time
import os
import sys
import webbrowser
import logging
from PIL import Image
import pystray
from pystray import MenuItem as item

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("launcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Launcher")

# Globals to manage threads/processes if needed
stop_event = threading.Event()

def run_web_server():
    logger.info("Starting Web Server...")
    try:
        from src.web.app import app
        # Disable reloader to avoid main thread issues in frozen app
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Web Server Error: {e}")

def run_telegram_bot():
    logger.info("Starting Telegram Bot...")
    try:
        # Import main from bot
        from src.bot.main import main as bot_main
        # We need to run this in a way that respects stop_event if possible,
        # but python-telegram-bot's polling is blocking. 
        # Since it's in a daemon thread, it will die when main process exits.
        bot_main()
    except Exception as e:
        logger.error(f"Telegram Bot Error: {e}")

def get_chrome_path():
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe"
    ]
    for path in chrome_paths:
        expanded = os.path.expandvars(path)
        if os.path.exists(expanded):
            return expanded
    return None

def launch_kiosk():
    url = "http://localhost:5000"
    logger.info(f"Launching Chrome in Kiosk mode at {url}")
    chrome_exe = get_chrome_path()
    if chrome_exe:
        try:
            subprocess.Popen([
                chrome_exe,
                "--kiosk",
                "--incognito",
                "--disable-infobars",
                "--no-first-run",
                url
            ])
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            webbrowser.open(url)
    else:
        logger.warning("Chrome not found. Opening default browser.")
        webbrowser.open(url)

def open_settings():
    webbrowser.open("http://localhost:5000/admin")

def exit_app(icon, item):
    logger.info("Exiting application...")
    stop_event.set()
    icon.stop()
    # Force exit because flask/bot threads might linger
    os._exit(0)

if __name__ == "__main__":
    # Ensure working directory is set to script location (crucial for pyinstaller)
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Start Web Server in a separate thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start Telegram Bot in a separate thread
    # (Moved to thread because pystray needs main thread)
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    # Launch Chrome Kiosk initially
    # Wait a bit for server
    logger.info("Waiting for servers to start before launching kiosk...")
    threading.Timer(5.0, launch_kiosk).start()

    # System Tray Icon Setup
    try:
        image = Image.open("logo.ico")
    except:
        # Fallback if logo not found (create simple image)
        from PIL import ImageDraw
        image = Image.new('RGB', (64, 64), color = (73, 109, 137))
        d = ImageDraw.Draw(image)
        d.text((10,10), "Pano", fill=(255,255,0))

    menu = (
        item('Arayüzü Aç (Tam Ekran)', lambda icon, item: launch_kiosk()),
        item('Ayarlar', lambda icon, item: open_settings()),
        item('Çıkış', exit_app)
    )

    icon = pystray.Icon("AkilliPano", image, "Akıllı Pano", menu)
    
    logger.info("System Tray Icon started.")
    icon.run()

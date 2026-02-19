import os
import sys
import subprocess
import threading
import time
import webbrowser
import logging
from PIL import Image
import pystray
from pystray import MenuItem as item

import config

# Determine base directory for logs
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

log_path = os.path.join(base_dir, "launcher.log")

# Configure logging
from logging.handlers import RotatingFileHandler
handlers = [RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3)]
if not getattr(sys, 'frozen', False):
    handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger("Launcher")

# Redirect stdout/stderr to logging if frozen (to capture app.run output/errors)
if getattr(sys, 'frozen', False):
    class LogWriter:
        def __init__(self, logger, level):
            self.logger = logger
            self.level = level
        def write(self, message):
            if message.strip():
                self.logger.log(self.level, message.strip())
        def flush(self):
            pass
    
    sys.stdout = LogWriter(logger, logging.INFO)
    sys.stderr = LogWriter(logger, logging.ERROR)

# Globals to manage threads/processes if needed
stop_event = threading.Event()

def run_web_server():
    logger.info(f"Starting Web Server on port {config.WEB_PORT}...")
    try:
        logger.info("Importing src.web.app...")
        from src.web.app import app
        logger.info("Imported src.web.app successfully.")
        
        # Disable reloader to avoid main thread issues in frozen app
        logger.info(f"Calling app.run(host={config.WEB_HOST}, port={config.WEB_PORT})...")
        app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False, use_reloader=False)
        logger.info("app.run exited.")
    except Exception as e:
        logger.error(f"Web Server Error: {e}")
        import traceback
        logger.error(traceback.format_exc())

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

def wait_for_server(port=None, timeout=30):
    if port is None:
        port = config.WEB_PORT
    start_time = time.time()
    logger.info(f"Waiting for server on port {port}...")
    while time.time() - start_time < timeout:
        try:
            import socket
            with socket.create_connection(("localhost", port), timeout=1):
                logger.info("Server connection successful.")
                return True
        except (socket.timeout, ConnectionRefusedError):
            if int(time.time() - start_time) % 5 == 0:
                logger.info("Still waiting for server...")
            time.sleep(1)
    logger.error("Timed out waiting for server.")
    return False

def launch_kiosk():
    url = f"http://localhost:{config.WEB_PORT}"
    logger.info("Waiting for Web Server to be ready...")
    
    if wait_for_server():
        logger.info(f"Server ready. Launching Chrome in Kiosk mode at {url}")
        chrome_exe = get_chrome_path()
        if chrome_exe:
            try:
                subprocess.Popen([
                    chrome_exe,
                    "--start-fullscreen",
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
    else:
        logger.error("Web Server failed to start within timeout.")
        # Show error dialog (Windows only)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Sunucu başlatılamadı! Lütfen log dosyasını kontrol edin.", "Hata", 16)
        except Exception:
            pass  # Non-Windows platform, just log

def open_settings():
    webbrowser.open(f"http://localhost:{config.WEB_PORT}/admin")

def exit_app(icon, item):
    logger.info("Exiting application...")
    stop_event.set()
    icon.stop()
    # Force exit because flask/bot threads might linger
    os._exit(0)

import socket

def find_free_port(start_port):
    """Finds the first available port starting from start_port."""
    for port in range(start_port, start_port + 1000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start_port  # Fallback

if __name__ == "__main__":
    # Ensure working directory is set to script location (crucial for pyinstaller)
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Find a free port (bypass Windows excluded ranges)
    try:
        new_port = find_free_port(config.WEB_PORT)
        if new_port != config.WEB_PORT:
            logger.info(f"Port {config.WEB_PORT} is unavailable/excluded. Switching to {new_port}.")
            config.WEB_PORT = new_port
    except Exception as e:
        logger.error(f"Port selection failed: {e}")

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
    except Exception:
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

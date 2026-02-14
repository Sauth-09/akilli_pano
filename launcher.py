import subprocess
import threading
import time
import os
import sys
import webbrowser
import logging

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
        bot_main()
    except Exception as e:
        logger.error(f"Telegram Bot Error: {e}")

def launch_chrome_kiosk():
    logger.info("Waiting for servers to start...")
    time.sleep(5) # Wait for Flask to be ready
    
    url = "http://localhost:5000"
    logger.info(f"Launching Chrome in Kiosk mode at {url}")
    
    # Try different Chrome paths
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe"
    ]
    
    chrome_exe = None
    for path in chrome_paths:
        expanded = os.path.expandvars(path)
        if os.path.exists(expanded):
            chrome_exe = expanded
            break
            
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
            webbrowser.open(url) # Fallback to default browser
    else:
        logger.warning("Chrome not found. Opening default browser.")
        webbrowser.open(url)

if __name__ == "__main__":
    # Ensure working directory is set to script location (crucial for pyinstaller)
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Start Web Server in a separate thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start Chrome Launcher in a separate thread (so it doesn't block bot)
    kiosk_thread = threading.Thread(target=launch_chrome_kiosk, daemon=True)
    kiosk_thread.start()

    # Run Telegram Bot in Main Thread (asyncio loop needs main thread usually preferred)
    try:
        run_telegram_bot()
    except KeyboardInterrupt:
        logger.info("Stopping...")

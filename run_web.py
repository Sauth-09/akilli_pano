from src.web.app import app
import config

if __name__ == '__main__':
    print(f"Starting Web Server on port {config.WEB_PORT}...")
    app.run(host='0.0.0.0', port=config.WEB_PORT, debug=True)

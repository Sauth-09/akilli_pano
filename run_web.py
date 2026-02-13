from src.web.app import app
import config

if __name__ == '__main__':
    print(f"Starting Web Server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)

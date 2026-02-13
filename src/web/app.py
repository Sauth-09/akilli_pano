from flask import Flask, render_template, jsonify
import os
import json
from datetime import datetime
import locale
import sys

# Ensure parent directory is in path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config

# Set locale for Turkish day names
try:
    locale.setlocale(locale.LC_TIME, "tr_TR.utf8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "Turkish_Turkey.1254")
    except locale.Error:
        pass # Fallback to default if Turkish locale is not available

app = Flask(__name__, 
            static_folder=config.WEB_STATIC_DIR, 
            template_folder=config.WEB_TEMPLATE_DIR)

def load_data():
    if not os.path.exists(config.DATA_FILE):
        return {}
    with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_slides')
def get_slides():
    files = []
    if os.path.exists(config.SLIDESHOW_DIR):
        for f in os.listdir(config.SLIDESHOW_DIR):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm')):
                files.append(f)
    return jsonify(files)

@app.route('/api/get_status')
def get_status():
    data = load_data()
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    current_day = now.strftime("%A")
    
    # Translate day name if locale didn't work or returned English
    days_map = {
        "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
        "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
    }
    if current_day in days_map:
        current_day_tr = days_map[current_day]
    else:
        current_day_tr = current_day # Fallback
        
    # Find duty teachers
    # We need the English day name for JSON lookup
    english_day = now.strftime("%A")
    duty_teachers = data.get('duty_teachers', {}).get(english_day, [])

    # Find current lesson/status
    current_status = "Ders Dışı"
    current_time = datetime.strptime(current_time_str, "%H:%M")
    
    schedule = data.get('schedule', {})
    
    for key, times in schedule.items():
        try:
            start_time = datetime.strptime(times['start'], "%H:%M")
            end_time = datetime.strptime(times['end'], "%H:%M")
            
            # Make sure we compare time objects correctly (ignoring date part issues if any)
            # The parsed time has 1900-01-01 date, which is fine as we compare against same
            
            if start_time <= current_time <= end_time:
                if key == "oglen_arasi":
                    current_status = "Öğle Arası"
                else:
                    current_status = f"{key}. Ders"
                break
        except ValueError:
            continue
            
    # Simple check for breaks: if not in lesson, check if between lessons
    if current_status == "Ders Dışı":
        pass

    return jsonify({
        "status": current_status,
        "duty_teachers": duty_teachers,
        "date": now.strftime("%d.%m.%Y"),
        "time": current_time_str,
        "day": current_day_tr, # Send Turkish day name for display
        "messages": data.get('messages', [])
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

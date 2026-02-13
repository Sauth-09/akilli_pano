from flask import Flask, render_template, jsonify
import os
import json
from datetime import datetime
import locale

# Set locale for Turkish day names
try:
    locale.setlocale(locale.LC_TIME, "tr_TR.utf8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "Turkish_Turkey.1254")
    except locale.Error:
        pass # Fallback to default if Turkish locale is not available

app = Flask(__name__)
PORT = 5000
DATA_FILE = 'data.json'
SLIDESHOW_DIR = os.path.join('static', 'slideshow')

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_slides')
def get_slides():
    files = []
    if os.path.exists(SLIDESHOW_DIR):
        for f in os.listdir(SLIDESHOW_DIR):
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
        # If it's already Turkish or another language, keep it, or try to map reverse if needed. 
        # For simplicity, let's assume standard English names from datetime if locale fails, 
        # but the JSON keys are in English (Monday, etc.) so we need to map TO English for lookup 
        # and TO Turkish for display.
        # Actually data.json keys are English.
        current_day_tr = current_day # Fallback
        
    # Find duty teachers
    # We need the English day name for JSON lookup
    english_day = now.strftime("%A")
    duty_teachers = data['duty_teachers'].get(english_day, [])

    # Find current lesson/status
    current_status = "Ders Dışı"
    current_time = datetime.strptime(current_time_str, "%H:%M")
    
    schedule = data.get('schedule', {})
    
    # Sort schedule by start time to be sure
    # This part assumes keys are somewhat sortable or we iterate carefully
    # But keys are "1", "2", "oglen_arasi".
    
    for key, times in schedule.items():
        start_time = datetime.strptime(times['start'], "%H:%M")
        end_time = datetime.strptime(times['end'], "%H:%M")
        
        if start_time <= current_time <= end_time:
            if key == "oglen_arasi":
                current_status = "Öğle Arası"
            else:
                current_status = f"{key}. Ders"
            break
        
        # Check for break (tenefüs)
        # If we are between this lesson's end and next lesson's start
        # This is strictly fetching status. Logic can be improved if needed.
        
    # Simple check for breaks: if not in lesson, check if between lessons
    if current_status == "Ders Dışı":
        # Check if it's a break
        sorted_lessons = []
        for k, v in schedule.items():
            if k == 'oglen_arasi': continue
            sorted_lessons.append((k, v['start'], v['end']))
        
        # We need a proper way to check breaks. 
        # For now, let's just send what we found. 
        # Front-end might handle "Ders Dışı" better or we refine here.
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
    app.run(host='0.0.0.0', port=PORT, debug=True)

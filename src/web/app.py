from flask import Flask, render_template, jsonify, request, redirect, url_for
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
        pass 

app = Flask(__name__, 
            static_folder=config.WEB_STATIC_DIR, 
            template_folder=config.WEB_TEMPLATE_DIR)

def load_data():
    if not os.path.exists(config.DATA_FILE):
        return {}
    with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    data = load_data()
    school_name = data.get('school_name', 'OKUL ADI')
    logo_url = data.get('logo_url', '')
    return render_template('index.html', school_name=school_name, logo_url=logo_url)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    data = load_data()
    message = None

    if request.method == 'POST':
        # General Settings
        data['school_name'] = request.form.get('school_name')
        data['logo_url'] = request.form.get('logo_url')
        
        # Countdown
        data['countdown'] = {
            'label': request.form.get('countdown_label'),
            'target_date': request.form.get('countdown_date')
        }
        
        # Messages (split by newline)
        raw_msgs = request.form.get('messages', '')
        data['messages'] = [m.strip() for m in raw_msgs.split('\n') if m.strip()]
        
        # Schedule
        keys = request.form.getlist('schedule_keys[]')
        starts = request.form.getlist('schedule_start[]')
        ends = request.form.getlist('schedule_end[]')
        
        # Reconstruct schedule dict
        # We need to maintain order if possible, but python 3.7+ dicts describe order
        new_schedule = {}
        for i, key in enumerate(keys):
            if i < len(starts) and i < len(ends):
                new_schedule[key] = {'start': starts[i], 'end': ends[i]}
        data['schedule'] = new_schedule
        
        # Duty Roster (Matrix)
        locations = request.form.getlist('location[]')
        mondays = request.form.getlist('Monday[]')
        tuesdays = request.form.getlist('Tuesday[]')
        wednesdays = request.form.getlist('Wednesday[]')
        thursdays = request.form.getlist('Thursday[]')
        fridays = request.form.getlist('Friday[]')
        
        new_roster = []
        for i, loc_name in enumerate(locations):
            # Safe access to index
            if i < len(mondays):
                new_roster.append({
                    "location": loc_name,
                    "schedule": {
                        "Monday": mondays[i],
                        "Tuesday": tuesdays[i],
                        "Wednesday": wednesdays[i],
                        "Thursday": thursdays[i],
                        "Friday": fridays[i]
                    }
                })
        data['duty_roster'] = new_roster
            
        save_data(data)
        message = "Ayarlar başarıyla kaydedildi!"

    return render_template('admin.html', data=data, message=message)

@app.route('/api/get_status')
def get_status():
    data = load_data()
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    current_day = now.strftime("%A")
    
    # Translate day name
    days_map = {
        "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
        "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
    }
    current_day_tr = days_map.get(current_day, current_day)
        
    # Find duty teachers for today from Roster
    english_day = now.strftime("%A")
    duty_list = []
    
    roster = data.get('duty_roster', [])
    for item in roster:
        teacher = item.get('schedule', {}).get(english_day, '')
        if teacher:
            duty_list.append(f"{item['location']}: {teacher}")

    # Find current lesson/status
    current_status = "Ders Dışı"
    current_time = datetime.strptime(current_time_str, "%H:%M")
    
    schedule = data.get('schedule', {})
    
    for key, times in schedule.items():
        try:
            start_time = datetime.strptime(times['start'], "%H:%M")
            end_time = datetime.strptime(times['end'], "%H:%M")
            
            if start_time <= current_time <= end_time:
                if key == "oglen_arasi":
                    current_status = "Öğle Arası"
                else:
                    current_status = f"{key}. Ders"
                break
        except ValueError:
            continue

    return jsonify({
        "status": current_status,
        "duty_teachers": duty_list,
        "date": now.strftime("%d.%m.%Y"),
        "time": current_time_str,
        "day": current_day_tr,
        "messages": data.get('messages', []),
        "countdown": data.get('countdown', {})
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

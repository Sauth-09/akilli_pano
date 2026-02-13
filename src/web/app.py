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
        
        
        # Schedule (List-based)
        names = request.form.getlist('schedule_name[]')
        starts = request.form.getlist('schedule_start[]')
        ends = request.form.getlist('schedule_end[]')
        
        new_schedule = []
        for i, name in enumerate(names):
            if i < len(starts) and i < len(ends):
                new_schedule.append({
                    'name': name,
                    'start': starts[i],
                    'end': ends[i]
                })
        data['schedule'] = new_schedule
        
        
        # Class Schedules
        # Since indices are dynamic, we iterate until we find no more classes
        new_class_schedules = []
        # Limiting to 50 classes to prevent infinite loops if something goes wrong
        for i in range(50):
            # Try to get class name field
            class_name_key = f'class_name_{i}'
            if class_name_key not in request.form:
                # If we have gaps (deleted items), we might miss them if we break.
                # But HTML logic puts them in sequential wrapper-ids usually.
                # If dynamic JS deletion keeps old IDs, we might have gaps.
                # Let's try checking a known range or iterating keys?
                # Simpler: The sidebar has 'class_names[]'. iterating that won't give us keys.
                # Let's rely on the assumption that we process what exists.
                # But wait, JS 'add class' uses sequential IDs. 'Remove' removes DOM. 
                # If I remove index 0, index 1 status becomes index 0 in visual list? No.
                # Let's iterate all form keys to find 'class_name_X'.
                pass
            
        # Better approach: Loop through a reasonable range and check if data exists
        processed_schedules = []
        for i in range(50):
            name_key = f'class_name_{i}'
            if name_key in request.form:
                c_name = request.form[name_key]
                program = {}
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                for day in days:
                    lessons = request.form.getlist(f'schedule_{i}_{day}[]')
                    program[day] = lessons
                processed_schedules.append({
                    "name": c_name,
                    "program": program
                })
        
        if processed_schedules:
            data['class_schedules'] = processed_schedules

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

    # Find current lesson/status AND current lesson index for classes
    current_status = "Ders Dışı"
    current_lesson_index = -1 # -1 means no lesson (break or off)
    current_time = datetime.strptime(current_time_str, "%H:%M")
    
    schedule = data.get('schedule', [])
    if isinstance(schedule, dict):
         schedule_list = []
         for k, v in schedule.items():
            schedule_list.append({'name': k, 'start': v['start'], 'end': v['end']})
         schedule = schedule_list

    for index, item in enumerate(schedule):
        try:
            start_time = datetime.strptime(item['start'], "%H:%M")
            end_time = datetime.strptime(item['end'], "%H:%M")
            
            if start_time <= current_time <= end_time:
                current_status = item['name']
                # Check if this item name represents a lesson (contains "Ders") or logic mapping
                # Assuming "1. Ders" -> index 0, "2. Ders" -> index 1.
                # However, breaks are also in schedule. We only want to count "Lessons".
                # A heuristic: if it's "Öğle Arası", index is -1.
                if "Ders" in item['name']:
                    # We need to find which "Ders" it is.
                    # Or simpler: count how many items BEFORE this one had "Ders" in name.
                    pass
                break
        except (ValueError, KeyError):
            continue
            
    # Calculate lesson index properly
    # We iterate again to find the index of the CURRENT lesson among all lessons.
    lesson_count = 0
    calculated_index = -1
    for item in schedule:
        try:
            s = datetime.strptime(item['start'], "%H:%M")
            e = datetime.strptime(item['end'], "%H:%M")
            # If it's a lesson (heuristic: not "Arası")
            if "Ders" in item.get('name', '') or "Etüt" in item.get('name', ''):
                if s <= current_time <= e:
                    calculated_index = lesson_count
                lesson_count += 1
        except: pass
    
    current_lesson_index = calculated_index

    # Get Class Status
    class_status_list = []
    if current_lesson_index != -1 and current_day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        classes = data.get('class_schedules', [])
        for cls in classes:
            prog = cls.get('program', {}).get(current_day, [])
            if current_lesson_index < len(prog):
                lesson_name = prog[current_lesson_index]
                if lesson_name:
                    class_status_list.append(f"{cls['name']}: {lesson_name}")

    return jsonify({
        "status": current_status,
        "duty_teachers": duty_list,
        "class_statuses": class_status_list, 
        "date": now.strftime("%d.%m.%Y"),
        "time": current_time_str,
        "day": current_day_tr,
        "messages": data.get('messages', []),
        "countdown": data.get('countdown', {})
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import os
import json
import copy
from datetime import datetime
import locale
import sys
import pandas as pd
import subprocess
from logging.handlers import RotatingFileHandler
import traceback

# Conditional import for Windows-only module
try:
    import winreg
except ImportError:
    winreg = None

# Ensure parent directory is in path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
import logging

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

# Secret key for session management
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'akilli-pano-secret-key-2026')

# Admin password (from data.json or config)
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')

# Configure logging with rotation (max 5MB, keep 3 backups)
handler = RotatingFileHandler("launcher.log", maxBytes=5*1024*1024, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
logging.getLogger('werkzeug').addHandler(handler)

DEFAULT_DATA = {
    "duty_roster": [],
    "class_schedules": [],
    "birthdays": [],
    "messages": ["Akıllı Okul Panosu Sistemine Hoşgeldiniz"],
    "quotes": ["Kitap okumayı unutmayın."],
    "school_name": "OKUL ADI",
    "logo_url": "",
    "slideshow": {
        "duration": 5000,
        "transition": "fade",
        "order": "newest",
        "fit_mode": "contain"
    },
    "performance_mode": "high",
    "countdown": {
        "label": "Geri Sayım",
        "target_date": ""
    },
    "layout": [
        {"id": "card-status", "title": "Durum", "visible": True, "type": "status"},
        {"id": "card-duty", "title": "Nöbetçi Öğretmenler", "visible": True, "type": "duty"},
        {"id": "card-quote", "title": "Günün Sözü", "visible": True, "type": "quote"},
        {"id": "card-countdown", "title": "Geri Sayım", "visible": True, "type": "countdown"},
        {"id": "card-birthdays", "title": "Doğum Günleri", "visible": True, "type": "birthdays"},
        {"id": "card-classes", "title": "Sınıf Durumları", "visible": True, "type": "classes"},
        {"id": "card-riddle", "title": "Bilmece/Soru", "visible": True, "type": "riddle"}
    ],
    "schedule": [],
    "marquee": {
        "font_size": "1.2",
        "duration": "30",
        "color": "#2c3e50",
        "font_family": "inherit"
    }
}

def load_data():
    data = copy.deepcopy(DEFAULT_DATA)
    if os.path.exists(config.DATA_FILE):
        try:
            with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Simple merge for top-level keys
                for k, v in loaded.items():
                    if isinstance(v, dict) and k in data and isinstance(data[k], dict):
                        data[k].update(v)
                    else:
                        data[k] = v
        except Exception as e:
            app.logger.error(f"Error loading data.json: {e}")
    
    # Migration: Ensure new cards exist in layout
    existing_ids = [item.get('id') for item in data.get('layout', [])]
    if 'card-riddle' not in existing_ids:
        data['layout'].append({"id": "card-riddle", "title": "Bilmece/Soru", "visible": True, "type": "riddle"})
    
    return data

def save_data(data):
    with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    data = load_data()
    school_name = data.get('school_name', 'OKUL ADI')
    logo_url = data.get('logo_url', '')
    layout = data.get('layout', [])
    return render_template('index.html', school_name=school_name, logo_url=logo_url, layout=layout, data=data)

def rotate_roster(data):
    """
    Rotates teachers among locations for each day.
    """
    roster = data.get('duty_roster', [])
    if not roster or len(roster) < 2:
        return data

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for day in days:
        teachers = []
        for item in roster:
            teachers.append(item.get('schedule', {}).get(day, ""))
        
        if teachers:
            # Shift right: Last element becomes first
            rotated_teachers = [teachers[-1]] + teachers[:-1]
            
            for i, item in enumerate(roster):
                if 'schedule' not in item: item['schedule'] = {}
                item['schedule'][day] = rotated_teachers[i]
    return data

def handle_save_settings(data):
    # General Settings Save
    data['school_name'] = request.form.get('school_name')
    
    # --- ENV Update Start ---
    new_bot_token = request.form.get('bot_token', '').strip()
    new_admin_ids = request.form.get('admin_ids', '').strip()
    new_access_code = request.form.get('bot_access_code', '').strip()
    # Checkbox not present means False usually, but we need to check if form was submitted
    # If checkbox is unchecked, it won't be in request.form
    new_ssl_verify = 'True' if request.form.get('bot_ssl_verify') else 'False'
    
    env_updates = {}
    if new_bot_token:
        env_updates['BOT_TOKEN'] = new_bot_token
    if new_admin_ids:
        # Validate admin_ids format roughly (numbers and commas)
        env_updates['ADMIN_IDS'] = new_admin_ids
    if new_access_code:
        env_updates['BOT_ACCESS_CODE'] = new_access_code
    
    # Always update SSL verify setting since it's a checkbox
    env_updates['BOT_SSL_VERIFY'] = new_ssl_verify
    
    if env_updates:
        config.update_env_file(env_updates)
        # Update runtime config variables so they are reflected in UI immediately (if needed)
        # Note: This won't update the running bot process until restart, but updates the UI view.
        if 'BOT_TOKEN' in env_updates: config.BOT_TOKEN = env_updates['BOT_TOKEN']
        if 'BOT_ACCESS_CODE' in env_updates: config.BOT_ACCESS_CODE = env_updates['BOT_ACCESS_CODE']
        if 'BOT_SSL_VERIFY' in env_updates: config.BOT_SSL_VERIFY = (new_ssl_verify == 'True')
        if 'ADMIN_IDS' in env_updates:
                try:
                    config.ADMIN_IDS = [int(x.strip()) for x in env_updates['ADMIN_IDS'].split(',') if x.strip()]
                except: pass
    # --- ENV Update End ---

    # Update data.json legacy access code if used there, though we are moving to .env
    data['bot_access_code'] = new_access_code
    
    # Logo Upload Handling
    if 'logo_file' in request.files:
        file = request.files['logo_file']
        if file.filename != '':
            # Ensure static/img exists
            img_dir = os.path.join(app.static_folder, 'img')
            if not os.path.exists(img_dir):
                os.makedirs(img_dir)
            
            # Save file with a standard name or original name
            # Let's use 'school_logo' + extension to keep it simple and overwrite easily
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico']:
                filename = f"school_logo{ext}"
                full_path = os.path.join(img_dir, filename)
                file.save(full_path)
                
                # Update data with local path
                data['logo_url'] = url_for('static', filename=f'img/{filename}')
    
    # Fallback to URL input if no file uploaded, but only if url input is provided/changed?
    logo_url_input = request.form.get('logo_url')
    if logo_url_input and logo_url_input.strip() != '':
        # Only update if user explicitly entered a URL (or kept the old one)
        # But if we just uploaded a file, we set data['logo_url'] above.
        # If we want upload to take precedence:
        if 'logo_file' in request.files and request.files['logo_file'].filename != '':
            pass # Already handled above
        else:
            data['logo_url'] = logo_url_input
    
    data['countdown'] = {
        'label': request.form.get('countdown_label'),
        'target_date': request.form.get('countdown_date')
    }
    
    raw_msgs = request.form.get('messages', '')
    data['messages'] = [m.strip() for m in raw_msgs.split('\\n') if m.strip()]
    
    raw_quotes = request.form.get('quotes', '')
    data['quotes'] = [q.strip() for q in raw_quotes.split('\\n') if q.strip()]
    
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
    
    locations = request.form.getlist('location[]')
    mondays = request.form.getlist('Monday[]')
    tuesdays = request.form.getlist('Tuesday[]')
    wednesdays = request.form.getlist('Wednesday[]')
    thursdays = request.form.getlist('Thursday[]')
    fridays = request.form.getlist('Friday[]')
    
    new_roster = []
    for i, loc_name in enumerate(locations):
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
    
    # Marquee Settings
    data['marquee'] = {
        'font_size': request.form.get('marquee_font_size', '1.2'),
        'duration': request.form.get('marquee_duration', '30'),
        'color': request.form.get('marquee_color', '#2c3e50'),
        'font_family': request.form.get('marquee_font_family', "'Roboto', sans-serif")
    }

    # Class Schedules Processing (Shortened for brevity, assume same logic as before or re-include)
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

    # Layout Settings
    layout_ids = request.form.getlist('layout_id[]')
    # Checkbox values are only sent if checked. This makes handling checkboxes in a list tricky if they aren't uniquely named.
    # Alternative: We iterate over the received IDs, and check if `visible_{id}` is in form.
    new_layout = []
    if layout_ids:
        # We need to know the 'type' and 'title' for each ID. 
        # Since we don't send type/title back from form usually (unless hidden inputs), we might rely on existing data or hidden inputs.
        # Let's simple use hidden inputs for type and title too.
        layout_titles = request.form.getlist('layout_title[]')
        layout_types = request.form.getlist('layout_type[]')
        
        for i, lid in enumerate(layout_ids):
            visible_key = f'layout_visible_{lid}'
            is_visible = request.form.get(visible_key) == 'on'
            
            # Safe access
            title = layout_titles[i] if i < len(layout_titles) else ""
            ltype = layout_types[i] if i < len(layout_types) else ""
            
            new_layout.append({
                "id": lid,
                "title": title,
                "visible": is_visible,
                "type": ltype
            })
        data['layout'] = new_layout

    # Slideshow Settings
    # Helper to get int safely
    def get_int(key, default):
        try:
            return int(request.form.get(key, default))
        except (ValueError, TypeError):
            return default

    # Get existing or default
    exist_ss = data.get('slideshow', {})
    
    # Duration: if provided use it, else keep existing, else default 10
    # Note: Input sends value in seconds, we store ms
    dur_input = request.form.get('slideshow_duration')
    if dur_input:
        new_duration = int(dur_input) * 1000
    else:
        new_duration = exist_ss.get('duration', 10000)

    data['slideshow'] = {
        'duration': new_duration,
        'transition': request.form.get('slideshow_transition', exist_ss.get('transition', 'fade')),
        'order': request.form.get('slideshow_order', exist_ss.get('order', 'newest')),
        'fit_mode': request.form.get('slideshow_fit_mode', exist_ss.get('fit_mode', 'contain'))
    }
    
    # Performance Mode
    data['performance_mode'] = request.form.get('performance_mode', 'high')

    # Auto-rotate setting
    if 'duty_rotation' not in data: data['duty_rotation'] = {}
    data['duty_rotation']['auto_rotate'] = request.form.get('auto_rotate') == 'on'
    if data['duty_rotation']['auto_rotate'] and data['duty_rotation'].get('last_week_number', 0) == 0:
        data['duty_rotation']['last_week_number'] = datetime.now().isocalendar()[1]

    save_data(data)
    return "Ayarlar başarıyla kaydedildi!"

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        # Check password from data.json or env
        data = load_data()
        admin_pass = data.get('admin_password', ADMIN_PASSWORD)
        if password == admin_pass:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Hatalı şifre!'
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    data = load_data()
    message = None

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'rotate_now':
            rotate_roster(data)
            save_data(data)
            message = "Nöbetler döndürüldü."
        
             
        elif action == 'add_birthday':
            name = request.form.get('birthday_name')
            date_str = request.form.get('birthday_date')
            if name and date_str:
                if 'birthdays' not in data: data['birthdays'] = []
                data['birthdays'].append({'name': name, 'date': date_str})
                save_data(data)
                message = "Doğum günü eklendi."
                
        elif action == 'delete_birthday':
            name = request.form.get('delete_birthday_name')
            date_str = request.form.get('delete_birthday_date')
            if 'birthdays' in data:
                data['birthdays'] = [b for b in data['birthdays'] if not (b['name'] == name and b['date'] == date_str)]
                save_data(data)
                message = "Doğum günü silindi."

        elif action == 'import_birthdays':
            if 'birthday_file' in request.files:
                file = request.files['birthday_file']
                if file.filename != '':
                    try:
                        df = pd.read_excel(file)
                        # Heuristic: Find columns
                        name_col = None
                        surname_col = None
                        date_col = None
                        
                        for col in df.columns:
                            c_lower = str(col).lower()
                            if "ad" in c_lower and "soyad" in c_lower:
                                name_col = col
                            elif "ad" in c_lower and not name_col:
                                name_col = col
                            elif "soyad" in c_lower:
                                surname_col = col
                            if "doğum" in c_lower and "tarih" in c_lower:
                                date_col = col
                        
                        if 'birthdays' not in data: data['birthdays'] = []
                        added_count = 0
                        
                        if (name_col or (name_col and surname_col)) and date_col:
                            for index, row in df.iterrows():
                                try:
                                    full_name = ""
                                    if surname_col and name_col:
                                        full_name = f"{row[name_col]} {row[surname_col]}".strip()
                                    elif name_col:
                                        full_name = str(row[name_col]).strip()
                                    
                                    d = row[date_col]
                                    date_formatted = ""
                                    if isinstance(d, datetime):
                                        date_formatted = d.strftime("%d.%m")
                                    else:
                                        d_str = str(d).replace('/', '.')
                                        parts = d_str.split('.')
                                        if len(parts) >= 2:
                                            # Assuming DD.MM.YYYY or similar
                                            date_formatted = f"{parts[0].zfill(2)}.{parts[1].zfill(2)}"
                                    
                                    if date_formatted and not any(b['name'] == full_name and b['date'] == date_formatted for b in data['birthdays']):
                                        data['birthdays'].append({'name': full_name, 'date': date_formatted})
                                        added_count += 1
                                except Exception:
                                    continue
                            
                            save_data(data)
                            message = f"{added_count} kişi eklendi."
                        else:
                            message = "Sütunlar bulunamadı (Adı Soyadı, Doğum Tarihi)."
                    except Exception as e:
                        message = f"Hata: {str(e)}"
        
        elif action == 'save_settings' or action is None:
            try:
                message = handle_save_settings(data)
            except Exception as e:
                app.logger.error(f"Error saving settings: {e}")
                app.logger.error(traceback.format_exc())
                message = f"Hata oluştu: {str(e)}"

    # Prepare env data for admin panel
    env_data = {
        'bot_token': config.BOT_TOKEN,
        'admin_ids': ", ".join(map(str, config.ADMIN_IDS)),
        'bot_access_code': config.BOT_ACCESS_CODE
    }
    return render_template('admin.html', data=data, message=message, env_data=env_data)

@app.route('/api/get_status')
def get_status():
    data = load_data()
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    # Get English day name safely (independent of locale)
    day_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_day_en = day_names_en[now.weekday()]
    
    # Auto-Rotation Check
    current_iso_week = now.isocalendar()[1]
    rotation_settings = data.get('duty_rotation', {})
    last_week = rotation_settings.get('last_week_number', 0)
    
    if rotation_settings.get('auto_rotate'):
        # If it's a new week (and not week 0, and current > last, handling year wrap roughly)
        # Simple logic: If current week != last week.
        # But we only want to rotate ONCE per week.
        # And preferably on Monday? Or just "New Week".
        # If we just enabled it, we don't want immediate rotation unless it's a new week relative to setting?
        # Let's assume initialized last_week is set when setting is ENABLED.
        # But for now, if last_week != current_week, rotate.
        if last_week != 0 and current_iso_week != last_week:
             # Perform rotation
             rotate_roster(data)
             data['duty_rotation']['last_week_number'] = current_iso_week
             save_data(data)
             # Reload data to reflect changes immediately in this response
             # Actually 'data' object is updated in memory, so valid for this request.
        elif last_week == 0:
             # First initialization
             data['duty_rotation']['last_week_number'] = current_iso_week
             save_data(data)

    
    # Translate day name for display
    days_map = {
        "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
        "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
    }
    current_day_tr = days_map.get(current_day_en, current_day_en)
        
    # Find duty teachers for today from Roster
    duty_list = []
    
    roster = data.get('duty_roster', [])
    for item in roster:
        teacher = item.get('schedule', {}).get(current_day_en, '')
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
        except (ValueError, KeyError):
            pass
    
    current_lesson_index = calculated_index

    # Get Class Status
    class_status_list = []
    is_lesson = current_lesson_index != -1
    lesson_number = 0
    
    if is_lesson and current_day_en in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        lesson_number = current_lesson_index + 1  # 1-based
        classes = data.get('class_schedules', [])
        for cls in classes:
            prog = cls.get('program', {}).get(current_day_en, [])
            if current_lesson_index < len(prog):
                lesson_name = prog[current_lesson_index]
                if lesson_name:
                    class_status_list.append(f"{cls['name']}: {lesson_name}")

    # Get NEXT lesson classes (for break time display)
    next_class_status_list = []
    next_lesson_index = -1
    
    if not is_lesson and current_day_en in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        # Find the next lesson index
        next_lesson_count = 0
        for item in schedule:
            try:
                s = datetime.strptime(item['start'], "%H:%M")
                if "Ders" in item.get('name', '') or "Etüt" in item.get('name', ''):
                    if s > current_time:
                        next_lesson_index = next_lesson_count
                        break
                    next_lesson_count += 1
            except (ValueError, KeyError):
                continue
        
        if next_lesson_index != -1:
            classes = data.get('class_schedules', [])
            for cls in classes:
                prog = cls.get('program', {}).get(current_day_en, [])
                if next_lesson_index < len(prog):
                    lesson_name = prog[next_lesson_index]
                    if lesson_name:
                        next_class_status_list.append(f"{cls['name']}: {lesson_name}")

    # Birthdays
    todays_birthdays = []
    today_str = now.strftime("%d.%m")
    if 'birthdays' in data:
        for b in data['birthdays']:
            b_date = b.get('date', '')
            if b_date.startswith(today_str):
                todays_birthdays.append(b['name'])

    return jsonify({
        "status": current_status,
        "is_lesson": is_lesson,
        "lesson_number": lesson_number,
        "duty_teachers": duty_list,
        "class_statuses": class_status_list,
        "next_class_statuses": next_class_status_list,
        "birthdays": todays_birthdays,
        "date": now.strftime("%d.%m.%Y"),
        "time": current_time_str,
        "day": current_day_tr,
        "day": current_day_tr,
        "messages": data.get('messages', []),
        "quotes": data.get('quotes', []),
        "countdown": data.get('countdown', {}),
        "slideshow": data.get('slideshow', {}) 
    })

@app.route('/api/open_slides_folder')
def open_slides_folder():
    try:
        if not os.path.exists(config.SLIDESHOW_DIR):
            os.makedirs(config.SLIDESHOW_DIR)
        os.startfile(config.SLIDESHOW_DIR)
        return jsonify({'status': 'success', 'message': 'Klasör açıldı'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/toggle_autostart', methods=['POST'])
def toggle_autostart():
    if winreg is None:
        return jsonify({'status': 'error', 'message': 'Bu özellik sadece Windows\'ta çalışır.'})
    try:
        enable = request.json.get('enable', False)
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "AkilliPano"
        # We assume the executable is where this script is running from, or a specific launcher path.
        # When running from source (python), it's python.exe + script. 
        # When frozen (PyInstaller), it's the executable.
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            # Development mode: Launch with pythonw (no console) via launcher.py if exists, or just this script?
            # User wants "launcher.py" to be the main entry. 
            # Let's point to the current working directory's launcher.py if possible, or run_web.py?
            # Actually, robust way for dev is full path to pythonw.exe + full path to launcher.py
            launcher_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'launcher.py')
            if not os.path.exists(launcher_path):
                 # Fallback to run_web.py in root
                 launcher_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'run_web.py')
            
            exe_path = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{launcher_path}"'

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            msg = "Otomatik başlatma açıldı."
        else:
            try:
                winreg.DeleteValue(key, app_name)
                msg = "Otomatik başlatma kapatıldı."
            except FileNotFoundError:
                msg = "Zaten kapalıydı."
        
        winreg.CloseKey(key)
        return jsonify({'status': 'success', 'message': msg, 'enabled': enable})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/get_autostart_status')
def get_autostart_status():
    if winreg is None:
        return jsonify({'enabled': False})
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "AkilliPano"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, app_name)
            enabled = True
        except FileNotFoundError:
            enabled = False
        winreg.CloseKey(key)
        return jsonify({'enabled': enabled})
    except Exception:
        return jsonify({'enabled': False})

@app.route('/api/get_slides')
def get_slides():
    slides = []
    if os.path.exists(config.SLIDESHOW_DIR):
        valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm']
        files = []
        for f in os.listdir(config.SLIDESHOW_DIR):
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts:
                full_path = os.path.join(config.SLIDESHOW_DIR, f)
                files.append({'name': f, 'mtime': os.path.getmtime(full_path)})
        
        # Sort based on config
        data = load_data()
        order = data.get('slideshow', {}).get('order', 'newest')
        
        if order == 'newest':
            files.sort(key=lambda x: x['mtime'], reverse=True)
        elif order == 'oldest':
            files.sort(key=lambda x: x['mtime'])
        elif order == 'random':
            import random
            random.shuffle(files)
        # else name sort? default os.listdir is arbitrary/name usually.
            
        slides = [f['name'] for f in files]
        
    return jsonify(slides)

@app.route('/api/delete_slide', methods=['POST'])
def delete_slide():
    try:
        filename = request.json.get('filename', '')
        if not filename:
            return jsonify({'status': 'error', 'message': 'Dosya adı belirtilmedi.'})
        
        # Security: prevent path traversal
        safe_name = os.path.basename(filename)
        file_path = os.path.join(config.SLIDESHOW_DIR, safe_name)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'status': 'success', 'message': f'{safe_name} silindi.'})
        else:
            return jsonify({'status': 'error', 'message': 'Dosya bulunamadı.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/get_slides_with_info')
def get_slides_with_info():
    """Returns slide list with thumbnail info for admin panel."""
    slides = []
    if os.path.exists(config.SLIDESHOW_DIR):
        valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm']
        for f in sorted(os.listdir(config.SLIDESHOW_DIR), reverse=True):
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts:
                full_path = os.path.join(config.SLIDESHOW_DIR, f)
                size_kb = os.path.getsize(full_path) / 1024
                mtime = os.path.getmtime(full_path)
                dt = datetime.fromtimestamp(mtime)
                
                slides.append({
                    'name': f,
                    'size': f"{size_kb:.0f} KB",
                    'type': 'image' if ext in ['.jpg', '.jpeg', '.png', '.gif'] else 'video',
                    'timestamp': mtime,
                    'date_str': dt.strftime("%d.%m.%Y %H:%M"),
                    'url': url_for('static', filename=f'slideshow/{f}')
                })
    return jsonify(slides)


@app.route('/api/riddles')
def get_riddles():
    """Returns list of riddle images."""
    riddles = []
    if os.path.exists(config.RIDDLES_DIR):
        valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        for f in sorted(os.listdir(config.RIDDLES_DIR)):
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts:
                riddles.append(url_for('static', filename=f'riddles/{f}'))
    return jsonify(riddles)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.WEB_PORT, debug=True)

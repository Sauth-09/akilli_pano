"""
Shared data access module for thread-safe file operations.
Used by both web app and telegram bot to avoid code duplication
and ensure safe concurrent access to data.json.
"""

import os
import json
import copy
import threading
import logging

import config

logger = logging.getLogger(__name__)

# Thread lock for file operations
_data_lock = threading.Lock()

DEFAULT_DATA = {
    "duty_roster": [],
    "class_schedules": [],
    "lesson_count": 8,
    "birthdays": [],
    "messages": ["Akıllı Okul Panosu Sistemine Hoşgeldiniz"],
    "quotes": ["Kitap okumayı unutmayın."],
    "school_name": "OKUL ADI",
    "logo_url": "/static/logo.ico",
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
    "schedule": {
        "groups": [
            {
                "name": "Varsayılan",
                "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "items": []
            }
        ]
    },
    "marquee": {
        "font_size": "1.2",
        "duration": "30",
        "color": "#2c3e50",
        "font_family": "inherit"
    },
    "riddle": {
        "duration": 10000,
        "transition": "fade",
        "fit_mode": "contain"
    }
}


def load_data():
    """Load data.json with thread safety and default merging."""
    with _data_lock:
        data = copy.deepcopy(DEFAULT_DATA)
        if os.path.exists(config.DATA_FILE):
            try:
                with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        if isinstance(v, dict) and k in data and isinstance(data[k], dict):
                            data[k].update(v)
                        else:
                            data[k] = v
            except Exception as e:
                logger.error(f"Error loading data.json: {e}")

        # Migration: Ensure new cards exist in layout
        existing_ids = [item.get('id') for item in data.get('layout', [])]
        if 'card-riddle' not in existing_ids:
            data['layout'].append({"id": "card-riddle", "title": "Bilmece/Soru", "visible": True, "type": "riddle"})

        # Migration: Convert old flat schedule list to new group format
        schedule = data.get('schedule', {})
        if isinstance(schedule, list):
            data['schedule'] = {
                "groups": [
                    {
                        "name": "Varsayılan",
                        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                        "items": schedule
                    }
                ]
            }

        return data


def save_data(data):
    """Save data.json with thread safety and consistent formatting."""
    with _data_lock:
        try:
            os.makedirs(os.path.dirname(config.DATA_FILE), exist_ok=True)
            with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving data.json: {e}")
            return False


import json
import os

DATA_FILE = r'c:\Users\Sadullah\Desktop\Pano_Proje\data\data.json'

def restore_layout():
    if not os.path.exists(DATA_FILE):
        print(f"File not found: {DATA_FILE}")
        return

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Restore Layout Defaults
        default_layout = [
            {"id": "card-status", "title": "Durum", "visible": True, "type": "status"},
            {"id": "card-duty", "title": "Nöbetçi Öğretmenler", "visible": True, "type": "duty"},
            {"id": "card-quote", "title": "Günün Sözü", "visible": True, "type": "quote"},
            {"id": "card-countdown", "title": "Geri Sayım", "visible": True, "type": "countdown"},
            {"id": "card-birthdays", "title": "Doğum Günleri", "visible": True, "type": "birthdays"},
            {"id": "card-classes", "title": "Sınıf Durumları", "visible": True, "type": "classes"}
        ]
        
        # Update existing layout items with default titles/types if missing/empty
        current_layout = data.get('layout', [])
        # Create a map of current layout by ID to preserve visibility/order if possible
        layout_map = {item['id']: item for item in current_layout if 'id' in item}
        
        new_layout = []
        for item in default_layout:
            lid = item['id']
            if lid in layout_map:
                existing = layout_map[lid]
                # Keep visibility if it exists, but restore title/type if empty
                title = existing.get('title') or item['title']
                ltype = existing.get('type') or item['type']
                visible = existing.get('visible', item['visible'])
                
                new_layout.append({
                    "id": lid,
                    "title": title,
                    "visible": visible,
                    "type": ltype
                })
            else:
                new_layout.append(item)
        
        data['layout'] = new_layout
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("Layout restored successfully.")
        
    except Exception as e:
        print(f"Error restoring layout: {e}")

if __name__ == "__main__":
    restore_layout()

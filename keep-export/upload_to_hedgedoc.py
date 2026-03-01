import os
import requests
import time
import re

# --- KONFIGURATION ---
SOURCE_MD_FOLDER = os.path.expanduser('~/Dokumente/markdown_notes')
HEDGEDOC_URL = 'http://gmk.lan:3000'.rstrip('/')
HISTORY_FILE = os.path.join(SOURCE_MD_FOLDER, '.upload_history.txt')
DELAY_BETWEEN_UPLOADS = 1.5 
# ---------------------

def slugify(text):
    """Macht Dateinamen URL-konform: 'Mein Test.md' -> 'mein-test'"""
    text = text.replace('.md', '').lower()
    # Umlaute ersetzen
    text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    # Alles außer Buchstaben und Zahlen durch Bindestrich ersetzen
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def get_uploaded_files():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def add_to_history(filename):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{filename}\n")

def upload_note(file_path):
    filename = os.path.basename(file_path)
    if filename in uploaded_set:
        print(f"⏩ Überspringe: {filename}")
        return True

    alias = slugify(filename) # Erstellt den schönen Namen
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    while True:
        try:
            # WICHTIG: Wir posten an /new/ALIAS
            target_url = f"{HEDGEDOC_URL}/new/{alias}"
            
            response = requests.post(
                target_url,
                data=content.encode('utf-8'),
                headers={'Content-Type': 'text/markdown'},
                allow_redirects=False
            )
            
            # 200 = OK, 302 = Redirect zur neuen Notiz
            if response.status_code in [200, 302]:
                new_location = response.headers.get('Location', '')
                final_url = f"{HEDGEDOC_URL}{new_location}" if not new_location.startswith('http') else new_location
                
                print(f"✅ Alias erstellt: {alias} -> {final_url}")
                add_to_history(filename)
                return True
            
            elif response.status_code == 403:
                print(f"❌ Fehler 403 bei {alias}: Aliases sind auf diesem Server für Gäste deaktiviert.")
                return False
                
            elif response.status_code == 429:
                print(f"⏳ Rate Limit. Pause 15s...")
                time.sleep(15)
                continue
            else:
                print(f"❌ Fehler bei {filename}: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠ Fehler: {e}")
            return False

def main():
    global uploaded_set
    uploaded_set = get_uploaded_files()
    files = sorted([f for f in os.listdir(SOURCE_MD_FOLDER) if f.endswith('.md')])
    
    print(f"🚀 Starte Alias-Import für {len(files)} Dateien...")
    for filename in files:
        if upload_note(os.path.join(SOURCE_MD_FOLDER, filename)):
            time.sleep(DELAY_BETWEEN_UPLOADS)

if __name__ == "__main__":
    main()
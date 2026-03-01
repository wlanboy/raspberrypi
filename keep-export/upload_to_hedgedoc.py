import os
import requests
import time
import re
import argparse
from datetime import datetime

# --- KONFIGURATION ---
SOURCE_MD_FOLDER = os.path.expanduser('~/Dokumente/markdown_notes')
HEDGEDOC_URL = 'http://gmk.lan:3000'.rstrip('/')
HISTORY_FILE = os.path.join(SOURCE_MD_FOLDER, '.upload_history.txt')
DELAY_BETWEEN_UPLOADS = 0
MAX_RATE_LIMIT_RETRIES = 5
INDEX_ALIAS = 'notizen-index'
# ---------------------

def slugify(text):
    """Macht Dateinamen URL-konform: 'Mein Test.md' -> 'mein-test'"""
    text = os.path.splitext(text)[0].lower()
    text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def get_uploaded_files():
    """
    Gibt dict {filename: url} zurück.
    Format neu: 'filename=url'
    Format alt: 'filename' (URL wird per slugify rekonstruiert)
    """
    if not os.path.exists(HISTORY_FILE):
        return {}
    result = {}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if '=' in line:
                filename, url = line.split('=', 1)
                result[filename] = url
            else:
                result[line] = ''  # altes Format, URL wird später rekonstruiert
    return result

def add_to_history(filename, url):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{filename}={url}\n")

def _post_note(alias, content):
    """Sendet POST /new/ALIAS. Gibt (status_code, final_url) zurück."""
    response = requests.post(
        f"{HEDGEDOC_URL}/new/{alias}",
        data=content.encode('utf-8'),
        headers={'Content-Type': 'text/markdown'},
        allow_redirects=False
    )
    if response.status_code == 302:
        location = response.headers.get('Location', '')
        final_url = f"{HEDGEDOC_URL}{location}" if not location.startswith('http') else location
        return 302, final_url
    return response.status_code, ''

def upload_note(file_path, uploaded_dict, used_aliases, dry_run=False, force=False):
    """Gibt (status, url) zurück. Status: 'success'|'skipped'|'error'|'dry_run'"""
    filename = os.path.basename(file_path)

    if filename in uploaded_dict and not force:
        stored_url = uploaded_dict[filename]
        url = stored_url if stored_url else f"{HEDGEDOC_URL}/{slugify(filename)}"
        print(f"⏩ Überspringe: {filename}")
        return 'skipped', url

    base_alias = slugify(filename)
    alias = base_alias
    counter = 2
    while alias in used_aliases:
        alias = f"{base_alias}-{counter}"
        counter += 1
    used_aliases.add(alias)

    if dry_run:
        print(f"[DRY-RUN] Würde hochladen: {filename} -> /new/{alias}")
        return 'dry_run', f"{HEDGEDOC_URL}/{alias}"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    rate_limit_retries = 0
    while True:
        try:
            status_code, final_url = _post_note(alias, content)

            if status_code == 302:
                print(f"✅ Hochgeladen: {alias} -> {final_url}")
                add_to_history(filename, final_url)
                return 'success', final_url

            elif status_code == 200:
                print(f"⚠ Unerwartete 200-Antwort für {alias} (kein Redirect). Notiz evtl. nicht erstellt.")
                return 'error', ''

            elif status_code == 409:
                print(f"⚠ Alias '{alias}' bereits belegt auf dem Server, überspringe {filename}.")
                return 'error', ''

            elif status_code == 403:
                print(f"❌ Fehler 403 bei {alias}: Aliases sind auf diesem Server für Gäste deaktiviert.")
                return 'error', ''

            elif status_code == 429:
                rate_limit_retries += 1
                if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
                    print(f"❌ Rate Limit für {filename} nach {MAX_RATE_LIMIT_RETRIES} Versuchen aufgegeben.")
                    return 'error', ''
                print(f"⏳ Rate Limit. Pause 15s... (Versuch {rate_limit_retries}/{MAX_RATE_LIMIT_RETRIES})")
                time.sleep(15)
                continue

            else:
                print(f"❌ Fehler bei {filename}: Status {status_code}")
                return 'error', ''

        except Exception as e:
            print(f"⚠ Fehler: {e}")
            return 'error', ''

def build_index_content(note_links):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Notizen-Index",
        "",
        f"*Zuletzt aktualisiert: {timestamp} — {len(note_links)} Notizen*",
        "",
    ]
    for filename, url in sorted(note_links.items()):
        title = os.path.splitext(filename)[0]
        lines.append(f"- [{title}]({url})")
    return "\n".join(lines)

def create_index_note(note_links, dry_run=False):
    if not note_links:
        print("  Keine Notizen für den Index vorhanden.")
        return

    try:
        answer = input(f"\nIndex-Notiz mit {len(note_links)} Links erstellen? [J/n] ").strip().lower()
    except EOFError:
        answer = ''  # nicht-interaktiv: default ja

    if answer not in ('', 'j', 'ja', 'y', 'yes'):
        print("  Index-Notiz übersprungen.")
        return

    content = build_index_content(note_links)

    if dry_run:
        print(f"[DRY-RUN] Würde Index-Notiz erstellen: /new/{INDEX_ALIAS} ({len(note_links)} Links)")
        return

    try:
        status_code, final_url = _post_note(INDEX_ALIAS, content)
        if status_code == 302:
            print(f"✅ Index-Notiz erstellt: {final_url}")
        elif status_code == 409:
            print(f"⚠ Index-Alias '{INDEX_ALIAS}' bereits belegt.")
            print(f"  Bitte alte Index-Notiz unter {HEDGEDOC_URL}/{INDEX_ALIAS} manuell löschen und erneut starten.")
        else:
            print(f"❌ Fehler bei Index-Notiz: Status {status_code}")
    except Exception as e:
        print(f"⚠ Fehler beim Erstellen der Index-Notiz: {e}")

def main():
    parser = argparse.ArgumentParser(description='Markdown-Notizen zu HedgeDoc hochladen')
    parser.add_argument('--force', action='store_true',
                        help='Bereits hochgeladene Dateien erneut hochladen')
    parser.add_argument('--dry-run', action='store_true',
                        help='Nur anzeigen, was hochgeladen würde, ohne tatsächlich zu uploaden')
    args = parser.parse_args()

    uploaded_dict = get_uploaded_files()
    used_aliases = set()
    note_links = {}  # filename -> url (alle bekannten Notizen)

    files = sorted([f for f in os.listdir(SOURCE_MD_FOLDER) if f.endswith('.md')])

    mode_label = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode_label}🚀 Starte Alias-Import für {len(files)} Dateien...")

    results = {'success': 0, 'skipped': 0, 'error': 0, 'dry_run': 0}

    for filename in files:
        result, url = upload_note(
            os.path.join(SOURCE_MD_FOLDER, filename),
            uploaded_dict,
            used_aliases,
            dry_run=args.dry_run,
            force=args.force,
        )
        results[result] += 1
        if result in ('success', 'skipped', 'dry_run') and url:
            note_links[filename] = url
        if result in ('success', 'dry_run'):
            time.sleep(DELAY_BETWEEN_UPLOADS)

    print("\n--- Zusammenfassung ---")
    if args.dry_run:
        print(f"  Würden hochgeladen:  {results['dry_run']}")
        print(f"  Würden übersprungen: {results['skipped']}")
    else:
        print(f"  Erfolgreich: {results['success']}")
        print(f"  Übersprungen: {results['skipped']}")
        print(f"  Fehler:      {results['error']}")

    create_index_note(note_links, dry_run=args.dry_run)

if __name__ == "__main__":
    main()

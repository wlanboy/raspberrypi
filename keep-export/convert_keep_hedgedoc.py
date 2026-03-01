import json
import os
import datetime
import re

# --- PFADE ANPASSEN ---
SOURCE_FOLDER = os.path.expanduser('~/Downloads/Takeout/GoogleNotizen')
OUTPUT_FOLDER = os.path.expanduser('~/Dokumente/markdown_notes')
# ----------------------

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def convert_time(usec):
    """Konvertiert Google Microseconds Timestamp in lesbares Datum."""
    return datetime.datetime.fromtimestamp(usec / 1000000).strftime('%Y-%m-%d %H:%M')

def clean_filename(title):
    """Entfernt ungültige Zeichen für Dateinamen."""
    return re.sub(r'[\\/*?:"<>|]', "", title).strip()

def json_to_hedgedoc_markdown(data):
    title = data.get('title', '').strip()
    content = data.get('textContent', '')
    created = convert_time(data.get('createdTimestampUsec', 0))
    labels = [l['name'] for l in data.get('labels', [])]
    
    # Falls kein Titel da ist, Zeitstempel nutzen
    if not title:
        title = f"Notiz_{created.replace(':', '-')}"

    md_lines = []

    # --- HedgeDoc Spezifische Tags ---
    # Format: ###### tags: `Label1` `Label2`
    if labels:
        tag_line = " ".join([f"`{l}`" for l in labels])
        md_lines.append(f"###### tags: {tag_line}\n")
    
    # --- Inhalt der Notiz ---
    md_lines.append(f"# {title}")
    md_lines.append(f"> **Erstellt am:** {created}\n")
    md_lines.append("---")
    md_lines.append(content)
    
    # --- Anhänge / Links ---
    if 'annotations' in data:
        md_lines.append("\n---\n### Links & Quellen")
        for ann in data['annotations']:
            if ann.get('url'):
                md_lines.append(f"- [{ann.get('title', 'Link')}]({ann.get('url')})")

    return title, "\n".join(md_lines)

def main():
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Quellordner nicht gefunden: {SOURCE_FOLDER}")
        return

    files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith('.json')]
    print(f"Konvertiere {len(files)} Dateien...")

    for filename in files:
        with open(os.path.join(SOURCE_FOLDER, filename), 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Nur verarbeiten, wenn es eine echte Notiz ist
                if 'textContent' in data or 'title' in data:
                    title, md_text = json_to_hedgedoc_markdown(data)
                    
                    safe_title = clean_filename(title)
                    # Falls Titel nach dem Säubern leer ist
                    if not safe_title: safe_title = "Unbenannte_Notiz_" + str(int(time.time()))
                    
                    output_path = os.path.join(OUTPUT_FOLDER, f"{safe_title}.md")
                    
                    with open(output_path, 'w', encoding='utf-8') as out_f:
                        out_f.write(md_text)
            except Exception as e:
                print(f"⚠ Fehler bei {filename}: {e}")

    print(f"✅ Fertig! Die Dateien liegen in: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()
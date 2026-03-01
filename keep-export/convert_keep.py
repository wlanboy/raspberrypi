import json
import os
import datetime

# Konfiguration
SOURCE_FOLDER = os.path.expanduser('~/Downloads/Takeout/GoogleNotizen')  # Ordner mit den JSON Dateien
OUTPUT_FOLDER = os.path.expanduser('~/Dokumente/markdown_notes')

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def convert_time(usec):
    """Konvertiert Google Microseconds Timestamp in lesbares Datum"""
    return datetime.datetime.fromtimestamp(usec / 1000000).strftime('%Y-%m-%d %H:%M:%S')

def json_to_markdown(data):
    title = data.get('title')
    content = data.get('textContent', '')
    created = convert_time(data.get('createdTimestampUsec', 0))
    labels = [l['name'] for l in data.get('labels', [])]
    
    # Falls kein Titel vorhanden, nehme Erstellungsdatum als Titel
    if not title:
        title = f"Notiz_{created.replace(':', '-')}"

    md_content = []
    md_content.append(f"# {title}\n")
    
    # Metadaten / Frontmatter
    md_content.append(f"**Erstellt am:** {created}")
    if labels:
        md_content.append(f"**Tags:** #{' #'.join(labels)}")
    md_content.append("\n---\n")
    
    # Der eigentliche Text
    md_content.append(content)
    
    # Anhänge / Links (Annotations)
    if 'annotations' in data:
        md_content.append("\n\n### Links / Quellen")
        for ann in data['annotations']:
            if ann.get('url'):
                md_content.append(f"- [{ann.get('title', 'Link')}]({ann.get('url')})")

    return title, "\n".join(md_content)

def main():
    for filename in os.listdir(SOURCE_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(SOURCE_FOLDER, filename), 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    
                    # Nur Notizen verarbeiten (keine Müll-Dateien)
                    if 'textContent' in data or 'title' in data:
                        title, md_text = json_to_markdown(data)
                        
                        # Dateiname säubern (ungültige Zeichen entfernen)
                        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
                        output_path = os.path.join(OUTPUT_FOLDER, f"{safe_title}.md")
                        
                        with open(output_path, 'w', encoding='utf-8') as out_f:
                            out_f.write(md_text)
                        print(f"Konvertiert: {filename} -> {safe_title}.md")
                except Exception as e:
                    print(f"Fehler bei Datei {filename}: {e}")

if __name__ == "__main__":
    main()

import json
import os
import datetime
import unicodedata
import argparse

# Konfiguration
SOURCE_FOLDER = os.path.expanduser('~/Downloads/Takeout/GoogleNotizen')  # Ordner mit den JSON Dateien
OUTPUT_FOLDER = os.path.expanduser('~/Dokumente/markdown_notes')

# 8. Source-Ordner prüfen
if not os.path.exists(SOURCE_FOLDER):
    print(f"Fehler: Quellordner nicht gefunden: {SOURCE_FOLDER}")
    exit(1)

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


def convert_time(usec):
    """Konvertiert Google Microseconds Timestamp in lesbares Datum"""
    return datetime.datetime.fromtimestamp(usec / 1000000).strftime('%Y-%m-%d %H:%M:%S')


def sanitize_filename(name):
    """7. Dateinamen bereinigen – Umlaute und Unicode erlaubt, nur wirklich ungültige Zeichen entfernen"""
    # Normalize unicode (NFC), dann ungültige Dateisystemzeichen entfernen
    name = unicodedata.normalize('NFC', name)
    invalid_chars = set(r'\/:*?"<>|')
    sanitized = "".join(c for c in name if c not in invalid_chars).strip()
    return sanitized or "Unbenannte_Notiz"


def json_to_markdown(data, hedgedoc=False):
    title = data.get('title', '')
    created = convert_time(data.get('createdTimestampUsec', 0))
    edited_usec = data.get('userEditedTimestampUsec', 0)
    labels = [l['name'] for l in data.get('labels', [])]
    color = data.get('color', '')
    is_archived = data.get('isArchived', False)

    if not title:
        title = f"Notiz_{created.replace(':', '-')}"

    if is_archived:
        labels.append('archiviert')

    if color and color.upper() != 'DEFAULT':
        labels.append(f'farbe:{color.lower()}')

    md_content = []

    if hedgedoc and labels:
        tag_line = " ".join([f"`{l}`" for l in labels])
        md_content.append(f"###### tags: {tag_line}\n")

    md_content.append(f"# {title}\n")

    # Metadaten
    md_content.append(f"**Erstellt am:** {created}")
    if edited_usec:
        md_content.append(f"**Bearbeitet am:** {convert_time(edited_usec)}")
    if not hedgedoc and labels:
        md_content.append(f"**Tags:** #{' #'.join(labels)}")
    md_content.append("\n---\n")

    # 2. Textinhalt oder Checkliste
    if 'listContent' in data:
        for item in data['listContent']:
            checkbox = '[x]' if item.get('isChecked', False) else '[ ]'
            md_content.append(f"- {checkbox} {item.get('text', '')}")
    else:
        content = data.get('textContent', '')
        if content:
            md_content.append(content)

    # Anhänge / Links (Annotations)
    if 'annotations' in data:
        md_content.append("\n\n### Links / Quellen")
        for ann in data['annotations']:
            if ann.get('url'):
                md_content.append(f"- [{ann.get('title', 'Link')}]({ann.get('url')})")

    return title, "\n".join(md_content)  # 9. Blöcke werden mit \n verbunden; Abschnitte tragen eigene \n


def main():
    parser = argparse.ArgumentParser(description='Google Keep JSON zu Markdown konvertieren')
    parser.add_argument('--hedgedoc', action='store_true', help='HedgeDoc-kompatible Tag-Zeile verwenden')
    args = parser.parse_args()

    used_names = {}

    for filename in sorted(os.listdir(SOURCE_FOLDER)):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(SOURCE_FOLDER, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)

                # 3. Gelöschte Notizen überspringen
                if data.get('isTrashed', False):
                    print(f"Übersprungen (Papierkorb): {filename}")
                    continue

                # Nur Notizen verarbeiten
                if 'textContent' not in data and 'listContent' not in data and 'title' not in data:
                    continue

                title, md_text = json_to_markdown(data, hedgedoc=args.hedgedoc)

                # 1. Dateiname säubern und Kollisionen vermeiden
                safe_title = sanitize_filename(title)
                if safe_title in used_names:
                    used_names[safe_title] += 1
                    safe_title = f"{safe_title}_{used_names[safe_title]}"
                else:
                    used_names[safe_title] = 0

                output_path = os.path.join(OUTPUT_FOLDER, f"{safe_title}.md")
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(md_text)
                print(f"Konvertiert: {filename} -> {safe_title}.md")

            except Exception as e:
                print(f"Fehler bei Datei {filename}: {e}")


if __name__ == "__main__":
    main()

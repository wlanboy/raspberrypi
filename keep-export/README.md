# Keep-Export Python Scripts

Dieses Projekt bietet Tools zum Exportieren und Konvertieren von Google Keep Notizen zu HedgeDoc (oder lokalem Markdown).

## 📋 Scripts Übersicht

### 1. `convert_keep.py`
**Funktion:** Konvertiert Google Keep JSON-Export zu lokalen Markdown-Dateien

**Was es tut:**
- Liest JSON-Dateien aus dem Google Takeout Export (Google Keep Notizen)
- Konvertiert jede Notiz in eine separate `.md` Datei
- Extrahiert und speichert Metadaten (Titel, Erstellungsdatum, Tags/Labels)
- Konvertiert Links/Annotationen in Markdown-Format

**Input:**
- Dateityp: JSON-Dateien aus Google Takeout
- Quellpfad: `~/Downloads/Takeout/GoogleNotizen`

**Output:**
- Dateityp: Markdown-Dateien (`.md`)
- Zielordner: `~/Dokumente/markdown_notes`

**Beispiel Struktur einer konvertierten Notiz:**
```markdown
# Notiz Titel

**Erstellt am:** 2024-01-15 14:30:45
**Tags:** #Arbeit #Wichtig

---

Eigentlicher Notizinhalt hier...

### Links / Quellen
- [Google](https://google.com)
- [GitHub](https://github.com)
```

**Verwendung:**
```bash
uv run convert_keep.py
```

---

### 2. `convert_keep_hedgedoc.py`
**Funktion:** Konvertiert Google Keep JSON zu HedgeDoc-optimiertem Markdown

**Was es anders macht (vs. convert_keep.py):**
- Nutzt HedgeDoc-spezifische Tag-Syntax (`###### tags:`)
- Bessere Formatierung für HedgeDoc-Server
- Robusteres Dateinamen-Cleaning
- Aussagekräftigere Fehlerbehandlung mit Emoji-Icons

**Input:**
- Dateityp: JSON-Dateien aus Google Takeout
- Quellpfad: `~/Downloads/Takeout/GoogleNotizen`

**Output:**
- Dateityp: Markdown-Dateien (`.md`)
- Zielordner: `~/Dokumente/markdown_notes`

**Beispiel Struktur einer HedgeDoc-konvertierten Notiz:**
```markdown
###### tags: `Arbeit` `Wichtig`

# Notiz Titel
> **Erstellt am:** 2024-01-15 14:30

---

Eigentlicher Notizinhalt hier...

---
### Links & Quellen
- [Google](https://google.com)
```

**Verwendung:**
```bash
uv run convert_keep_hedgedoc.py
```

---

### 3. `upload_to_hedgedoc.py`
**Funktion:** Lädt Markdown-Dateien in einen HedgeDoc-Server hoch und erstellt schöne Aliases

**Was es tut:**
- Liest alle `.md` Dateien aus einem lokalen Ordner
- Konvertiert Dateinamen in schöne Aliases (`Meine Notiz 2024.md` → `meine-notiz-2024`)
- Behandelt Umlaute intelligent (ä→ae, ö→oe, ü→ue, ß→ss)
- Lädt jede Datei in den HedgeDoc-Server hoch
- Tracking hochgeladener Dateien (verhindert Duplikate)
- Verwaltet Rate-Limiting (Delay zwischen Uploads)

**Konfiguration:**
```python
SOURCE_MD_FOLDER = '~/Dokumente/markdown_notes'  # Quellordner mit .md Dateien
HEDGEDOC_URL = 'http://gmk.lan:3000'            # HedgeDoc-Server URL
DELAY_BETWEEN_UPLOADS = 1.5                      # Sekunden Pause zwischen Uploads
```

**Upload-Tracking:**
- Erstellt `.upload_history.txt` im Quellordner
- Verhindert Duplikat-Uploads bereits hochgeladener Dateien
- Manuelle Anpassung möglich durch Ändern der History-Datei

**Fehlerverwaltung:**
- Status Code 200/302: ✅ Erfolgreich hochgeladen
- Status Code 403: ❌ Aliases deaktiviert (Gastmodus)
- Status Code 429: ⏳ Rate Limit → 15s Pause, dann Retry
- Andere Fehler: Ignoriert, geht zum nächsten Script

**Verwendung:**
```bash
uv run upload_to_hedgedoc.py
```

**Beispiel Output:**
```
🚀 Starte Alias-Import für 43 Dateien...
⏩ Überspringe: Alte_Notiz.md
✅ Alias erstellt: meine-neue-notiz -> http://gmk.lan:3000/lxgf2b5tqy
✅ Alias erstellt: projekt-planung -> http://gmk.lan:3000/9k3xc8q2wz
⏳ Rate Limit. Pause 15s...
```

---

## 🔄 Workflow Beispiel

Kompletter Prozess zum Migrieren von Google Keep zu HedgeDoc:

```bash
# 1. Google Takeout Export von Keep runterladen
# 2. Exportdatei in ~/Downloads/Takeout/GoogleNotizen entpacken

# 3. In Markdown konvertieren
uv run convert_keep_hedgedoc.py

# 4. Dateien in HedgeDoc hochladen
uv run upload_to_hedgedoc.py

# 5. Überprüfen der hochgeladenen Notizen auf HedgeDoc Server
# http://gmk.lan:3000
```

---

## 📦 Abhängigkeiten

```
requests   # HTTP-Anfragen für HedgeDoc Upload
```

Installieren mit:
```bash
pip install requests
```

---

## ⚙️ Konfiguration anpassen

Alle Pfade können in den Scripten angepasst werden:

**convert_keep.py:**
```python
SOURCE_FOLDER = os.path.expanduser('~/Custom/Path/ToKeep')
OUTPUT_FOLDER = os.path.expanduser('~/Custom/Output/Path')
```

**convert_keep_hedgedoc.py:**
```python
SOURCE_FOLDER = os.path.expanduser('~/Custom/Path/ToKeep')
OUTPUT_FOLDER = os.path.expanduser('~/Custom/Output/Path')
```

**upload_to_hedgedoc.py:**
```python
SOURCE_MD_FOLDER = os.path.expanduser('~/Custom/Markdown/Path')
HEDGEDOC_URL = 'http://your-hedgedoc-server:port'
DELAY_BETWEEN_UPLOADS = 2.0  # Sekunden
```

---

## 🐛 Häufige Probleme

| Problem | Lösung |
|---------|--------|
| "Quellordner nicht gefunden" | Pfad in `SOURCE_FOLDER` überprüfen |
| Rate Limit Fehler | `DELAY_BETWEEN_UPLOADS` erhöhen |
| Aliases funktionieren nicht (403 Fehler) | HedgeDoc im Gastmodus: Aliases sind deaktiviert |
| Doppelte Uploads | `.upload_history.txt` löschen um neu zu starten |
| Encoding Fehler bei Umlauten | Os/Python UTF-8 Encoding überprüfen |

---

## 📝 Lizenz

Siehe [LICENSE](../LICENSE)

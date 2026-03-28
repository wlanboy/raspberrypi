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

### 4. `server.py`

**Funktion:** FastAPI Web-Server zum Anzeigen und Durchsuchen von Markdown-Notizen

**Was es tut:**

- Startet einen lokalen Web-Server (FastAPI + Uvicorn)
- Zeigt alle Markdown-Dateien in einer Web-Oberfläche an
- Bietet Such- und Filterfunktion nach Titel und Inhalt
- Extrahiert Metadaten (Titel, Erstellungsdatum, Tags)
- Paginierung der Notizenliste (20 pro Seite)

**Features:**

- 📝 **Notizenliste:** Alle konvertierten Notizen werden mit Vorschau angezeigt
- 🔍 **Suchfunktion:** Live-Suche in Titel und Inhalt
- 🏷️ **Tags:** Zeigt alle Tags/Labels einer Notiz
- 📅 **Datum:** Zeigt Erstellungsdatum sortiert nach neustem zuerst
- 📄 **Preview:** 250 Zeichen Vorschau des Notizinhalts

**Konfiguration:**

```python
NOTES_DIR = os.path.expanduser('~/Dokumente/markdown_notes')  # Quellordner
# Server läuft auf Port 8000
# Öffentlich erreichbar: http://0.0.0.0:8000
```

**API Endpoints:**

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/` | GET | HTML-Webseite mit Index |
| `/api/notes` | GET | Notizen-API mit Suche, Pagination |
| `/static/*` | GET | Statische Dateien (CSS, JS) |

**Query Parameter für `/api/notes`:**

- `q` (optional): Suchstring (durchsucht Titel und Inhalt)
- `page` (optional): Seitennummer, default: 1
- `limit` (optional): Notizen pro Seite, default: 20

**Beispiel API Calls:**

```bash
# Alle Notizen (Seite 1)
curl http://localhost:8000/api/notes

# Suche nach "Projekt"
curl http://localhost:8000/api/notes?q=Projekt

# Seite 2 mit 10 Notizen pro Seite
curl http://localhost:8000/api/notes?page=2&limit=10
```

**Verwendung:**

```bash
# Server starten
uv run server.py

# Server läuft dann unter:
# http://localhost:8000
```

**Abhängigkeiten für Server:**

```txt
fastapi      # Web Framework
uvicorn      # ASGI Server
jinja2       # Template Engine
```

Installation:

```bash
pip install fastapi uvicorn jinja2
```

**Beispiel Response von `/api/notes`:**

```json
[
  {
    "filename": "Meine-Notiz.md",
    "title": "Meine Notiz",
    "date": "2024-01-15T14:30:00",
    "date_str": "2024-01-15 14:30",
    "tags": ["Arbeit", "Wichtig"],
    "preview": "Dies ist der Anfang meiner Notiz mit bis zu 250 Zeichen...",
    "full_content": "... kompletter Inhalt ..."
  }
]
```

---

## 🔄 Workflow Beispiel

Kompletter Prozess zum Migrieren von Google Keep zu HedgeDoc mit Web-Interface:

```bash
# 1. Google Takeout Export von Keep runterladen
# 2. Exportdatei in ~/Downloads/Takeout/GoogleNotizen entpacken

# 3. In Markdown konvertieren
uv run convert_keep_hedgedoc.py

# 4. Optional: Web-Server starten zum Durchsuchen der Notizen
uv run server.py
# Öffne dann: http://localhost:8000

# 5. Dateien in HedgeDoc hochladen
uv run upload_to_hedgedoc.py

# 6. Überprüfen der hochgeladenen Notizen auf HedgeDoc Server
# http://gmk.lan:3000
```

---

## 🎯 Welches Script für welchen Use-Case?

| Use-Case | Script(s) |
|----------|-----------|
| Nur lokale Markdown-Dateien aus Keep | `convert_keep.py` oder `convert_keep_hedgedoc.py` |
| Google Keep → Lokale Archive | `convert_keep_hedgedoc.py` |
| Notizen durchsuchen & anschauen | `server.py` (nach convert) |
| Google Keep → HedgeDoc Server | `convert_keep_hedgedoc.py` → `upload_to_hedgedoc.py` |
| Komplette Migration mit Web-Interface | Alle 4 Scripts in Reihenfolge |

---

## 📦 Abhängigkeiten

```txt
requests   # HTTP-Anfragen für HedgeDoc Upload
fastapi    # Web Framework für Server
uvicorn    # ASGI Server für FastAPI
jinja2     # Template Engine für Server
```

Installieren mit:

```bash
pip install requests fastapi uvicorn jinja2
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

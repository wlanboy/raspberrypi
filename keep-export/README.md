# Keep Export

Tools zum Konvertieren von Google Keep Notizen (via Google Takeout) in Markdown-Dateien — entweder lokal oder für den Upload auf einen selbst gehosteten HedgeDoc-Server.

## Scripts

### `convert_keep.py`

Konvertiert Google Keep JSON-Export zu lokalen Markdown-Dateien.

- Input: JSON-Dateien aus Google Takeout (`~/Downloads/Takeout/GoogleNotizen`)
- Output: Markdown-Dateien in `~/Dokumente/markdown_notes`

```bash
uv sync
uv lock --upgrade
uv run pyright
uv run ruff check
uv run convert_keep.py
```

Beispiel Ausgabe:

```markdown
# Notiz Titel

**Erstellt am:** 2024-01-15 14:30:45

---

Eigentlicher Notizinhalt hier...

### Links / Quellen

- [Google](https://google.com)
- [GitHub](https://github.com)
```

---

### `convert_keep_hedgedoc.py`

Wie `convert_keep.py`, aber mit HedgeDoc-optimierter Ausgabe:

- HedgeDoc-spezifische Tag-Syntax (`###### tags:`)
- Robusteres Dateinamen-Cleaning
- Aussagekräftigere Fehlerbehandlung

```bash
uv run convert_keep_hedgedoc.py
```

Beispiel Ausgabe:

```markdown
###### tags: `Arbeit` `Wichtig`

# Notiz Titel

> **Erstellt am:** 2024-01-15 14:30

---

Eigentlicher Notizinhalt hier...
```

---

### `upload_to_hedgedoc.py`

Lädt konvertierte Markdown-Dateien in einen HedgeDoc-Server hoch und erstellt URL-Aliases.

- Konvertiert Dateinamen in Aliases (`Meine Notiz 2024.md` → `meine-notiz-2024`)
- Behandelt Umlaute (ä→ae, ö→oe, ü→ue, ß→ss)
- Verhindert Duplikate via `.upload_history.txt`
- Verwaltet Rate-Limiting automatisch

Konfiguration:

```python
SOURCE_MD_FOLDER = '~/Dokumente/markdown_notes'  # Quellordner
HEDGEDOC_URL = 'http://gmk.lan:3000'             # HedgeDoc-Server URL
DELAY_BETWEEN_UPLOADS = 1.5                       # Sekunden zwischen Uploads
```

| Code | Bedeutung |
| ---- | --------- |
| 200/302 | Erfolgreich hochgeladen |
| 403 | Aliases deaktiviert (Gastmodus) |
| 429 | Rate Limit — 15s Pause, dann Retry |

```bash
uv run upload_to_hedgedoc.py
```

---

### `server.py`

FastAPI Web-Server zum Anzeigen und Durchsuchen der konvertierten Notizen.

- Listet alle Markdown-Dateien mit Vorschau (250 Zeichen)
- Live-Suche in Titel und Inhalt
- Paginierung (20 Notizen pro Seite)
- Sortierung nach Erstellungsdatum

Konfiguration:

```python
NOTES_DIR = os.path.expanduser('~/Dokumente/markdown_notes')
# Server läuft auf Port 8000
```

API Endpoints:

| Endpoint | Methode | Beschreibung |
| -------- | ------- | ------------ |
| `/` | GET | HTML-Webseite mit Notizenliste |
| `/api/notes` | GET | JSON-API mit Suche und Pagination |
| `/static/*` | GET | Statische Dateien (CSS, JS) |

Query-Parameter für `/api/notes`: `q` (Suchstring), `page` (default: 1), `limit` (default: 20)

```bash
uv run server.py
# http://localhost:8000
```

---

## Workflow

```bash
# 1. Google Takeout Export herunterladen und entpacken nach:
#    ~/Downloads/Takeout/GoogleNotizen

# 2. Notizen in Markdown konvertieren
uv run convert_keep_hedgedoc.py

# 3. Optional: Notizen lokal durchsuchen
uv run server.py

# 4. Auf HedgeDoc hochladen
uv run upload_to_hedgedoc.py
```

## Use-Case Übersicht

| Use-Case | Script(s) |
| -------- | --------- |
| Lokale Markdown-Archivierung | `convert_keep.py` |
| HedgeDoc-optimierte Konvertierung | `convert_keep_hedgedoc.py` |
| Notizen im Browser durchsuchen | `server.py` |
| Komplette Migration zu HedgeDoc | `convert_keep_hedgedoc.py` + `upload_to_hedgedoc.py` |

## Abhängigkeiten

```bash
uv sync
```

```txt
requests   # HTTP-Anfragen für HedgeDoc Upload
fastapi    # Web Framework für Server
uvicorn    # ASGI Server für FastAPI
jinja2     # Template Engine für Server
```

## Häufige Probleme

| Problem | Lösung |
| ------- | ------ |
| "Quellordner nicht gefunden" | Pfad in `SOURCE_FOLDER` überprüfen |
| Rate Limit Fehler | `DELAY_BETWEEN_UPLOADS` erhöhen |
| 403 bei Upload | HedgeDoc im Gastmodus — Aliases deaktiviert |
| Doppelte Uploads | `.upload_history.txt` löschen |
| Encoding-Fehler bei Umlauten | Python UTF-8 Encoding überprüfen |

## Lizenz

Siehe [LICENSE](../LICENSE)

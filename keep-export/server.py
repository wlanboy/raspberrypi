import os
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime

app = FastAPI()

NOTES_DIR = os.path.expanduser('~/Dokumente/markdown_notes')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

_cache = {"mtime": None, "notes": []}


def get_note_metadata(filename):
    path = os.path.join(NOTES_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    tags = re.findall(r'`([^`]+)`', re.search(r'###### tags: (.*)', content).group(1)) if re.search(r'###### tags: (.*)', content) else []
    date_match = re.search(r'\*\*Erstellt am:\*\* (.*)', content)
    date_str = date_match.group(1).strip() if date_match else "1970-01-01 00:00"

    dt = datetime.min
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            pass

    title = re.search(r'^# (.*)', content, re.MULTILINE).group(1) if re.search(r'^# (.*)', content, re.MULTILINE) else filename
    clean_text = re.sub(r'###### tags:.*|\*\*Erstellt am:\*\*.*|\*\*Bearbeitet am:\*\*.*|^# .*|^---$', '', content, flags=re.MULTILINE).strip()

    return {
        "filename": filename,
        "title": title,
        "date": dt,
        "date_str": date_str,
        "tags": tags,
        "preview": clean_text[:250] + "..." if len(clean_text) > 250 else clean_text,
        "full_content": content
    }


def get_all_notes():
    mtime = os.path.getmtime(NOTES_DIR)
    if _cache["mtime"] != mtime:
        files = [f for f in os.listdir(NOTES_DIR) if f.endswith('.md')]
        notes = [get_note_metadata(f) for f in files]
        notes.sort(key=lambda x: x['date'], reverse=True)
        _cache["mtime"] = mtime
        _cache["notes"] = notes
    return _cache["notes"]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/notes")
async def api_notes(q: str = "", page: int = 1, limit: int = 20):
    notes = get_all_notes()
    if q:
        q_lower = q.lower()
        notes = [n for n in notes if q_lower in n['title'].lower() or q_lower in n['full_content'].lower()]
    start = (page - 1) * limit
    return notes[start:start + limit]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import urllib.request
import urllib.error
import json
import ssl
import os
import sys

# -----------------------------
# Umgebungsvariablen laden
# -----------------------------
GITHUB_USER = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITEA_TOKEN = os.getenv("GITEA_TOKEN")

if not GITHUB_USER or not GITHUB_TOKEN or not GITEA_TOKEN:
    print("❌ Fehler: Umgebungsvariablen GITHUB_USERNAME, GITHUB_TOKEN und GITEA_TOKEN prüfen!")
    sys.exit(1)

# -----------------------------
# Konfiguration
# -----------------------------
TOPIC_FILTER = "mirror"
GITEA_URL = "https://git.gmk.lan:3300"
GITEA_ORG = "github"
MIRROR_INTERVAL = "8h0m0s"

ssl_ctx = ssl._create_unverified_context()

# -----------------------------
# Zentralisierte HTTP Funktion (mit Header-Auth)
# -----------------------------
def http_request(url, data=None, headers=None, method="GET"):
    all_headers = headers or {}
    
    # Gitea Header-Authentifizierung (Moderner Weg)
    if GITEA_URL in url:
        all_headers["Authorization"] = f"token {GITEA_TOKEN}"
    
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=all_headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ssl_ctx) as resp:
            return resp.read().decode("utf-8"), resp.getcode()
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8"), e.code
    except Exception as e:
        return str(e), 500

# -----------------------------
# API Funktionen
# -----------------------------
def get_github_repos():
    repos = []
    page = 1
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
    }
    while True:
        url = f"https://api.github.com/user/repos?page={page}&per_page=100&type=owner"
        text, status = http_request(url, headers=headers)
        if status != 200:
            raise Exception(f"GitHub Fehler: {status} {text}")
        data = json.loads(text)
        if not data: break
        repos.extend(data)
        page += 1
    return repos

def get_gitea_repos():
    url = f"{GITEA_URL}/api/v1/orgs/{GITEA_ORG}/repos"
    text, status = http_request(url)
    return json.loads(text) if status == 200 else []

def delete_gitea_repo(repo_name):
    url = f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{repo_name}"
    _, status = http_request(url, method="DELETE")
    return status == 204

def gitea_repo_exists(repo_name):
    url = f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{repo_name}"
    _, status = http_request(url)
    return status == 200

def create_gitea_mirror(repo_url, repo_name):
    url = f"{GITEA_URL}/api/v1/repos/migrate"
    
    # Auth in die URL einbetten für Git-Prozess (behebt 422 Terminal Prompt Fehler)
    authenticated_clone_url = repo_url.replace("https://", f"https://{GITHUB_USER}:{GITHUB_TOKEN}@")

    payload = {
        "clone_addr": authenticated_clone_url,
        "repo_name": repo_name,
        "repo_owner": GITEA_ORG,
        "mirror": True,
        "mirror_interval": MIRROR_INTERVAL,
        "private": False,
        "service": "git",
        "lfs": False,
        "wiki": False
    }

    headers = {"Content-Type": "application/json"}
    text, status = http_request(url, data=payload, headers=headers, method="POST")

    if status == 201:
        print(f"✔ Spiegel erstellt: {repo_name}")
    else:
        print(f"❌ Fehler bei {repo_name}: {status}")
        print(f"Antwort: {text}")

# -----------------------------
# Hauptprogramm
# -----------------------------
def main():
    print("🚀 Starte Mirror-Sync...")
    
    # 1. Gitea Clean-up
    answer = input("❓ Alle Repos in Gitea-Org löschen? (ja/[nein]): ").strip().lower()
    if answer == "": 
        answer = "nein"
    
    if answer == "ja":
        for r in get_gitea_repos():
            print(f"🗑 Lösche {r['name']}...")
            delete_gitea_repo(r['name'])

    # 2. GitHub Repos abrufen
    gh_repos = get_github_repos()
    
    for repo in gh_repos:
        name = repo["name"]
        if TOPIC_FILTER not in repo.get("topics", []):
            continue

        if gitea_repo_exists(name):
            print(f"⏭ Überspringe {name} (existiert bereits)")
            continue

        print(f"➕ Erstelle Mirror für {name} (Private: {repo['private']})...")
        print(repo["clone_url"])
        create_gitea_mirror(repo["clone_url"], name)

if __name__ == "__main__":
    main()

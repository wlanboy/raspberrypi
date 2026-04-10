import urllib.request
import urllib.error
import json
import ssl
import os
import sys
import subprocess

# -----------------------------
# Umgebungsvariablen laden
# -----------------------------
GITEA_TOKEN = os.getenv("GITEA_TOKEN")

if not GITEA_TOKEN:
    print("❌ Fehler: Umgebungsvariable GITEA_TOKEN prüfen!")
    sys.exit(1)

# -----------------------------
# Konfiguration
# -----------------------------
GITEA_URL = "https://git.gmk.lan:3300"
GITEA_ORG_REF = "github"
GITEA_ORG = "local"
LOCAL_BASE = sys.argv[1] if len(sys.argv) > 1 else "/mnt/z/github"

ssl_ctx = ssl._create_unverified_context()

# -----------------------------
# HTTP Funktion
# -----------------------------
def http_request(url, data=None, headers=None, method="GET"):
    all_headers = headers or {}
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
def gitea_repo_exists(org, repo_name):
    url = f"{GITEA_URL}/api/v1/repos/{org}/{repo_name}"
    _, status = http_request(url)
    return status == 200

def create_gitea_repo(repo_name):
    url = f"{GITEA_URL}/api/v1/orgs/{GITEA_ORG}/repos"
    payload = {
        "name": repo_name,
        "private": False,
        "auto_init": False,
    }
    headers = {"Content-Type": "application/json"}
    text, status = http_request(url, data=payload, headers=headers, method="POST")
    if status == 201:
        return True
    print(f"  ❌ Repo anlegen fehlgeschlagen: {status} {text}")
    return False

def push_repo(local_path, repo_name):
    remote_url = f"https://oauth2:{GITEA_TOKEN}@git.gmk.lan:3300/{GITEA_ORG}/{repo_name}.git"
    env = {**os.environ, "GIT_SSL_NO_VERIFY": "true"}

    # Temporären Remote setzen (überschreibt nicht dauerhaft)
    result = subprocess.run(
        ["git", "push", remote_url, "--all", "--force"],
        cwd=local_path,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print(f"  ❌ Push fehlgeschlagen:\n{result.stderr.strip()}")
        return False

    # Tags auch pushen
    subprocess.run(
        ["git", "push", remote_url, "--tags"],
        cwd=local_path,
        capture_output=True,
        text=True,
        env=env,
    )
    return True

# -----------------------------
# Hauptprogramm
# -----------------------------
def main():
    print(f"🚀 Lokale Repos aus {LOCAL_BASE} nach Gitea ({GITEA_ORG}) pushen...\n")

    if not os.path.isdir(LOCAL_BASE):
        print(f"❌ Verzeichnis nicht gefunden: {LOCAL_BASE}")
        sys.exit(1)

    entries = sorted(os.listdir(LOCAL_BASE))
    pushed = 0
    skipped = 0
    errors = 0

    for name in entries:
        local_path = os.path.join(LOCAL_BASE, name)

        # Nur echte Git-Repos
        if not os.path.isdir(os.path.join(local_path, ".git")):
            continue

        if gitea_repo_exists(GITEA_ORG, name):
            print(f"⏭ Überspringe {name} (existiert bereits in {GITEA_ORG})")
            skipped += 1
            continue

        if gitea_repo_exists(GITEA_ORG_REF, name):
            print(f"⏭ Überspringe {name} (existiert bereits in {GITEA_ORG_REF})")
            skipped += 1
            continue

        print(f"➕ {name}")
        if not create_gitea_repo(name):
            errors += 1
            continue

        if push_repo(local_path, name):
            print(f"  ✔ Gepusht")
            pushed += 1
        else:
            errors += 1

    print(f"\n📊 Fertig: {pushed} gepusht, {skipped} übersprungen, {errors} Fehler")

if __name__ == "__main__":
    main()

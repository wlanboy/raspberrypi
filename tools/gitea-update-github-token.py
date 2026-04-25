import urllib.request
import urllib.error
import json
import ssl
import os
import sys

GITHUB_USER = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_GITEA_TOKEN")
GITEA_TOKEN = os.getenv("GITEA_TOKEN")

if not GITHUB_USER or not GITHUB_TOKEN or not GITEA_TOKEN:
    print("❌ Fehler: Umgebungsvariablen GITHUB_USERNAME, GITHUB_GITEA_TOKEN und GITEA_TOKEN prüfen!")
    sys.exit(1)

GITEA_URL = "https://git.gmk.lan:3300"
GITEA_ORG = "github"
MIRROR_INTERVAL = "8h0m0s"

ssl_ctx = ssl._create_unverified_context()

def http_request(url, data=None, headers=None, method="GET"):
    all_headers = headers or {}
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

def get_gitea_mirror_repos():
    repos = []
    page = 1
    while True:
        url = f"{GITEA_URL}/api/v1/orgs/{GITEA_ORG}/repos?page={page}&limit=100"
        text, status = http_request(url)
        if status != 200:
            break
        data = json.loads(text)
        if not data:
            break
        repos.extend([r for r in data if r.get("mirror")])
        page += 1
    return repos

def delete_gitea_repo(repo_name):
    url = f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{repo_name}"
    _, status = http_request(url, method="DELETE")
    return status == 204

def create_gitea_mirror(repo_name, original_url):
    url = f"{GITEA_URL}/api/v1/repos/migrate"
    authenticated_url = original_url.replace("https://", f"https://{GITHUB_USER}:{GITHUB_TOKEN}@")
    payload = {
        "clone_addr": authenticated_url,
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
    return status == 201, text

def main():
    print("🔑 GitHub-Token-Update für Gitea-Mirrors...")

    mirror_repos = get_gitea_mirror_repos()

    if not mirror_repos:
        print("Keine Mirror-Repos gefunden.")
        return

    print(f"📋 {len(mirror_repos)} Mirror-Repos in Org '{GITEA_ORG}' gefunden\n")

    answer = input(f"❓ Token für alle {len(mirror_repos)} Repos aktualisieren? (ja/[nein]): ").strip().lower()
    if answer != "ja":
        print("Abgebrochen.")
        return

    updated = 0
    failed = 0

    for repo in mirror_repos:
        name = repo["name"]
        original_url = repo.get("original_url") or f"https://github.com/{GITHUB_USER}/{name}.git"
        print(f"🔄 {name}...", end=" ", flush=True)

        if not delete_gitea_repo(name):
            print("❌ Löschen fehlgeschlagen")
            failed += 1
            continue

        ok, text = create_gitea_mirror(name, original_url)
        if ok:
            print("✔")
            updated += 1
        else:
            print(f"❌ Neu erstellen fehlgeschlagen: {text}")
            failed += 1

    print(f"\n📊 Zusammenfassung:")
    print(f"   Aktualisiert:   {updated}")
    print(f"   Fehlgeschlagen: {failed}")

if __name__ == "__main__":
    main()

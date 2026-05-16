#!/usr/bin/env python3

import getpass
import json
import os
import re
import ssl
import sys
from urllib.request import Request, urlopen

# --- KONFIGURATION ---
GITEA_URL = "https://git.gmk.lan:3300"
GITEA_ORG = "github"

GITEA_TOKEN = os.environ.get("GITEA_TOKEN") or input("Gitea Token: ").strip()
GH_USER = os.environ.get("GITHUB_USERNAME") or input("GitHub Username: ").strip()
GH_PAT = getpass.getpass("GitHub Token: ")

# --- SCRIPT-START ---

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE  # selbstsigniertes Zertifikat

API_HEADERS = {
    "Authorization": f"token {GITEA_TOKEN}",
    "Content-Type": "application/json",
}


def api(method, path, body=None):
    from urllib.error import HTTPError, URLError
    url = f"{GITEA_URL}/api/v1{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, headers=API_HEADERS, method=method)
    try:
        with urlopen(req, context=ctx) as resp:
            return resp.status, resp.read().decode()
    except HTTPError as e:
        return e.code, e.read().decode()
    except URLError as e:
        print(f"  [FEHLER] Verbindung zu {GITEA_URL} fehlgeschlagen: {e.reason}")
        sys.exit(1)


def failed_repos_from_notices():
    """Liest alle Seiten der Admin-Notices und gibt Repos mit fehlgeschlagenem Sync zurück."""
    repos = set()
    page = 1
    td_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
    repo_pattern = re.compile(r"[Rr]epository\s+'([^/]+/[^']+)'\s+failed", re.IGNORECASE)
    tag_pattern = re.compile(r"<[^>]+>")

    while True:
        from urllib.error import HTTPError, URLError
        req = Request(
            f"{GITEA_URL}/-/admin/notices?page={page}",
            headers={"Authorization": f"token {GITEA_TOKEN}"},
        )
        try:
            with urlopen(req, context=ctx) as resp:
                html = resp.read().decode()
        except HTTPError as e:
            print(f"  [FEHLER] Admin-Notices nicht abrufbar (HTTP {e.code}).")
            sys.exit(1)
        except URLError as e:
            print(f"  [FEHLER] Verbindung zu {GITEA_URL} fehlgeschlagen: {e.reason}")
            sys.exit(1)

        found_on_page = 0
        for cell in td_pattern.findall(html):
            text = tag_pattern.sub("", cell).strip()
            m = repo_pattern.search(text)
            if m:
                repos.add(m.group(1))
                found_on_page += 1

        if found_on_page == 0 or f'page={page + 1}' not in html:
            break
        page += 1

    return repos


print("--- Lese fehlgeschlagene Syncs aus Admin-Notices ---")
all_failed = failed_repos_from_notices()

# Nur Repos der konfigurierten Organisation berücksichtigen
failed_repos = [r.split("/")[1] for r in all_failed if r.startswith(f"{GITEA_ORG}/")]

if not failed_repos:
    print("Keine fehlgeschlagenen Syncs für die Organisation gefunden.")
    sys.exit(0)

print(f"Gefundene Repos mit fehlgeschlagenem Sync: {', '.join(failed_repos)}")
print("-----------------------------------------------")

for repo in failed_repos:
    print(f"Bearbeite Repo: {repo}...")

    status, body = api(
        "PATCH",
        f"/repos/{GITEA_ORG}/{repo}/push_mirrors",
        {"remote_address": f"https://{GH_USER}:{GH_PAT}@github.com/{GH_USER}/{repo}.git"},
    )

    if status == 200 and "remote_address" in body:
        print("  [OK] Credentials aktualisiert.")
        sync_status, _ = api("POST", f"/repos/{GITEA_ORG}/{repo}/mirror-sync")
        if sync_status in (200, 204):
            print("  [OK] Sync-Vorgang gestartet.")
        else:
            print(f"  [WARNUNG] Sync-Start fehlgeschlagen (HTTP {sync_status}).")
    else:
        print(f"  [FEHLER] Konnte Credentials für {repo} nicht aktualisieren.")
        print(f"  Antwort: {body}")

    print("-----------------------------------------------")

print("Fertig!")

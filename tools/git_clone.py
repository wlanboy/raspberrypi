import json
import os
import subprocess
import sys

BASE_DIR = os.path.expanduser("~/github")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
PRIVATE_DIR = os.path.join(BASE_DIR, "private")


def ensure_dirs():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    os.makedirs(PRIVATE_DIR, exist_ok=True)


def get_all_repos():
    result = subprocess.run(
        [
            "gh", "repo", "list",
            "--json", "name,isPrivate,url",
            "--limit", "1000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ gh repo list fehlgeschlagen: {result.stderr.strip()}")
        sys.exit(1)
    return json.loads(result.stdout)


def clone_repo(repo, target_dir):
    name = repo["name"]
    dest = os.path.join(target_dir, name)

    if os.path.isdir(dest):
        print(f"⏭️  {name} existiert bereits – wird übersprungen")
        return "skipped"

    clone_url = repo["url"]
    print(f"📥 Klone {name} → {dest}")
    result = subprocess.run(
        ["git", "clone", clone_url, dest],
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Fehler beim Klonen von {name}: {result.stderr.strip()}")
        return "error"
    return "cloned"


def main():
    ensure_dirs()

    print("🔍 Lade Repository-Liste via gh CLI...")
    repos = get_all_repos()
    print(f"   {len(repos)} Repos gefunden\n")

    stats = {"cloned": 0, "skipped": 0, "error": 0}

    for repo in repos:
        target = PRIVATE_DIR if repo["isPrivate"] else PUBLIC_DIR
        status = clone_repo(repo, target)
        stats[status] += 1

    print("\n📊 Zusammenfassung:")
    print(f"   Geklont:       {stats['cloned']}")
    print(f"   Übersprungen:  {stats['skipped']}")
    print(f"   Fehler:        {stats['error']}")
    print("\n📁 Zielordner:")
    print(f"   Public:  {PUBLIC_DIR}")
    print(f"   Private: {PRIVATE_DIR}")


if __name__ == "__main__":
    main()

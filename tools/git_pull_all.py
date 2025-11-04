import os
import subprocess
import argparse

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def has_remote(path):
    try:
        result = subprocess.run(
            ["git", "-C", path, "remote"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False

def git_pull_in_subfolders(base_dir="."):
    for folder in os.listdir(base_dir):
        full_path = os.path.join(base_dir, folder)

        if not os.path.isdir(full_path):
            print(f"🔸 {folder} ist keine Verzeichnis – wird übersprungen")
            continue

        if not is_git_repo(full_path):
            print(f"⏭️  {folder} ist kein Git-Repository (kein .git-Ordner)")
            continue

        if not has_remote(full_path):
            print(f"⏭️  {folder} hat kein Remote konfiguriert – wird übersprungen")
            continue

        print(f"📂 Pulling in {folder}")
        try:
            subprocess.run(["git", "-C", full_path, "pull"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Fehler beim Pull in {folder}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Führe git pull in allen Git-Repos mit Remote eines Verzeichnisses aus.")
    parser.add_argument("basedir", nargs="?", default=".", help="Pfad zum Basisverzeichnis (optional, Standard: aktuelles Verzeichnis)")
    args = parser.parse_args()

    git_pull_in_subfolders(args.basedir)

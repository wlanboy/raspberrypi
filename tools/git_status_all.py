import os
import subprocess
import argparse

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def git_status_in_subfolders(base_dir="."):
    for folder in sorted(os.listdir(base_dir)):
        full_path = os.path.join(base_dir, folder)

        if not os.path.isdir(full_path):
            continue

        if not is_git_repo(full_path):
            continue

        result = subprocess.run(
            ["git", "-C", full_path, "status", "--short"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )

        branch_result = subprocess.run(
            ["git", "-C", full_path, "branch", "--show-current"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )
        branch = branch_result.stdout.strip()

        output = result.stdout.strip()
        if output:
            print(f"📂 {folder} [{branch}] – Änderungen:")
            for line in output.splitlines():
                print(f"   {line}")
        else:
            print(f"✅ {folder} [{branch}] – sauber")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zeige git status für alle Git-Repos in einem Verzeichnis.")
    parser.add_argument("basedir", nargs="?", default=".", help="Pfad zum Basisverzeichnis (optional, Standard: aktuelles Verzeichnis)")
    args = parser.parse_args()

    git_status_in_subfolders(args.basedir)

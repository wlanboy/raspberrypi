import os
import subprocess
import argparse

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def get_git_info(path):
    try:
        # Aktueller Branch
        branch = subprocess.check_output(
            ["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
            text=True
        ).strip()

        # Remote-URLs
        remotes = subprocess.check_output(
            ["git", "-C", path, "remote", "-v"],
            text=True
        ).strip().splitlines()

        remote_urls = set()
        for line in remotes:
            parts = line.split()
            if len(parts) >= 2:
                remote_urls.add(parts[1])

        return branch, list(remote_urls)
    except subprocess.CalledProcessError:
        return None, []

def scan_git_repos(base_dir):
    print(f"\n🔍 Scanning Git repositories in: {os.path.abspath(base_dir)}\n")
    for folder in os.listdir(base_dir):
        full_path = os.path.join(base_dir, folder)
        if os.path.isdir(full_path) and is_git_repo(full_path):
            branch, remotes = get_git_info(full_path)
            print(f"📁 {folder}")
            print(f"   🌿 Branch: {branch if branch else 'Unbekannt'}")
            if remotes:
                for url in remotes:
                    print(f"   🔗 Remote: {url}")
            else:
                print("   🔗 Kein Remote konfiguriert")
            print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scannt Git-Repositories in einem Verzeichnis.")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.path.expanduser("~"),
        help="Pfad zum Verzeichnis (optional, Standard: Home-Verzeichnis)"
    )
    args = parser.parse_args()
    scan_git_repos(args.path)

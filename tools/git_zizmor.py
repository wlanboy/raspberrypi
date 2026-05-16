import os
import subprocess
import argparse

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def has_workflows(path):
    return os.path.isdir(os.path.join(path, ".github", "workflows"))

def run_zizmor(path, gh_token=None, fmt=None, no_blanket=False):
    cmd = ["uvx", "zizmor"]
    if gh_token:
        cmd += [f"--gh-token={gh_token}"]
    if fmt:
        cmd += [f"--format={fmt}"]
    if no_blanket:
        cmd += ["--persona=regular"]
    cmd.append(".")
    try:
        result = subprocess.run(
            cmd,
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return result.returncode, result.stdout
    except FileNotFoundError:
        return -1, "❌ 'uvx' nicht gefunden – bitte uv installieren (https://github.com/astral-sh/uv)"

def audit_repos(base_dir=".", gh_token=None, fmt=None, no_blanket=False):
    for folder in os.listdir(base_dir):
        full_path = os.path.join(base_dir, folder)

        if not os.path.isdir(full_path):
            continue

        if not is_git_repo(full_path):
            print(f"⏭️  {folder} ist kein Git-Repository – wird übersprungen")
            continue

        if not has_workflows(full_path):
            print(f"⏭️  {folder} hat keine GitHub Actions Workflows – wird übersprungen")
            continue

        print(f"🔍 Prüfe Workflows in {folder} ...")
        returncode, output = run_zizmor(full_path, gh_token=gh_token, fmt=fmt, no_blanket=no_blanket)

        if output.strip():
            print(output.strip())

        if returncode == 0:
            print(f"✅ {folder}: keine Probleme gefunden")
        elif returncode == 1:
            print(f"⚠️  {folder}: Probleme gefunden (siehe oben)")
        else:
            print(f"❌ {folder}: Fehler beim Ausführen von zizmor (exit {returncode})")

        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Führe zizmor (GitHub Actions Security Audit) in allen Git-Repos eines Verzeichnisses aus."
    )
    parser.add_argument(
        "basedir",
        nargs="?",
        default=".",
        help="Pfad zum Basisverzeichnis (optional, Standard: aktuelles Verzeichnis)"
    )
    parser.add_argument(
        "--gh-token",
        metavar="TOKEN",
        help="GitHub Token für erweiterte Online-Checks (z.B. Impostor-Commits, bekannte CVEs)"
    )
    parser.add_argument(
        "--format",
        choices=["sarif", "json"],
        dest="fmt",
        help="Ausgabeformat (sarif oder json, Standard: menschenlesbar)"
    )
    parser.add_argument(
        "-b",
        action="store_true",
        dest="no_blanket",
        help="Unterdrückt 'required by blanket policy' Findings (erzwingt --persona=regular)"
    )
    args = parser.parse_args()

    audit_repos(args.basedir, gh_token=args.gh_token, fmt=args.fmt, no_blanket=args.no_blanket)

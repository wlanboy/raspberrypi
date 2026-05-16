import os
import re
import subprocess
import argparse
import urllib.request
import urllib.error
import json
from pathlib import Path
from collections import defaultdict

ACTION_PATTERN = re.compile(
    r'(uses:\s+)([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*)@([^\s#\n]+)'
)

def is_git_repo(path):
    return (Path(path) / ".git").is_dir()

def find_workflow_files(base_dir):
    result = []
    for folder in sorted(os.listdir(base_dir)):
        full_path = Path(base_dir) / folder
        if not full_path.is_dir() or not is_git_repo(full_path):
            continue
        workflow_dir = full_path / ".github" / "workflows"
        if not workflow_dir.is_dir():
            continue
        for fname in sorted(os.listdir(workflow_dir)):
            if fname.endswith((".yml", ".yaml")):
                result.append(str(workflow_dir / fname))
    return result

def extract_actions(filepath):
    with open(filepath) as f:
        content = f.read()
    return [(m.group(2), m.group(3)) for m in ACTION_PATTERN.finditer(content)]

def get_latest_version(action, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "git-github-action-update",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{action}/releases/latest"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("tag_name")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return None
    except Exception:
        return None

    # Fallback: tags list
    url = f"https://api.github.com/repos/{action}/tags"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return data[0]["name"]
    except Exception:
        pass
    return None

def major_of(v):
    m = re.match(r"v?(\d+)", v.strip())
    return int(m.group(1)) if m else None

def major_tag_of(v):
    m = re.match(r"(v?)(\d+)", v.strip())
    if not m:
        return v
    prefix = m.group(1) or "v"
    return f"{prefix}{m.group(2)}"

def is_newer_major(latest, current):
    """Only returns True when the major version has increased."""
    if not latest or latest == current:
        return False
    if re.fullmatch(r"[0-9a-f]{40}", current):
        return False
    curr_m = major_of(current)
    lat_m = major_of(latest)
    if curr_m is None or lat_m is None:
        return False
    return lat_m > curr_m


def update_file(filepath, updates):
    with open(filepath) as f:
        content = f.read()
    for action, (old_ver, new_ver) in updates.items():
        # Negative lookahead: don't match @v3 inside @v3.5
        pattern = re.escape(f"{action}@{old_ver}") + r"(?![.\w\-])"
        content = re.sub(pattern, f"{action}@{new_ver}", content)
    with open(filepath, "w") as f:
        f.write(content)

def repo_of(filepath):
    for parent in Path(filepath).parents:
        if (parent / ".git").is_dir():
            return str(parent)
    return None

def git_run(repo, *args):
    subprocess.run(["git", "-C", repo] + list(args), check=True)

def get_gh_token():
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Findet veraltete GitHub Actions und aktualisiert sie."
    )
    parser.add_argument(
        "basedir", nargs="?", default=".", help="Basisverzeichnis (Standard: .)"
    )
    parser.add_argument("--gh-token", metavar="TOKEN", help="GitHub API Token")
    args = parser.parse_args()

    token = args.gh_token or get_gh_token()
    if token:
        print("🔑 GitHub Token gefunden – Online-Checks aktiviert.")
    else:
        print("⚠️  Kein GitHub Token – Rate Limit möglicherweise niedrig.")

    print("\n🔍 Suche nach Workflow-Dateien ...")
    workflow_files = find_workflow_files(args.basedir)
    if not workflow_files:
        print("Keine Workflow-Dateien gefunden.")
        return

    # Collect: action -> set of versions, (action, version) -> files
    action_versions = defaultdict(set)
    usage_map = defaultdict(list)
    for wf in workflow_files:
        for action, version in extract_actions(wf):
            action_versions[action].add(version)
            if wf not in usage_map[(action, version)]:
                usage_map[(action, version)].append(wf)

    print(
        f"✅ {len(workflow_files)} Workflow-Datei(en), "
        f"{len(action_versions)} eindeutige Action(s).\n"
    )

    print("🌐 Prüfe aktuelle Versionen via GitHub API ...")
    latest_versions = {}
    for action in sorted(action_versions):
        latest = get_latest_version(action, token)
        latest_versions[action] = latest
        print(f"   {action}: {latest or '?'}")

    # Determine outdated entries (major version changes only)
    outdated = []
    for (action, cur_ver), files in usage_map.items():
        latest = latest_versions.get(action)
        if is_newer_major(latest, cur_ver):
            new_ver = major_tag_of(latest)
            outdated.append((action, cur_ver, new_ver, files))
    outdated.sort(key=lambda x: x[0])

    print()
    if not outdated:
        print("✅ Alle Actions sind aktuell (keine neuen Major-Versionen).")
        return

    print("━" * 60)
    print("⚠️  Neue Major-Versionen verfügbar:")
    print("━" * 60)
    for i, (action, cur, new, files) in enumerate(outdated, 1):
        file_list = "  ".join(os.path.relpath(f, args.basedir) for f in files)
        print(f"  [{i}] {action}")
        print(f"       {cur} → {new}")
        print(f"       {file_list}")
    print("━" * 60)

    raw = input(
        '\nWelche Actions aktualisieren? '
        '(Nummern kommasepariert, "a" = alle, "n" = keine): '
    ).strip().lower()

    if raw in ("n", "nein", "no", ""):
        print("Abgebrochen.")
        return

    if raw in ("a", "alle", "all"):
        selected = outdated
    else:
        chosen = set()
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(outdated):
                    chosen.add(idx)
                else:
                    print(f"⚠️  Ungültige Nummer: {part} – wird übersprungen")
        selected = [outdated[i] for i in sorted(chosen)]

    if not selected:
        print("Keine Actions ausgewählt.")
        return

    # Group updates by file
    file_updates = defaultdict(dict)
    for action, cur, new, files in selected:
        for f in files:
            file_updates[f][action] = (cur, new)

    print()
    for filepath, updates in sorted(file_updates.items()):
        update_file(filepath, updates)
        rel = os.path.relpath(filepath, args.basedir)
        changes = ", ".join(f"{a}: {v[0]} → {v[1]}" for a, v in updates.items())
        print(f"✅ {rel} ({changes})")

    answer = input("\nSollen die Änderungen committed und gepusht werden? [j/N] ").strip().lower()
    if answer not in ("j", "ja", "y", "yes"):
        print("Änderungen gespeichert, aber nicht committed.")
        return

    # Group modified files by repo
    repo_files = defaultdict(list)
    for filepath in file_updates:
        repo = repo_of(filepath)
        if repo:
            repo_files[repo].append(filepath)

    print()
    for repo in sorted(repo_files):
        repo_name = os.path.basename(repo)
        files = repo_files[repo]
        print(f"📂 {repo_name}")
        try:
            git_run(repo, "pull")
            for f in files:
                git_run(repo, "add", f)
            # Build commit message
            updated = set()
            for f in files:
                for action, (_, new_ver) in file_updates[f].items():
                    updated.add(f"{action}@{new_ver}")
            msg = "Updated GitHub Actions: " + ", ".join(sorted(updated))
            git_run(repo, "commit", "-m", msg)
            git_run(repo, "push")
            print(f"   ✅ Committed und gepusht: {msg}")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Fehler in {repo_name}: {e}")
        print()

if __name__ == "__main__":
    main()

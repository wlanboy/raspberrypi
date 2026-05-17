import os
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

CONCLUSION_STYLE = {
    "success":   ("✅", "\033[32m"),
    "failure":   ("❌", "\033[31m"),
    "cancelled": ("⚠️ ", "\033[33m"),
    "skipped":   ("⏭️ ", "\033[90m"),
    "timed_out": ("⏱️ ", "\033[31m"),
    "stale":     ("🕰️ ", "\033[90m"),
}

STATUS_STYLE = {
    "in_progress": ("🔄", "\033[34m"),
    "queued":      ("⏳", "\033[90m"),
    "waiting":     ("⏳", "\033[90m"),
    "requested":   ("⏳", "\033[90m"),
}

RESET = "\033[0m"

FAILED_CONCLUSIONS = {"failure", "timed_out", "cancelled"}

def is_git_repo(path):
    return (Path(path) / ".git").is_dir()

def find_repos(base_dir):
    result = []
    for folder in sorted(os.listdir(base_dir)):
        full_path = Path(base_dir) / folder
        if full_path.is_dir() and is_git_repo(full_path):
            result.append(full_path)
    return result

def get_repo_is_private(repo_path):
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "isPrivate"],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout).get("isPrivate")
    except Exception:
        return None

def get_online_repos(public_only=False, private_only=False):
    try:
        result = subprocess.run(
            ["gh", "repo", "list", "--limit", "200", "--json", "name,nameWithOwner,isPrivate"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        repos = json.loads(result.stdout)
        if public_only:
            repos = [r for r in repos if not r["isPrivate"]]
        elif private_only:
            repos = [r for r in repos if r["isPrivate"]]
        return repos, None
    except FileNotFoundError:
        return None, "gh CLI nicht gefunden"
    except Exception as e:
        return None, str(e)

def get_latest_runs(repo_path=None, repo_name=None):
    try:
        cmd = [
            "gh", "run", "list",
            "--limit", "100",
            "--json", "workflowName,status,conclusion,event,headBranch,createdAt",
        ]
        if repo_name:
            cmd += ["--repo", repo_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path)
        if result.returncode != 0:
            err = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "unbekannt"
            return None, err
        runs = json.loads(result.stdout)
        seen = {}
        for run in runs:
            wf = run["workflowName"]
            if wf not in seen:
                seen[wf] = run
        return list(seen.values()), None
    except FileNotFoundError:
        return None, "gh CLI nicht gefunden"
    except Exception as e:
        return None, str(e)

def format_age(created_at):
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        diff = datetime.now(timezone.utc) - dt
        days = diff.days
        hours, rem = divmod(diff.seconds, 3600)
        minutes = rem // 60
        if days >= 1:
            return f"{days}d ago"
        if hours >= 1:
            return f"{hours}h ago"
        return f"{minutes}m ago"
    except Exception:
        return "?"

def format_run(run):
    status = run.get("status", "")
    conclusion = run.get("conclusion") or ""

    if status != "completed":
        icon, color = STATUS_STYLE.get(status, ("❓", "\033[0m"))
        label = status
    else:
        icon, color = CONCLUSION_STYLE.get(conclusion, ("❓", "\033[0m"))
        label = conclusion

    age = format_age(run.get("createdAt", ""))
    branch = run.get("headBranch", "")
    event = run.get("event", "")
    wf = run.get("workflowName", "")

    return f"  {color}{icon} {label:<11}{RESET}  {wf:<40}  {branch:<20}  {event:<18}  {age}"

def main():
    parser = argparse.ArgumentParser(
        description="Zeigt den Status des letzten GitHub Actions Runs je Pipeline für alle Projekte."
    )
    parser.add_argument(
        "basedir", nargs="?", default=".",  # Wurzelverzeichnis für die lokale Repo-Suche
        help="Basisverzeichnis (Standard: .)"
    )
    parser.add_argument(
        "--no-color", action="store_true",  # Deaktiviert ANSI-Farben, z.B. für Pipe-Ausgabe
        help="Farbige Ausgabe deaktivieren"
    )

    visibility_group = parser.add_mutually_exclusive_group()
    visibility_group.add_argument(
        "--public", action="store_true",    # Nur öffentliche Repos (lokal: gh repo view, online: isPrivate=false)
        help="Nur öffentliche Repositories anzeigen"
    )
    visibility_group.add_argument(
        "--private", action="store_true",   # Nur private Repos (lokal: gh repo view, online: isPrivate=true)
        help="Nur private Repositories anzeigen"
    )

    parser.add_argument(
        "--online", action="store_true",    # Kein lokales Scannen: holt alle Repos per gh repo list
        help="Alle GitHub-Repositories abrufen statt lokale Verzeichnisse zu scannen"
    )
    parser.add_argument(
        "--error", action="store_true",     # Zeigt nur Repos mit failure/timed_out/cancelled, blendet erfolgreiche aus
        help="Nur Repositories mit mindestens einem fehlgeschlagenen Run anzeigen"
    )
    args = parser.parse_args()

    if args.no_color:
        global RESET
        RESET = ""
        for k in CONCLUSION_STYLE:
            icon, _ = CONCLUSION_STYLE[k]
            CONCLUSION_STYLE[k] = (icon, "")
        for k in STATUS_STYLE:
            icon, _ = STATUS_STYLE[k]
            STATUS_STYLE[k] = (icon, "")

    header = f"  {'Status':<14}  {'Workflow':<40}  {'Branch':<20}  {'Event':<18}  Alter"
    sep = "━" * len(header)

    if args.online:
        repos, error = get_online_repos(public_only=args.public, private_only=args.private)
        if error:
            print(f"❌ Fehler beim Abrufen der GitHub-Repos: {error}")
            return
        if not repos:
            print("Keine Repositories gefunden.")
            return

        vis_label = " (nur öffentlich)" if args.public else " (nur privat)" if args.private else ""
        print(f"🌐 {len(repos)} GitHub-Repository/ies gefunden{vis_label}\n")

        for repo in sorted(repos, key=lambda r: r["name"]):
            name = repo["nameWithOwner"]
            runs, run_error = get_latest_runs(repo_name=name)

            if args.error:
                if not runs or not any(r.get("conclusion") in FAILED_CONCLUSIONS for r in runs):
                    continue
                runs = [r for r in runs if r.get("conclusion") in FAILED_CONCLUSIONS]

            privacy = "🔒" if repo["isPrivate"] else "🌍"
            print(f"{privacy} {name}")
            if run_error:
                print(f"  ⚠️  Übersprungen: {run_error}")
            elif not runs:
                print("  — Keine Runs gefunden")
            else:
                print(header)
                print(sep)
                for run in sorted(runs, key=lambda r: r["workflowName"]):
                    print(format_run(run))
            print()
    else:
        repos = find_repos(args.basedir)
        if not repos:
            print("Keine Git-Repositories gefunden.")
            return

        if args.public or args.private:
            filtered = []
            for repo in repos:
                is_private = get_repo_is_private(repo)
                if is_private is None:
                    filtered.append(repo)
                elif args.public and not is_private:
                    filtered.append(repo)
                elif args.private and is_private:
                    filtered.append(repo)
            repos = filtered

        vis_label = " (nur öffentlich)" if args.public else " (nur privat)" if args.private else ""
        print(f"🔍 {len(repos)} Repository/ies gefunden{vis_label}\n")

        for repo in repos:
            name = repo.name
            runs, error = get_latest_runs(repo_path=repo)

            if args.error:
                if not runs or not any(r.get("conclusion") in FAILED_CONCLUSIONS for r in runs):
                    continue
                runs = [r for r in runs if r.get("conclusion") in FAILED_CONCLUSIONS]

            print(f"📂 {name}")
            if error:
                print(f"  ⚠️  Übersprungen: {error}")
            elif not runs:
                print("  — Keine Runs gefunden")
            else:
                print(header)
                print(sep)
                for run in sorted(runs, key=lambda r: r["workflowName"]):
                    print(format_run(run))
            print()

if __name__ == "__main__":
    main()

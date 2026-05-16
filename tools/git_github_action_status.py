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

def is_git_repo(path):
    return (Path(path) / ".git").is_dir()

def find_repos(base_dir):
    result = []
    for folder in sorted(os.listdir(base_dir)):
        full_path = Path(base_dir) / folder
        if full_path.is_dir() and is_git_repo(full_path):
            result.append(full_path)
    return result

def get_latest_runs(repo_path):
    try:
        result = subprocess.run(
            [
                "gh", "run", "list",
                "--limit", "100",
                "--json", "workflowName,status,conclusion,event,headBranch,createdAt",
            ],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
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
        "basedir", nargs="?", default=".", help="Basisverzeichnis (Standard: .)"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Farbige Ausgabe deaktivieren"
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

    repos = find_repos(args.basedir)
    if not repos:
        print("Keine Git-Repositories gefunden.")
        return

    print(f"🔍 {len(repos)} Repository/ies gefunden\n")
    header = f"  {'Status':<14}  {'Workflow':<40}  {'Branch':<20}  {'Event':<18}  Alter"
    sep = "━" * len(header)

    for repo in repos:
        name = repo.name
        runs, error = get_latest_runs(repo)

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

#!/usr/bin/env python3
"""
update-uv.py – Aktualisiert uv.lock auf die neuesten Releases,
prüft via `uv sync` und gibt eine fertige Commit-Message aus.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR: Path  # wird in main() gesetzt


# ---------------------------------------------------------------------------
# uv.lock parsen
# ---------------------------------------------------------------------------

def parse_versions(lock_path: Path) -> dict[str, str]:
    versions = {}
    content = lock_path.read_text(encoding="utf-8")
    for block in re.split(r"\[\[package\]\]", content):
        name_m = re.search(r'^name\s*=\s*"([^"]+)"', block, re.M)
        ver_m = re.search(r'^version\s*=\s*"([^"]+)"', block, re.M)
        if name_m and ver_m:
            versions[name_m.group(1)] = ver_m.group(1)
    return versions


# ---------------------------------------------------------------------------
# uv-Befehle
# ---------------------------------------------------------------------------

def run_uv_lock() -> bool:
    print("\nStarte uv lock --upgrade ...")
    result = subprocess.run(["uv", "lock", "--upgrade"], cwd=PROJECT_DIR)
    return result.returncode == 0


def run_uv_sync() -> bool:
    print("\nPrüfe mit uv sync ...")
    result = subprocess.run(["uv", "sync"], cwd=PROJECT_DIR)
    return result.returncode == 0


def run_checks(installed: dict[str, str]) -> bool:
    checks = [
        ("ruff",    ["uv", "run", "ruff", "check"]),
        ("pyright", ["uv", "run", "pyright"]),
    ]
    all_ok = True
    for package, cmd in checks:
        if package not in installed:
            continue
        print(f"\nStarte {cmd[2]} ...")
        result = subprocess.run(cmd, cwd=PROJECT_DIR)
        if result.returncode != 0:
            print(f"❌ {cmd[2]} fehlgeschlagen.")
            all_ok = False
    return all_ok


# ---------------------------------------------------------------------------
# Commit-Message generieren
# ---------------------------------------------------------------------------

def build_commit_message(old: dict, new: dict) -> str:
    updates = [
        (name, old[name], new_ver)
        for name, new_ver in new.items()
        if name in old and old[name] != new_ver
    ]
    added = sorted(name for name in new if name not in old)
    removed = sorted(name for name in old if name not in new)

    if not updates and not added and not removed:
        return "chore: no dependency updates"

    lines = ["uv updater: bump dependencies to latest releases", ""]
    for name, old_ver, new_ver in sorted(updates):
        lines.append(f"- {name}: {old_ver} → {new_ver}")
    for name in added:
        lines.append(f"- {name}: added {new[name]}")
    for name in removed:
        lines.append(f"- {name}: removed")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Git commit
# ---------------------------------------------------------------------------

def git_commit(message: str) -> None:
    add = subprocess.run(
        ["git", "add", "uv.lock", "pyproject.toml"],
        cwd=PROJECT_DIR,
    )
    if add.returncode != 0:
        print("⚠️  git add fehlgeschlagen – kein Commit erstellt.")
        return
    commit = subprocess.run(["git", "commit", "-m", message], cwd=PROJECT_DIR)
    if commit.returncode == 0:
        print("✔ Commit erstellt.")
    else:
        print("⚠️  git commit fehlgeschlagen.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global PROJECT_DIR
    parser = argparse.ArgumentParser(
        description="Aktualisiert uv.lock auf die neuesten Releases."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Verzeichnis mit pyproject.toml und uv.lock (Standard: aktuelles Verzeichnis)",
    )
    args = parser.parse_args()
    PROJECT_DIR = Path(args.directory).resolve()

    pyproject = PROJECT_DIR / "pyproject.toml"
    lock = PROJECT_DIR / "uv.lock"

    if not pyproject.exists():
        sys.exit(f"pyproject.toml nicht gefunden: {pyproject}")
    if not lock.exists():
        sys.exit(f"uv.lock nicht gefunden: {lock}")

    backup = lock.with_suffix(".lock.bak")
    shutil.copy2(lock, backup)
    print(f"Backup erstellt: {backup}\n")

    old_versions = parse_versions(lock)

    if not run_uv_lock():
        print("❌ uv lock --upgrade fehlgeschlagen.")
        backup.unlink(missing_ok=True)
        sys.exit(1)

    new_versions = parse_versions(lock)
    msg = build_commit_message(old_versions, new_versions)

    if old_versions == new_versions:
        print("\nKeine Updates verfügbar – uv.lock unverändert.")
        backup.unlink(missing_ok=True)
        return

    if not run_uv_sync():
        print("\nSync FEHLGESCHLAGEN – uv.lock wird zurückgesetzt.")
        shutil.copy2(backup, lock)
        backup.unlink(missing_ok=True)
        sys.exit(1)

    print("\nSync erfolgreich.")

    if not run_checks(new_versions):
        print("\nChecks FEHLGESCHLAGEN – uv.lock wird zurückgesetzt.")
        shutil.copy2(backup, lock)
        backup.unlink(missing_ok=True)
        sys.exit(1)

    backup.unlink(missing_ok=True)
    print()
    print("=" * 60)
    print("COMMIT MESSAGE")
    print("=" * 60)
    print(msg)
    print("=" * 60)
    git_commit(msg)


if __name__ == "__main__":
    main()

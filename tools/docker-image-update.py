#!/usr/bin/env python3
"""
Pull updated Docker images of affected containers.
Reads docker-image.status written by docker-image-status.py.

Usage: python3 docker-image-update.py [--dry-run]
"""

import subprocess
import json
import sys
import os
import datetime

STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker-image.status")

GREEN = "\033[32m"
RED   = "\033[31m"
CYAN  = "\033[36m"
RESET = "\033[0m"


def run(cmd, dry_run=False):
    print(f"  $ {' '.join(cmd)}")
    if dry_run:
        return
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"  {RED}FAILED (exit {result.returncode}){RESET}")


def load_status():
    if not os.path.exists(STATUS_FILE):
        print(f"Error: status file not found: {STATUS_FILE}", file=sys.stderr)
        print("Run docker-image-status.py first.", file=sys.stderr)
        sys.exit(1)

    with open(STATUS_FILE) as f:
        status = json.load(f)

    checked_at = status.get("checked_at", "unknown")
    print(f"Status from: {checked_at}")

    # Warn if status file is older than 1 hour
    try:
        ts = datetime.datetime.fromisoformat(checked_at)
        age = datetime.datetime.now(datetime.timezone.utc) - ts
        if age.total_seconds() > 3600:
            minutes = int(age.total_seconds() / 60)
            print(f"Warning: status file is {minutes} minutes old — consider re-running docker-image-status.py")
    except Exception:
        pass

    return status.get("containers", [])


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print(f"{CYAN}DRY RUN — no changes will be made{RESET}\n")

    containers = load_status()

    to_update = [c for c in containers if c.get("up_to_date") is False]
    up_to_date = [c for c in containers if c.get("up_to_date") is True]
    unknown    = [c for c in containers if c.get("up_to_date") is None]

    print(f"\nContainers up to date : {len(up_to_date)}")
    print(f"Containers to update  : {len(to_update)}")
    print(f"Containers unknown    : {len(unknown)}")

    if not to_update:
        print(f"\n{GREEN}Nothing to update.{RESET}")
        return

    print()
    for c in to_update:
        name  = c["name"]
        image = c["image"]
        print(f"{CYAN}Updating {name} ({image}){RESET}")

        print("  Pulling image ...")
        run(["docker", "pull", image], dry_run)

        print(f"  {GREEN}Done{RESET}")
        print()

    if unknown:
        print("Skipped (digest unknown):")
        for c in unknown:
            print(f"  {c['name']}  —  {c.get('error', '')}")


if __name__ == "__main__":
    main()

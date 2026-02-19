#!/usr/bin/env python3
# Zeigt alle eigenen GitHub-Repos, die KEIN "mirror" Topic haben

import json
import subprocess
import sys


def get_repos():
    result = subprocess.run(
        ["gh", "repo", "list", "--limit", "1000", "--json", "nameWithOwner,repositoryTopics"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Fehler: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def main():
    repos = get_repos()

    no_mirror = []
    no_topics = []

    for repo in repos:
        topics = [t["name"] for t in (repo.get("repositoryTopics") or [])]
        if not topics:
            no_topics.append(repo["nameWithOwner"])
        elif "mirror" not in topics:
            no_mirror.append(repo["nameWithOwner"])

    print("=== Kein 'mirror' Topic (aber andere Tags vorhanden) ===")
    for name in sorted(no_mirror):
        print(f"  {name}")

    print()
    print("=== Gar keine Topics ===")
    for name in sorted(no_topics):
        print(f"  {name}")


if __name__ == "__main__":
    main()

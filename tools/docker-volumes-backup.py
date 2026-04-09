#!/usr/bin/env python3
"""
Docker/Podman Volume Backup/Restore Tool
"""

import argparse
import subprocess
import sys
import json
from datetime import datetime
from pathlib import Path


# --- Color output ---

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text

def green(t):  return _c("32", t)
def red(t):    return _c("31", t)
def yellow(t): return _c("33", t)
def bold(t):   return _c("1",  t)


# --- Runtime detection ---

def detect_runtime(prefer: str | None = None) -> str:
    """Return 'docker' or 'podman', auto-detected or forced via --runtime."""
    candidates = [prefer] if prefer else ["docker", "podman"]
    for rt in candidates:
        if rt and subprocess.run(
            [rt, "info"], capture_output=True
        ).returncode == 0:
            return rt
    names = prefer or "docker or podman"
    print(red(f"ERROR: No container runtime found ({names}). Is it running?"), file=sys.stderr)
    sys.exit(1)


# --- Core helpers ---

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def get_volumes(rt: str, name: str | None = None) -> list[dict]:
    result = run([rt, "volume", "ls", "--format", "{{json .}}"])
    volumes = [json.loads(line) for line in result.stdout.strip().splitlines() if line]
    if name:
        volumes = [v for v in volumes if v["Name"] == name]
    return volumes


def get_containers_using_volume(rt: str, volume_name: str) -> list[str]:
    """Return names of running containers that mount the given volume."""
    result = run([rt, "ps", "--format", "{{json .}}"], check=False)
    if result.returncode != 0:
        return []
    containers = [json.loads(line) for line in result.stdout.strip().splitlines() if line]
    using = []
    for c in containers:
        inspect = run([rt, "inspect", c["ID"], "--format", "{{json .Mounts}}"], check=False)
        if inspect.returncode != 0:
            continue
        mounts = json.loads(inspect.stdout.strip() or "[]")
        for m in mounts:
            if m.get("Type") == "volume" and m.get("Name") == volume_name:
                using.append(c["Names"])
    return using


def check_runtime_available(rt: str):
    result = subprocess.run([rt, "info"], capture_output=True)
    if result.returncode != 0:
        print(red(f"ERROR: '{rt}' is not running or not accessible."), file=sys.stderr)
        sys.exit(1)


# --- Commands ---

def backup_volume(rt: str, volume_name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Warn if volume is in use by running containers
    in_use = get_containers_using_volume(rt, volume_name)
    if in_use:
        print(yellow(f"  WARNING: Volume '{volume_name}' is mounted by running container(s): {', '.join(in_use)}"))
        print(yellow("           Backup may be inconsistent. Consider stopping containers first."))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"{volume_name}_{timestamp}.tar.gz"

    print(f"  Backing up {bold(volume_name)} -> {backup_file}")
    result = run([
        rt, "run", "--rm",
        "-v", f"{volume_name}:/data:ro",
        "-v", f"{output_dir.resolve()}:/backup",
        "alpine",
        "tar", "czf", f"/backup/{backup_file.name}", "-C", "/data", "."
    ], check=False)

    if result.returncode != 0:
        print(red(f"  ERROR: {result.stderr.strip()}"), file=sys.stderr)
        sys.exit(1)

    size = backup_file.stat().st_size
    print(green(f"  Done. Size: {size / 1024:.1f} KB"))
    return backup_file


def cmd_backup(args):
    rt = detect_runtime(args.runtime)
    volumes = get_volumes(rt, args.volume)
    if not volumes:
        target = f"'{args.volume}'" if args.volume else "any"
        print(red(f"No {target} volume found."), file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    print(f"Using runtime: {bold(rt)}")
    print(f"Backing up {bold(str(len(volumes)))} volume(s) to {output_dir}/\n")
    for vol in volumes:
        backup_volume(rt, vol["Name"], output_dir)


def cmd_list(args):
    output_dir = Path(args.output)
    if not output_dir.exists():
        print(yellow(f"Backup directory '{output_dir}' does not exist."))
        return

    backups = sorted(output_dir.glob("*.tar.gz"))
    if not backups:
        print(yellow("No backups found."))
        return

    print(f"{'File':<50} {'Size':>10}")
    print("-" * 62)
    for f in backups:
        size_kb = f.stat().st_size / 1024
        print(f"{f.name:<50} {size_kb:>9.1f}K")


def cmd_volumes(args):
    rt = detect_runtime(args.runtime)
    volumes = get_volumes(rt)
    if not volumes:
        print(yellow("No Docker/Podman volumes found."))
        return

    # Get container usage per volume
    result = run([rt, "ps", "-a", "--format", "{{json .}}"], check=False)
    containers = [json.loads(line) for line in result.stdout.strip().splitlines() if line]

    usage: dict[str, list[str]] = {v["Name"]: [] for v in volumes}
    for container in containers:
        inspect = run([rt, "inspect", container["ID"], "--format", "{{json .Mounts}}"], check=False)
        if inspect.returncode != 0:
            continue
        mounts = json.loads(inspect.stdout.strip() or "[]")
        for mount in mounts:
            if mount.get("Type") == "volume":
                vol_name = mount.get("Name", "")
                if vol_name in usage:
                    usage[vol_name].append(container["Names"])

    print(f"Using runtime: {bold(rt)}\n")
    print(f"{'Volume':<40} {'Driver':<12} {'Containers'}")
    print("-" * 75)
    for vol in volumes:
        name = vol["Name"]
        driver = vol.get("Driver", "local")
        containers_str = ", ".join(usage.get(name, [])) or "-"
        in_use = bool(usage.get(name))
        line = f"{name:<40} {driver:<12} {containers_str}"
        print(green(line) if in_use else line)


def cmd_delete(args):
    rt = detect_runtime(args.runtime)
    volumes = get_volumes(rt, args.volume)
    if not volumes:
        print(red(f"Volume '{args.volume}' not found."), file=sys.stderr)
        sys.exit(1)

    vol = volumes[0]

    # Refuse if volume is in use by running containers
    in_use = get_containers_using_volume(rt, vol["Name"])
    if in_use:
        print(red(f"ERROR: Volume '{vol['Name']}' is in use by: {', '.join(in_use)}"), file=sys.stderr)
        print("Stop the container(s) first.", file=sys.stderr)
        sys.exit(1)

    if not args.force:
        answer = input(f"Delete volume '{bold(vol['Name'])}'? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    print(f"Deleting volume '{vol['Name']}'...")
    result = run([rt, "volume", "rm", vol["Name"]], check=False)
    if result.returncode != 0:
        print(red(f"ERROR: {result.stderr.strip()}"), file=sys.stderr)
        sys.exit(1)
    print(green("Done."))


def cmd_restore(args):
    rt = detect_runtime(args.runtime)
    backup_file = Path(args.file)
    if not backup_file.exists():
        print(red(f"Backup file '{backup_file}' not found."), file=sys.stderr)
        sys.exit(1)

    existing = get_volumes(rt, args.volume)
    if existing:
        answer = input(f"Volume '{bold(args.volume)}' already exists. Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return
        run([rt, "volume", "rm", args.volume])

    print(f"Using runtime: {bold(rt)}")
    print(f"Creating volume '{args.volume}'...")
    run([rt, "volume", "create", args.volume])

    print(f"Restoring from '{backup_file}'...")
    result = run([
        rt, "run", "--rm",
        "-v", f"{args.volume}:/data",
        "-v", f"{backup_file.resolve().parent}:/backup:ro",
        "alpine",
        "tar", "xzf", f"/backup/{backup_file.name}", "-C", "/data"
    ], check=False)

    if result.returncode != 0:
        print(red(f"ERROR: {result.stderr.strip()}"), file=sys.stderr)
        sys.exit(1)
    print(green("Restore complete."))


# --- Argument parsing ---

def main():
    parser = argparse.ArgumentParser(description="Docker/Podman Volume Backup/Restore Tool")
    parser.add_argument(
        "--runtime", metavar="RT", choices=["docker", "podman"],
        help="Container runtime to use (default: auto-detect)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # backup
    p_backup = sub.add_parser("backup", help="Backup one or all volumes")
    p_backup.add_argument("--volume", metavar="NAME", help="Volume name (default: all)")
    p_backup.add_argument("--output", metavar="DIR", default="./docker-backups",
                          help="Backup directory (default: ./docker-backups)")

    # list
    p_list = sub.add_parser("list", help="List available backups")
    p_list.add_argument("--output", metavar="DIR", default="./docker-backups",
                        help="Backup directory (default: ./docker-backups)")

    # volumes
    sub.add_parser("volumes", help="List all volumes with container usage")

    # delete
    p_delete = sub.add_parser("delete", help="Delete a volume")
    p_delete.add_argument("--volume", metavar="NAME", required=True, help="Volume name to delete")
    p_delete.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    # restore
    p_restore = sub.add_parser("restore", help="Restore a volume from backup")
    p_restore.add_argument("--volume", metavar="NAME", required=True, help="Target volume name")
    p_restore.add_argument("--file", metavar="BACKUP_FILE", required=True,
                           help="Path to .tar.gz backup file")

    args = parser.parse_args()
    {
        "backup":  cmd_backup,
        "list":    cmd_list,
        "volumes": cmd_volumes,
        "delete":  cmd_delete,
        "restore": cmd_restore,
    }[args.command](args)


if __name__ == "__main__":
    main()

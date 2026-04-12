#!/usr/bin/env python3

import os
import sys
import subprocess
import yaml

CONFIG_PATH = "/etc/rancher/k3s/config.yaml"
CERT_FILES = [
    "/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt",
    "/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.key",
]


def check_root():
    if os.geteuid() != 0:
        print("Error: This script must be run as root (sudo).", file=sys.stderr)
        sys.exit(1)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def show_sans(config):
    sans = config.get("tls-san", [])
    if not sans:
        print("No tls-san entries configured.")
    else:
        print("Current tls-san entries:")
        for entry in sans:
            print(f"  - {entry}")


def add_san(config, value):
    sans = config.get("tls-san", [])
    if value in sans:
        print(f"Entry already exists, skipping: {value}")
        return False
    sans.append(value)
    config["tls-san"] = sans
    print(f"Adding entry: {value}")
    return True


def run(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(result.returncode)


def restart_k3s():
    run(["systemctl", "stop", "k3s"])
    for path in CERT_FILES:
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed: {path}")
        else:
            print(f"Not found (skipping): {path}")
    run(["systemctl", "start", "k3s"])


def main():
    if len(sys.argv) > 2:
        print(f"Usage: {sys.argv[0]} [<ip-or-hostname>]", file=sys.stderr)
        sys.exit(1)

    check_root()
    config = load_config()

    if len(sys.argv) == 1:
        show_sans(config)
        return

    value = sys.argv[1]
    changed = add_san(config, value)

    if changed:
        save_config(config)
        restart_k3s()
        print("Done.")


if __name__ == "__main__":
    main()

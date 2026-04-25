#!/bin/bash
# removeserver.sh – Firecracker-MicroVM stoppen und alle zugehörigen Ressourcen löschen
#
# Verwendung: ./removeserver.sh <name>
#   name – VM-Name, der mit addserver.sh erstellt wurde

set -euo pipefail

NAME="${1:-}"

if [ -z "$NAME" ]; then
    echo "Fehler: VM-Name fehlt."
    echo "Verwendung: $0 <name>"
    exit 1
fi

if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "Fehler: Name darf nur Kleinbuchstaben, Ziffern und Bindestriche enthalten."
    exit 1
fi

FC_DIR="${FC_DIR:-$HOME/firecracker}"
VM_DIR="$FC_DIR/vms/$NAME"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
skip() { echo "[$(date '+%H:%M:%S')] – übersprungen: $*"; }
err()  { echo "[$(date '+%H:%M:%S')] FEHLER: $*" >&2; exit 1; }

[ -d "$VM_DIR" ] || err "VM '$NAME' nicht gefunden: $VM_DIR"

sudo -v

# ── Prozess stoppen ───────────────────────────────────────────────────────────

PID_FILE="$VM_DIR/firecracker.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "Stoppe Firecracker-Prozess (PID $PID)..."
        kill "$PID"
        # Warten bis der Prozess beendet ist (max. 5 Sek.)
        for i in $(seq 1 10); do
            kill -0 "$PID" 2>/dev/null || break
            sleep 0.5
        done
        if kill -0 "$PID" 2>/dev/null; then
            log "Prozess antwortet nicht – sende SIGKILL..."
            kill -9 "$PID" 2>/dev/null || true
        fi
        ok "Prozess beendet."
    else
        skip "Prozess $PID läuft nicht mehr."
    fi
else
    skip "Keine PID-Datei gefunden – VM war bereits gestoppt."
fi

# ── Verwaiste Loop-Mounts bereinigen ─────────────────────────────────────────
#
# Wenn addserver.sh während des rootfs-Mounts abbrach, hängt das Dateisystem
# noch im Kernel. rm -rf würde die Datei unter dem aktiven Mount löschen und
# ein orphaned loop device hinterlassen.

VM_ROOTFS="$VM_DIR/rootfs.ext4"
if [ -f "$VM_ROOTFS" ]; then
    STALE_MOUNT=$(findmnt -n -o TARGET --source "$VM_ROOTFS" 2>/dev/null || true)
    if [ -n "$STALE_MOUNT" ]; then
        log "Löse verwaistes Mount von rootfs.ext4 ($STALE_MOUNT)..."
        sudo umount "$STALE_MOUNT"
        rmdir "$STALE_MOUNT" 2>/dev/null || true
        ok "Verwaistes Mount entfernt."
    fi
fi

# ── TAP-Interface entfernen ───────────────────────────────────────────────────
#
# Primär aus tap_dev-Datei lesen; falls fehlend (Abbruch vor Metadaten-Schreiben)
# aus der index-Datei ableiten.

TAP_DEV=""
if [ -f "$VM_DIR/tap_dev" ]; then
    TAP_DEV=$(cat "$VM_DIR/tap_dev")
elif [ -f "$VM_DIR/index" ]; then
    TAP_DEV="tap$(cat "$VM_DIR/index")"
    log "tap_dev-Datei fehlt – leite TAP-Name aus Index ab: $TAP_DEV"
fi

if [ -n "$TAP_DEV" ]; then
    if ip link show "$TAP_DEV" &>/dev/null; then
        log "Entferne TAP-Interface $TAP_DEV..."
        sudo ip link set "$TAP_DEV" down 2>/dev/null || true
        sudo ip tuntap del dev "$TAP_DEV" mode tap || true
        ok "$TAP_DEV entfernt."
    else
        skip "$TAP_DEV existiert nicht (bereits entfernt oder nach Reboot verschwunden)."
    fi

    # systemd-networkd-Konfiguration entfernen
    NETDEV_FILE="/etc/systemd/network/50-${TAP_DEV}.netdev"
    NETWORK_FILE="/etc/systemd/network/50-${TAP_DEV}.network"
    removed=0
    for f in "$NETDEV_FILE" "$NETWORK_FILE"; do
        if [ -f "$f" ]; then
            sudo rm -f "$f"
            removed=1
        fi
    done
    if [ "$removed" = "1" ]; then
        sudo systemctl reload-or-restart systemd-networkd || true
        ok "systemd-networkd-Konfiguration für $TAP_DEV entfernt."
    else
        skip "Keine systemd-networkd-Dateien für $TAP_DEV gefunden."
    fi
else
    skip "Kein TAP-Name ermittelbar – TAP-Cleanup übersprungen."
fi

# ── VM-Verzeichnis löschen ────────────────────────────────────────────────────

log "Lösche VM-Verzeichnis $VM_DIR..."
rm -rf "$VM_DIR"
ok "VM '$NAME' vollständig entfernt."

#!/bin/bash
# removeserver.sh – Firecracker-MicroVM stoppen und alle zugehörigen Ressourcen löschen
#
# Räumt auch dann auf, wenn das VM-Verzeichnis bereits gelöscht wurde:
# TAP-Interface, systemd-networkd-Konfiguration, iptables-nft- und nft-Regeln,
# verwaiste Loop-Mounts.
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
warn() { echo "[$(date '+%H:%M:%S')] ! $*" >&2; }

if [ ! -d "$VM_DIR" ]; then
    warn "VM-Verzeichnis nicht gefunden ($VM_DIR) – versuche trotzdem System-Ressourcen aufzuräumen."
fi

sudo -v

# ── Prozess stoppen ───────────────────────────────────────────────────────────

PID_FILE="$VM_DIR/firecracker.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "Stoppe Firecracker-Prozess (PID $PID)..."
        kill "$PID"
        for _i in $(seq 1 10); do
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
# Fall 1: rootfs-Datei noch vorhanden → via findmnt suchen.
# Fall 2: VM-Verzeichnis weg, aber Mount noch aktiv → /proc/mounts nach
#         Pfaden unter VM_DIR durchsuchen.

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

# Alle Mounts, deren Quellpfad unter VM_DIR liegt (auch wenn Dir bereits weg)
while IFS= read -r _tgt; do
    log "Löse verwaistes Mount: $_tgt ..."
    sudo umount -l "$_tgt" 2>/dev/null || true
    ok "Mount $_tgt gelöst."
done < <(awk -v d="$VM_DIR/" '$1 ~ "^"d || $2 ~ "^"d {print $2}' /proc/mounts 2>/dev/null | sort -r || true)

# ── TAP-Interface und IPs ermitteln ──────────────────────────────────────────
#
# Quelle 1: Metadaten im VM-Verzeichnis (bevorzugt).
# Quelle 2: /etc/systemd/network/50-tap*.vm (Fallback, wenn VM-Dir weg ist).

TAP_DEV=""
GUEST_IP=""
HOST_IP=""

if [ -f "$VM_DIR/tap_dev" ]; then
    TAP_DEV=$(cat "$VM_DIR/tap_dev")
elif [ -f "$VM_DIR/index" ]; then
    TAP_DEV="tap$(cat "$VM_DIR/index")"
    log "tap_dev-Datei fehlt – leite TAP-Name aus Index ab: $TAP_DEV"
fi
[ -f "$VM_DIR/guest_ip" ] && GUEST_IP=$(cat "$VM_DIR/guest_ip") || true
[ -f "$VM_DIR/host_ip"  ] && HOST_IP=$(cat "$VM_DIR/host_ip")  || true

if [ -z "$TAP_DEV" ]; then
    VM_META=$(grep -rl "^NAME=${NAME}$" /etc/systemd/network/50-tap*.vm 2>/dev/null | head -1 || true)
    if [ -n "$VM_META" ]; then
        TAP_DEV=$(grep "^TAP_DEV=" "$VM_META" | cut -d= -f2)
        HOST_IP=$(grep "^HOST_IP="  "$VM_META" | cut -d= -f2)
        GUEST_IP=$(grep "^GUEST_IP=" "$VM_META" | cut -d= -f2)
        log "Metadaten aus $VM_META wiederhergestellt: TAP=$TAP_DEV, Host=$HOST_IP, Guest=$GUEST_IP"
    else
        warn "Keine Metadaten für VM '$NAME' gefunden – TAP/Netzwerk-Cleanup nicht möglich."
    fi
fi

# ── systemd-networkd-Konfiguration entfernen (vor TAP-Löschen, damit IPMasquerade sauber abbaut) ──

if [ -n "$TAP_DEV" ]; then
    _removed=0
    for _f in \
        "/etc/systemd/network/50-${TAP_DEV}.netdev" \
        "/etc/systemd/network/50-${TAP_DEV}.network" \
        "/etc/systemd/network/50-${TAP_DEV}.vm"; do
        if [ -f "$_f" ]; then
            sudo rm -f "$_f"
            _removed=1
        fi
    done
    if [ "$_removed" = "1" ]; then
        sudo systemctl reload-or-restart systemd-networkd || true
        ok "systemd-networkd-Konfiguration für $TAP_DEV entfernt."
    else
        skip "Keine systemd-networkd-Dateien für $TAP_DEV gefunden."
    fi
fi

# ── iptables-nft Regeln entfernen ─────────────────────────────────────────────
#
# Deckt den Fall ab, dass Regeln manuell (z. B. nach getting-started.md) oder
# durch ein älteres Skript ohne systemd-networkd angelegt wurden.

if command -v iptables-nft &>/dev/null && [ -n "$GUEST_IP" ] || [ -n "$TAP_DEV" ]; then
    HOST_IFACE=$(ip -j route list default 2>/dev/null | jq -r '.[0].dev' 2>/dev/null || true)

    if [ -n "$HOST_IFACE" ]; then
        if [ -n "$GUEST_IP" ]; then
            if sudo iptables-nft -t nat -C POSTROUTING -o "$HOST_IFACE" -s "$GUEST_IP" -j MASQUERADE 2>/dev/null; then
                sudo iptables-nft -t nat -D POSTROUTING -o "$HOST_IFACE" -s "$GUEST_IP" -j MASQUERADE
                ok "iptables-nft: POSTROUTING-Regel für $GUEST_IP entfernt."
            else
                skip "iptables-nft: keine POSTROUTING-Regel für $GUEST_IP vorhanden."
            fi
        fi
        if [ -n "$TAP_DEV" ]; then
            if sudo iptables-nft -C FORWARD -i "$TAP_DEV" -o "$HOST_IFACE" -j ACCEPT 2>/dev/null; then
                sudo iptables-nft -D FORWARD -i "$TAP_DEV" -o "$HOST_IFACE" -j ACCEPT
                ok "iptables-nft: FORWARD-Regel für $TAP_DEV entfernt."
            else
                skip "iptables-nft: keine FORWARD-Regel für $TAP_DEV vorhanden."
            fi
        fi
    else
        skip "iptables-nft: Standard-Interface nicht ermittelbar."
    fi
fi

# ── nft Regeln in der 'firecracker'-Tabelle entfernen ─────────────────────────
#
# Deckt manuelle nft-Konfiguration nach network-setup.md ab.
# Die systemd-networkd-eigene Tabelle (io.systemd.nat) wird durch den
# networkd-Reload oben bereits bereinigt.

if command -v nft &>/dev/null; then
    if sudo nft list table firecracker &>/dev/null 2>&1; then
        if [ -n "$GUEST_IP" ]; then
            _handle=$(sudo nft -a list chain firecracker postrouting 2>/dev/null \
                | grep "$GUEST_IP" \
                | awk '{for(i=1;i<=NF;i++) if($i=="handle") print $(i+1)}' \
                | head -1 || true)
            if [ -n "$_handle" ]; then
                sudo nft delete rule firecracker postrouting handle "$_handle"
                ok "nft: postrouting-Regel für $GUEST_IP (handle $_handle) entfernt."
            else
                skip "nft: keine postrouting-Regel für $GUEST_IP vorhanden."
            fi
        fi
        if [ -n "$TAP_DEV" ]; then
            _handle=$(sudo nft -a list chain firecracker filter 2>/dev/null \
                | grep "$TAP_DEV" \
                | awk '{for(i=1;i<=NF;i++) if($i=="handle") print $(i+1)}' \
                | head -1 || true)
            if [ -n "$_handle" ]; then
                sudo nft delete rule firecracker filter handle "$_handle"
                ok "nft: filter-Regel für $TAP_DEV (handle $_handle) entfernt."
            else
                skip "nft: keine filter-Regel für $TAP_DEV vorhanden."
            fi
        fi
    else
        skip "nft: Tabelle 'firecracker' nicht vorhanden."
    fi
fi

# ── TAP-Interface entfernen ───────────────────────────────────────────────────

if [ -n "$TAP_DEV" ]; then
    if ip link show "$TAP_DEV" &>/dev/null; then
        log "Entferne TAP-Interface $TAP_DEV..."
        sudo ip link set "$TAP_DEV" down 2>/dev/null || true
        sudo ip tuntap del dev "$TAP_DEV" mode tap || true
        ok "$TAP_DEV entfernt."
    else
        skip "$TAP_DEV existiert nicht (bereits entfernt oder nach Reboot verschwunden)."
    fi
else
    skip "Kein TAP-Name ermittelbar – TAP-Cleanup übersprungen."
fi

# ── VM-Verzeichnis löschen ────────────────────────────────────────────────────

if [ -d "$VM_DIR" ]; then
    log "Lösche VM-Verzeichnis $VM_DIR..."
    rm -rf "$VM_DIR"
    ok "VM '$NAME' vollständig entfernt."
else
    ok "VM '$NAME' Ressourcen aufgeräumt (Verzeichnis war bereits gelöscht)."
fi

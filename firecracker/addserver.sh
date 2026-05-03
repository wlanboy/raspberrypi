#!/bin/bash
# addserver.sh – Neue Firecracker-MicroVM erstellen und starten
#
# Idempotent: existiert eine VM mit dem Namen bereits, wird sie gestartet
# (falls gestoppt) oder der aktuelle Status gemeldet (falls läuft).
#
# Verwendung: ./addserver.sh <name> [vcpus] [mem_mib] [disk_gb]
#   name     – eindeutiger VM-Name, z. B. "web01" (nur a-z, 0-9, Bindestrich)
#   vcpus    – Anzahl vCPUs        (Standard: 2)
#   mem_mib  – RAM in MiB          (Standard: 1024)
#   disk_gb  – Disk-Größe in GB    (Standard: 5, muss ≥ 3 sein)
#
# Netzwerk-Schema (pro VM automatisch vergeben, /30-Subnetze sequentiell):
#   VM-Index N → tap IP:  172.16.[(4*N+1)/256].[(4*N+1)%256]
#                Guest-IP: 172.16.[(4*N+2)/256].[(4*N+2)%256]
#   Beispiel N=0: tap=172.16.0.1/30, guest=172.16.0.2
#   Beispiel N=1: tap=172.16.0.5/30, guest=172.16.0.6
#
# Voraussetzung: firecracker.sh wurde erfolgreich ausgeführt.

set -euo pipefail

# ── Parameter ────────────────────────────────────────────────────────────────

NAME="${1:-}"
VCPUS="${2:-2}"
MEM_MIB="${3:-1024}"
DISK_GB="${4:-5}"

if [ -z "$NAME" ]; then
    echo "Fehler: VM-Name fehlt."
    echo "Verwendung: $0 <name> [vcpus] [mem_mib] [disk_gb]"
    exit 1
fi

# Namen auf erlaubte Zeichen prüfen (verhindert Pfad-Injection)
if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "Fehler: Name darf nur Kleinbuchstaben, Ziffern und Bindestriche enthalten."
    exit 1
fi

if [[ ! "$VCPUS" =~ ^[0-9]+$ ]] || [ "$VCPUS" -lt 1 ]; then
    echo "Fehler: vcpus muss eine positive Ganzzahl sein."
    exit 1
fi

if [[ ! "$MEM_MIB" =~ ^[0-9]+$ ]] || [ "$MEM_MIB" -lt 128 ]; then
    echo "Fehler: mem_mib muss eine Ganzzahl ≥ 128 sein."
    exit 1
fi

if [[ ! "$DISK_GB" =~ ^[0-9]+$ ]] || [ "$DISK_GB" -lt 3 ]; then
    echo "Fehler: Disk-Größe muss mindestens 3 GB betragen (Basis-Image-Größe)."
    exit 1
fi

# Nutzer, der die VM anlegt (wird als sudo-fähiger Benutzer in der VM angelegt)
HOST_USER="${SUDO_USER:-$USER}"
HOST_HOME="$(eval echo ~"$HOST_USER")"

# ── Pfade ─────────────────────────────────────────────────────────────────────

FC_DIR="${FC_DIR:-$HOME/firecracker}"
BASE_ROOTFS="$FC_DIR/base.ext4"
VMLINUX="$FC_DIR/vmlinux"
VM_DIR="$FC_DIR/vms/$NAME"

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
skip() { echo "[$(date '+%H:%M:%S')] – übersprungen: $*"; }
err()  { echo "[$(date '+%H:%M:%S')] FEHLER: $*" >&2; exit 1; }

# Gibt zurück, ob eine VM aktuell läuft (PID-Datei + Prozess existiert)
vm_is_running() {
    local pid_file="$VM_DIR/firecracker.pid"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0   # läuft
        fi
    fi
    return 1   # gestoppt
}

# ── Voraussetzungen prüfen ───────────────────────────────────────────────────

[ -f "$BASE_ROOTFS" ] || err "Basis-Rootfs nicht gefunden: $BASE_ROOTFS – bitte zuerst firecracker.sh ausführen."
[ -f "$VMLINUX"     ] || err "Kernel nicht gefunden: $VMLINUX – bitte zuerst firecracker.sh ausführen."
command -v firecracker &>/dev/null || err "Firecracker nicht installiert – bitte zuerst firecracker.sh ausführen."

sudo -v   # sudo-Credentials vorab cachen

# ── Wenn VM schon existiert: Status prüfen und ggf. neu starten ──────────────

if [ -d "$VM_DIR" ]; then
    if vm_is_running; then
        GUEST_IP=$(cat "$VM_DIR/guest_ip" 2>/dev/null || echo "unbekannt")
        echo ""
        echo "VM '$NAME' läuft bereits."
        echo "  SSH:  ssh root@${GUEST_IP}"
        echo "  Log:  tail -f $VM_DIR/console.log"
        echo "  Stop: kill \$(cat $VM_DIR/firecracker.pid)"
        exit 0
    else
        log "VM '$NAME' existiert, ist aber gestoppt – starte neu..."
        # Socket aus vorherigem Lauf entfernen
        rm -f "$VM_DIR/firecracker.socket"
        # Direkt zum Start-Abschnitt springen (alle Metadaten laden)
        INDEX=$(cat "$VM_DIR/index")
        GUEST_IP=$(cat "$VM_DIR/guest_ip")
        HOST_IP=$(cat "$VM_DIR/host_ip")
        VCPUS=$(cat "$VM_DIR/vcpus"      2>/dev/null || echo "$VCPUS")
        MEM_MIB=$(cat "$VM_DIR/mem_mib"   2>/dev/null || echo "$MEM_MIB")
        DISK_GB=$(cat "$VM_DIR/disk_gb"   2>/dev/null || echo "$DISK_GB")
        HOST_USER=$(cat "$VM_DIR/host_user" 2>/dev/null || echo "$HOST_USER")
        TAP_DEV="tap${INDEX}"
        # TAP-Interface erneut anlegen, falls nach Reboot verschwunden
        if ! ip link show "$TAP_DEV" &>/dev/null; then
            log "TAP-Interface $TAP_DEV fehlt – lege es neu an..."
            sudo ip tuntap add dev "$TAP_DEV" mode tap
            sudo ip addr add "${HOST_IP}/30" dev "$TAP_DEV"
            sudo ip link set "$TAP_DEV" up
            # networkd neu laden, damit IPMasquerade-Regeln wieder aktiv sind
            sudo systemctl reload-or-restart systemd-networkd || true
        fi
        # → Start-Abschnitt
        __restart=1
    fi
fi

__restart="${__restart:-0}"

# ── Neuen VM-Index vergeben ───────────────────────────────────────────────────
#
# Jede VM bekommt einen eindeutigen Index (0, 1, 2, …).
# Der Index bestimmt TAP-Name, Subnetz und MAC-Adresse.

if [ "$__restart" = "0" ]; then

    log "Vergebe VM-Index..."
    INDEX=0
    # Alle vorhandenen Indizes sammeln und den nächsten freien wählen
    for meta in "$FC_DIR/vms"/*/index; do
        [ -f "$meta" ] || continue
        used=$(cat "$meta")
        if [ "$used" -ge "$INDEX" ]; then
            INDEX=$(( used + 1 ))
        fi
    done

    # Sequentielle /30-Subnetze: je VM 4 Adressen (tap IP + guest IP + Netz + Broadcast)
    # Max. Index bei 172.16.0.0/16: (65535-2)/4 = 16383
    if [ "$INDEX" -gt 16383 ]; then
        err "Maximale Anzahl VMs (16384) erreicht."
    fi

    OFFSET=$(( INDEX * 4 ))
    HOST_THIRD=$(( (OFFSET + 1) / 256 ))
    HOST_FOURTH=$(( (OFFSET + 1) % 256 ))
    GUEST_THIRD=$(( (OFFSET + 2) / 256 ))
    GUEST_FOURTH=$(( (OFFSET + 2) % 256 ))
    HOST_IP="172.16.${HOST_THIRD}.${HOST_FOURTH}"
    GUEST_IP="172.16.${GUEST_THIRD}.${GUEST_FOURTH}"
    TAP_DEV="tap${INDEX}"
    # MAC: 06:00:AC:10:<octet3>:<octet4> – letzte 4 Bytes codieren die Guest-IP (172.16.X.Y)
    MAC=$(printf "06:00:AC:10:%02X:%02X" "$GUEST_THIRD" "$GUEST_FOURTH")

    ok "Index $INDEX → $TAP_DEV, Host: $HOST_IP, Gast: $GUEST_IP, MAC: $MAC"

    # ── VM-Verzeichnis anlegen und Metadaten speichern ────────────────────────

    mkdir -p "$VM_DIR"
    echo "$INDEX"    > "$VM_DIR/index"
    echo "$GUEST_IP" > "$VM_DIR/guest_ip"
    echo "$HOST_IP"  > "$VM_DIR/host_ip"
    echo "$TAP_DEV"  > "$VM_DIR/tap_dev"
    echo "$VCPUS"     > "$VM_DIR/vcpus"
    echo "$MEM_MIB"   > "$VM_DIR/mem_mib"
    echo "$DISK_GB"   > "$VM_DIR/disk_gb"
    echo "$HOST_USER" > "$VM_DIR/host_user"

    # ── Rootfs aus Basis-Image kopieren ──────────────────────────────────────
    #
    # Jede VM erhält eine eigene Kopie des goldenen Images.
    # cp --reflink=auto nutzt CoW (Copy-on-Write) auf btrfs/xfs, andernfalls
    # wird normal kopiert.

    VM_ROOTFS="$VM_DIR/rootfs.ext4"
    log "Kopiere Basis-Image nach $VM_ROOTFS..."
    cp --reflink=auto "$BASE_ROOTFS" "$VM_ROOTFS"

    # Disk auf gewünschte Größe vergrößern (nur Vergrößern möglich)
    if [ "$DISK_GB" -gt 3 ]; then
        log "Vergrößere Disk auf ${DISK_GB}G..."
        truncate -s "${DISK_GB}G" "$VM_ROOTFS"
        # e2fsck prüft und repariert das Dateisystem vor dem Resize
        sudo e2fsck -f -y "$VM_ROOTFS"; _ec=$?
        [ "$_ec" -le 2 ] \
            || err "e2fsck schlug fehl (Exit $_ec) – Basis-Image prüfen: $BASE_ROOTFS"
        sudo resize2fs "$VM_ROOTFS" \
            || err "resize2fs schlug fehl (Exit $?) – Basis-Image prüfen: $BASE_ROOTFS"
        ok "Disk auf ${DISK_GB}G vergrößert."
    fi

    # ── Rootfs anpassen: Hostname und Netzwerk ────────────────────────────────
    #
    # Das goldene Image hat keine Netzwerkkonfiguration.
    # Wir mounten die Kopie kurz, um VM-spezifische Einstellungen zu setzen.

    log "Konfiguriere Rootfs (Hostname, Netzwerk)..."
    MOUNT_DIR=$(mktemp -d)
    # Trap stellt sicher, dass das Mount-Verzeichnis auch bei Fehlern bereinigt wird.
    trap 'sudo umount "$MOUNT_DIR" 2>/dev/null || true; rmdir "$MOUNT_DIR" 2>/dev/null || true' EXIT
    sudo mount -t ext4 -o loop "$VM_ROOTFS" "$MOUNT_DIR" \
        || err "Konnte Rootfs nicht mounten: $VM_ROOTFS"
    [ -d "$MOUNT_DIR/etc" ] \
        || err "Basis-Image hat kein /etc-Verzeichnis – Image neu erstellen: rm $BASE_ROOTFS && ./firecracker.sh"

    # Hostname
    echo "$NAME" | sudo tee "$MOUNT_DIR/etc/hostname" > /dev/null
    sudo tee "$MOUNT_DIR/etc/hosts" > /dev/null <<EOF
127.0.0.1   localhost
127.0.1.1   $NAME
EOF

    # Statische IP über systemd-networkd
    # Firecracker hat kein DHCP; statische Konfiguration ist notwendig.
    sudo mkdir -p "$MOUNT_DIR/etc/systemd/network"
    sudo tee "$MOUNT_DIR/etc/systemd/network/20-eth0.network" > /dev/null <<EOF
[Match]
Name=eth0

[Network]
Address=${GUEST_IP}/30
Gateway=${HOST_IP}
DNS=8.8.8.8
DNS=1.1.1.1
MTUBytes=1450
EOF

    # Unprivilegierten Ping für alle Benutzer erlauben
    sudo mkdir -p "$MOUNT_DIR/etc/sysctl.d"
    printf 'net.ipv4.ping_group_range = 0 2147483647\n' \
        | sudo tee "$MOUNT_DIR/etc/sysctl.d/10-ping.conf" > /dev/null

    # ── SSH-Schlüssel für root einrichten ────────────────────────────────────
    mapfile -t _id_pubkeys < <(find "$HOST_HOME/.ssh" -maxdepth 1 -name 'id_*.pub' 2>/dev/null | sort)
    if [ ${#_id_pubkeys[@]} -gt 0 ]; then
        SSH_KEY_SOURCE="id_pubkeys"
    elif [ -f "$HOST_HOME/.ssh/authorized_keys" ]; then
        SSH_KEY_SOURCE="$HOST_HOME/.ssh/authorized_keys"
    else
        SSH_KEY_SOURCE=$(find "$HOST_HOME/.ssh" -maxdepth 1 -name '*.pub' 2>/dev/null | head -1)
    fi

    if [ -n "$SSH_KEY_SOURCE" ]; then
        log "Lege Benutzer '$HOST_USER' an und richte SSH-Schlüssel ein..."
        sudo chroot "$MOUNT_DIR" useradd -m -s /bin/bash "$HOST_USER"

        # SSH-Key für den Benutzer
        sudo mkdir -p "$MOUNT_DIR/home/$HOST_USER/.ssh"
        sudo chmod 700 "$MOUNT_DIR/home/$HOST_USER/.ssh"
        if [ "$SSH_KEY_SOURCE" = "id_pubkeys" ]; then
            cat "${_id_pubkeys[@]}" | sudo tee "$MOUNT_DIR/home/$HOST_USER/.ssh/authorized_keys" > /dev/null
        else
            sudo cp "$SSH_KEY_SOURCE" "$MOUNT_DIR/home/$HOST_USER/.ssh/authorized_keys"
        fi
        sudo chmod 600 "$MOUNT_DIR/home/$HOST_USER/.ssh/authorized_keys"
        sudo chroot "$MOUNT_DIR" chown -R "${HOST_USER}:${HOST_USER}" "/home/${HOST_USER}/.ssh"

        # SSH-Key auch für root
        sudo mkdir -p "$MOUNT_DIR/root/.ssh"
        sudo chmod 700 "$MOUNT_DIR/root/.ssh"
        if [ "$SSH_KEY_SOURCE" = "id_pubkeys" ]; then
            cat "${_id_pubkeys[@]}" | sudo tee "$MOUNT_DIR/root/.ssh/authorized_keys" > /dev/null
        else
            sudo cp "$SSH_KEY_SOURCE" "$MOUNT_DIR/root/.ssh/authorized_keys"
        fi
        sudo chmod 600 "$MOUNT_DIR/root/.ssh/authorized_keys"

        ok "Benutzer '$HOST_USER' und root mit SSH-Schlüssel eingerichtet."
    else
        log "Warnung: Kein SSH-Schlüssel gefunden – nur root-Login per Passwort (root) möglich."
    fi

    # SSH-Host-Keys vorab generieren – verhindert Hänger beim ersten Boot
    # (Firecracker VMs haben keinen virtio-rng, Entropy-Pool füllt sich langsam)
    # Keys direkt auf den Mount-Pfad generieren (kein Chroot nötig, Host hat Entropy)
    for _kt in rsa ecdsa ed25519; do
        sudo ssh-keygen -q -N "" -t "$_kt" \
            -f "$MOUNT_DIR/etc/ssh/ssh_host_${_kt}_key"
    done
    ok "SSH-Host-Keys vorausgeneriert."

    sudo umount "$MOUNT_DIR"
    rmdir "$MOUNT_DIR"
    trap - EXIT
    ok "Rootfs konfiguriert."

    # ── TAP-Interface anlegen ─────────────────────────────────────────────────
    #
    # tap{N} ist ein virtuelles Netzwerkinterface auf dem Host.
    # Firecracker verbindet die VM damit; der Host sieht es wie eine
    # normale Netzwerkkarte.

    log "Lege TAP-Interface $TAP_DEV an..."
    if ip link show "$TAP_DEV" &>/dev/null; then
        skip "$TAP_DEV existiert bereits."
    else
        sudo ip tuntap add dev "$TAP_DEV" mode tap
        sudo ip addr add "${HOST_IP}/30" dev "$TAP_DEV"
        sudo ip link set "$TAP_DEV" up
        ok "$TAP_DEV angelegt: $HOST_IP"
    fi

    # TAP dauerhaft via systemd-networkd (überlebt Reboot)
    # Netdev-Datei definiert den Interface-Typ
    sudo tee "/etc/systemd/network/50-${TAP_DEV}.netdev" > /dev/null <<EOF
[NetDev]
Name=${TAP_DEV}
Kind=tap
EOF

    # Network-Datei konfiguriert IP und NAT.
    # IPMasquerade=ipv4: eingehende VM-Pakete werden beim Verlassen des
    # Hosts (z. B. über eth0) mit der Host-IP als Absender versehen (NAT).
    sudo tee "/etc/systemd/network/50-${TAP_DEV}.network" > /dev/null <<EOF
[Match]
Name=${TAP_DEV}

[Network]
Address=${HOST_IP}/30
IPMasquerade=ipv4
IPForward=yes
EOF

    # VM-Metadatei: ermöglicht removeserver.sh auch nach Löschen des VM-Verzeichnisses
    # noch TAP-Name, IPs und VM-Name zu ermitteln.
    sudo tee "/etc/systemd/network/50-${TAP_DEV}.vm" > /dev/null <<EOF
NAME=${NAME}
TAP_DEV=${TAP_DEV}
HOST_IP=${HOST_IP}
GUEST_IP=${GUEST_IP}
EOF

    # systemd-networkd neu laden, damit die neuen Dateien aktiv werden
    sudo systemctl reload-or-restart systemd-networkd || true

    # ── Firecracker-Konfiguration schreiben ───────────────────────────────────

    VM_CONFIG="$VM_DIR/config.json"
    log "Erstelle config.json..."
    cat > "$VM_CONFIG" <<EOF
{
  "boot-source": {
    "kernel_image_path": "${VMLINUX}",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off root=/dev/vda rw ipv6.disable=1 net.ifnames=0 biosdevname=0 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "${VM_DIR}/rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": ${VCPUS},
    "mem_size_mib": ${MEM_MIB}
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "${MAC}",
      "host_dev_name": "${TAP_DEV}"
    }
  ],
  "entropy": {},
  "logger": {
    "log_path": "${VM_DIR}/firecracker.log",
    "level": "Info",
    "show_level": true
  }
}
EOF
    ok "config.json erstellt."

fi   # Ende des "neue VM anlegen"-Blocks

# ── Firecracker starten ───────────────────────────────────────────────────────
#
# Die VM startet im Hintergrund. Konsolenausgabe landet in console.log,
# Firecracker-interne Logs in firecracker.log.

VM_SOCKET="$VM_DIR/firecracker.socket"
VM_CONFIG="$VM_DIR/config.json"

log "Starte VM '$NAME'..."
firecracker \
    --api-sock "$VM_SOCKET" \
    --config-file "$VM_CONFIG" \
    > "$VM_DIR/console.log" 2>&1 &

echo $! > "$VM_DIR/firecracker.pid"
ok "Firecracker gestartet (PID $(cat "$VM_DIR/firecracker.pid"))."

# ── Zusammenfassung ───────────────────────────────────────────────────────────

# Kurz warten, damit Fehlermeldungen im Log landen, bevor wir die Meldung zeigen
sleep 1

# Prüfen, ob der Prozess noch läuft (sofortiger Absturz erkennbar)
if ! vm_is_running; then
    echo ""
    echo "FEHLER: VM '$NAME' ist sofort abgestürzt."
    echo "Letztes Konsolenlog:"
    tail -20 "$VM_DIR/console.log" || true
    echo ""
    echo "Firecracker-Log:"
    tail -20 "$VM_DIR/firecracker.log" 2>/dev/null || true
    exit 1
fi

GUEST_IP=$(cat "$VM_DIR/guest_ip")

echo ""
echo "════════════════════════════════════════════════════════"
echo " VM '$NAME' gestartet"
echo "════════════════════════════════════════════════════════"
echo " vCPUs:       $VCPUS"
echo " RAM:         ${MEM_MIB} MiB"
echo " Disk:        ${DISK_GB} GB"
echo " IP (Gast):   $GUEST_IP"
echo " IP (Host):   $(cat "$VM_DIR/host_ip")"
echo ""
HOST_USER=$(cat "$VM_DIR/host_user" 2>/dev/null || echo "root")
echo " SSH (nach Boot, ca. 3-5 Sek.):"
echo "   ssh ${HOST_USER}@${GUEST_IP}"
echo ""
echo " Konsolenausgabe live verfolgen:"
echo "   tail -f $VM_DIR/console.log"
echo ""
echo " VM stoppen:"
echo "   kill \$(cat $VM_DIR/firecracker.pid)"
echo "════════════════════════════════════════════════════════"

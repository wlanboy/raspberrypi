#!/bin/bash
# firecracker.sh – Einmalige Einrichtung der Firecracker-Host-Umgebung
#
# Idempotent: kann beliebig oft ausgeführt werden; bereits vorhandene
# Komponenten werden erkannt und übersprungen.
#
# Voraussetzungen: Ubuntu 22.04 / 24.04, sudo-Rechte, KVM-fähige CPU
#
# Verzeichnisstruktur nach dem Lauf:
#   $FC_DIR/
#     firecracker.version  – Gecachte Firecracker-Version
#     vmlinux              – Kernel-Binärdatei für alle VMs
#     kernel.version       – Kernel-Version (Idempotenz-Check)
#     kernel.key           – S3-Key des Kernels (Download-Cache)
#     base.ext4            – Goldenes Root-Image (Vorlage für addserver.sh)
#     rootfs.version       – Ubuntu-Version des Rootfs (Idempotenz-Check)
#     ubuntu.key           – S3-Key des Ubuntu-Rootfs (Download-Cache)
#     vms/                 – Verzeichnis für laufende VM-Instanzen

set -euo pipefail

# ── Konfiguration ────────────────────────────────────────────────────────────

FC_VERSION="${FC_VERSION:-latest}"
FC_DIR="${FC_DIR:-$HOME/firecracker}"
FC_BINARY="/usr/local/bin/firecracker"
FC_VERSION_FILE="$FC_DIR/firecracker.version"
ARCH=$(uname -m)

BASE_DISK_SIZE="5G"

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
skip() { echo "[$(date '+%H:%M:%S')] – übersprungen: $*"; }
warn() { echo "[$(date '+%H:%M:%S')] ! $*" >&2; }
err()  { echo "[$(date '+%H:%M:%S')] FEHLER: $*" >&2; exit 1; }

require_sudo() { sudo -v; }

# Sicherungskopie einer Datei vor Veränderung (ohne sudo)
backup() {
    local f="$1"
    if [ -f "$f" ]; then
        local ts; ts=$(date '+%Y%m%d-%H%M%S')
        cp -a "$f" "${f}.bak.${ts}"
        log "Backup erstellt: ${f}.bak.${ts}"
    fi
}

# Sicherungskopie einer Datei vor Veränderung (mit sudo)
sudo_backup() {
    local f="$1"
    if [ -f "$f" ]; then
        local ts; ts=$(date '+%Y%m%d-%H%M%S')
        sudo cp -a "$f" "${f}.bak.${ts}"
        log "Backup erstellt: ${f}.bak.${ts}"
    fi
}

# ── Reset-Modus ───────────────────────────────────────────────────────────────
#
# ./firecracker.sh --reset
#   Beendet laufende VMs, löst alle Loop-Mounts, entfernt FC_DIR und Binary.

RESET_MODE=0
for _arg in "$@"; do [ "$_arg" = "--reset" ] && RESET_MODE=1; done

reset_environment() {
    log "Reset: Stoppe laufende Firecracker-Prozesse..."
    if pgrep -x firecracker &>/dev/null; then
        sudo pkill -x firecracker || true
        sleep 2
        pgrep -x firecracker &>/dev/null && warn "Einige Firecracker-Prozesse laufen noch – fortfahren trotzdem."
    else
        skip "Keine laufenden Firecracker-Prozesse."
    fi

    log "Reset: Löse alle Mounts und Loop-Devices für Images in $FC_DIR..."
    if [ -d "$FC_DIR" ]; then
        while IFS= read -r img; do
            while IFS= read -r loopdev; do
                [ -z "$loopdev" ] && continue
                awk -v d="$loopdev" '$1==d {print $2}' /proc/mounts \
                    | xargs -r sudo umount -l 2>/dev/null || true
                sudo losetup -d "$loopdev" 2>/dev/null || true
                log "  Getrennt: $loopdev ($img)"
            done < <(sudo losetup -j "$img" 2>/dev/null | cut -d: -f1)
        done < <(find "$FC_DIR" -name "*.ext4" 2>/dev/null)

        grep "$FC_DIR" /proc/mounts 2>/dev/null \
            | awk '{print $2}' | sort -r \
            | xargs -r sudo umount -l 2>/dev/null || true
    fi

    log "Reset: Entferne $FC_DIR und $FC_BINARY..."
    sudo rm -rf "$FC_DIR"
    sudo rm -f  "$FC_BINARY"

    ok "Reset abgeschlossen – Neuaufbau startet."
    echo ""
}

if [ "$RESET_MODE" = "1" ]; then
    require_sudo
    reset_environment
fi

# ── 0. Verzeichnisstruktur vorbereiten ──────────────────────────────────────
# Muss vor allen anderen Schritten erfolgen, da Versionsdateien in FC_DIR liegen.

mkdir -p "$FC_DIR/vms"

# ── 1. KVM-Zugriff prüfen ────────────────────────────────────────────────────

log "Prüfe KVM-Zugriff..."

if [ ! -e /dev/kvm ]; then
    sudo modprobe kvm
    sudo modprobe kvm_intel 2>/dev/null || sudo modprobe kvm_amd 2>/dev/null || true
fi

if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
    log "Füge $USER zur Gruppe kvm hinzu – bitte danach neu anmelden."
    sudo usermod -aG kvm "$USER"
    sudo chmod o+rw /dev/kvm
fi

ok "KVM verfügbar."

# ── 2. Abhängigkeiten installieren ──────────────────────────────────────────

log "Prüfe System-Pakete..."

PACKAGES=(curl jq e2fsprogs squashfs-tools)
TO_INSTALL=()
for pkg in "${PACKAGES[@]}"; do
    dpkg -s "$pkg" &>/dev/null || TO_INSTALL+=("$pkg")
done

if [ ${#TO_INSTALL[@]} -gt 0 ]; then
    log "Installiere: ${TO_INSTALL[*]}"
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${TO_INSTALL[@]}"
    ok "Pakete installiert: ${TO_INSTALL[*]}"
else
    skip "Alle Pakete bereits installiert."
fi

# ── 3. Firecracker-Binary installieren ──────────────────────────────────────

log "Prüfe Firecracker-Binary..."

if [ "$FC_VERSION" = "latest" ]; then
    FC_VERSION=$(basename "$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
        "https://github.com/firecracker-microvm/firecracker/releases/latest")")
    log "Neueste Version: $FC_VERSION"
fi

INSTALLED_VERSION=""
if [ -f "$FC_VERSION_FILE" ]; then
    INSTALLED_VERSION=$(cat "$FC_VERSION_FILE")
elif command -v firecracker &>/dev/null; then
    INSTALLED_VERSION=$(firecracker --version 2>&1 | grep -oP 'v[\d.]+' | head -1 || true)
fi

if [ "$INSTALLED_VERSION" = "$FC_VERSION" ] && [ -x "$FC_BINARY" ]; then
    skip "Firecracker $FC_VERSION bereits installiert."
else
    log "Lade Firecracker $FC_VERSION herunter..."
    TGZ_URL="https://github.com/firecracker-microvm/firecracker/releases/download/${FC_VERSION}/firecracker-${FC_VERSION}-${ARCH}.tgz"
    TGZ_TMP="/tmp/firecracker-${FC_VERSION}.tgz"
    EXTRACT_DIR="/tmp/firecracker-extract-$$"

    sudo_backup "$FC_BINARY"

    curl -fsSL "$TGZ_URL" -o "$TGZ_TMP"
    mkdir -p "$EXTRACT_DIR"
    tar -xzf "$TGZ_TMP" -C "$EXTRACT_DIR"
    sudo mv "${EXTRACT_DIR}/release-${FC_VERSION}-${ARCH}/firecracker-${FC_VERSION}-${ARCH}" "$FC_BINARY"
    sudo chmod +x "$FC_BINARY"
    rm -rf "$TGZ_TMP" "$EXTRACT_DIR"

    echo "$FC_VERSION" > "$FC_VERSION_FILE"
    ok "Firecracker $FC_VERSION installiert: $FC_BINARY"
fi

# ── 4. Pfade für Artefakte definieren ───────────────────────────────────────

CI_VERSION="${FC_VERSION%.*}"
S3_BASE="http://spec.ccfc.min.s3.amazonaws.com"
S3_HTTPS="https://s3.amazonaws.com/spec.ccfc.min"

VMLINUX="$FC_DIR/vmlinux"
KERNEL_VERSION_FILE="$FC_DIR/kernel.version"
KERNEL_KEY_FILE="$FC_DIR/kernel.key"

BASE_ROOTFS="$FC_DIR/base.ext4"
ROOTFS_VERSION_FILE="$FC_DIR/rootfs.version"
UBUNTU_KEY_FILE="$FC_DIR/ubuntu.key"

# ── 5. CI-Versionen ermitteln ────────────────────────────────────────────────
#
# S3-Abfragen werden übersprungen wenn alle lokalen Artefakte vorhanden sind
# und die gecachten Keys zur aktuellen CI-Version passen.

KERNEL_VERSION=""
KERNEL_KEY=""
UBUNTU_VERSION=""
UBUNTU_KEY=""
_needs_s3=0

if [ -f "$KERNEL_KEY_FILE" ] && [ -f "$KERNEL_VERSION_FILE" ] && [ -f "$VMLINUX" ]; then
    _cached_key=$(cat "$KERNEL_KEY_FILE")
    if [[ "$_cached_key" == *"${CI_VERSION}"* ]]; then
        KERNEL_KEY="$_cached_key"
        KERNEL_VERSION=$(cat "$KERNEL_VERSION_FILE")
    else
        _needs_s3=1
    fi
else
    _needs_s3=1
fi

if [ -f "$UBUNTU_KEY_FILE" ] && [ -f "$ROOTFS_VERSION_FILE" ] && [ -f "$BASE_ROOTFS" ]; then
    _cached_key=$(cat "$UBUNTU_KEY_FILE")
    if [[ "$_cached_key" == *"${CI_VERSION}"* ]]; then
        UBUNTU_KEY="$_cached_key"
        UBUNTU_VERSION=$(cat "$ROOTFS_VERSION_FILE")
    else
        _needs_s3=1
    fi
else
    _needs_s3=1
fi

if [ "$_needs_s3" = "0" ]; then
    skip "CI-Artefakte aus Cache: Kernel ${KERNEL_VERSION}, Ubuntu ${UBUNTU_VERSION}"
else
    log "Ermittle CI-Artefakte für Firecracker ${FC_VERSION} (CI: ${CI_VERSION})..."

    KERNEL_KEY=$(curl -fsSL \
        "${S3_BASE}/?prefix=firecracker-ci/${CI_VERSION}/${ARCH}/vmlinux-&list-type=2" \
        | grep -oP "(?<=<Key>)(firecracker-ci/${CI_VERSION}/${ARCH}/vmlinux-[0-9]+\.[0-9]+\.[0-9]{1,3})(?=</Key>)" \
        | sort -V | tail -1)
    [ -n "$KERNEL_KEY" ] || err "Kein Kernel im CI-Bucket für ${CI_VERSION}/${ARCH} gefunden."
    KERNEL_VERSION=$(basename "$KERNEL_KEY")

    UBUNTU_KEY=$(curl -fsSL \
        "${S3_BASE}/?prefix=firecracker-ci/${CI_VERSION}/${ARCH}/ubuntu-&list-type=2" \
        | grep -oP "(?<=<Key>)(firecracker-ci/${CI_VERSION}/${ARCH}/ubuntu-[0-9]+\.[0-9]+\.squashfs)(?=</Key>)" \
        | sort -V | tail -1)
    [ -n "$UBUNTU_KEY" ] || err "Kein Ubuntu-Rootfs im CI-Bucket für ${CI_VERSION}/${ARCH} gefunden."
    UBUNTU_VERSION=$(basename "$UBUNTU_KEY" .squashfs | grep -oE '[0-9]+\.[0-9]+')

    echo "$KERNEL_KEY"   > "$KERNEL_KEY_FILE"
    echo "$UBUNTU_KEY"   > "$UBUNTU_KEY_FILE"

    ok "Kernel: ${KERNEL_VERSION}, Ubuntu: ${UBUNTU_VERSION}"
fi

# ── 6. Kernel herunterladen ─────────────────────────────────────────────────

if [ -f "$VMLINUX" ] && [ "$(cat "$KERNEL_VERSION_FILE" 2>/dev/null)" = "$KERNEL_VERSION" ]; then
    skip "Kernel bereits vorhanden: $KERNEL_VERSION"
else
    log "Lade Kernel herunter: $KERNEL_VERSION..."
    backup "$VMLINUX"
    curl -fsSL --progress-bar "${S3_HTTPS}/${KERNEL_KEY}" -o "$VMLINUX"
    echo "$KERNEL_VERSION" > "$KERNEL_VERSION_FILE"
    ok "Kernel gespeichert: $VMLINUX"
fi

# ── 7. Basis-Rootfs erstellen ────────────────────────────────────────────────
#
# Das CI-Ubuntu-Squashfs wird entpackt, konfiguriert und als ext4 gespeichert.
# addserver.sh kopiert dieses goldene Image und passt es pro VM an.

_base_ok=0
if [ -f "$BASE_ROOTFS" ] && [ "$(cat "$ROOTFS_VERSION_FILE" 2>/dev/null)" = "$UBUNTU_VERSION" ]; then
    _tmp_check=$(mktemp -d)
    if sudo mount -t ext4 -o loop,ro "$BASE_ROOTFS" "$_tmp_check" 2>/dev/null; then
        if [ -f "$_tmp_check/etc/os-release" ] && [ -x "$_tmp_check/bin/bash" ]; then
            _base_ok=1
        fi
        sudo umount "$_tmp_check"
    fi
    rmdir "$_tmp_check"
fi

if [ "$_base_ok" = "1" ]; then
    skip "Basis-Rootfs bereits vorhanden: base.ext4 (Ubuntu ${UBUNTU_VERSION})"
else
    [ -f "$BASE_ROOTFS" ] && log "Basis-Rootfs veraltet oder beschädigt – wird neu erstellt..."
    log "Erstelle Basis-Rootfs aus Ubuntu ${UBUNTU_VERSION} (CI-Image)..."

    TMP_DIR=$(mktemp -d)
    MOUNT_DIR=$(mktemp -d)
    trap 'sudo umount "$MOUNT_DIR" 2>/dev/null || true; sudo rm -rf "$TMP_DIR" "$MOUNT_DIR"' EXIT

    CACHE_SQUASHFS="$FC_DIR/ubuntu-${UBUNTU_VERSION}.squashfs"

    if [ -f "$CACHE_SQUASHFS" ]; then
        log "Nutze vorhandenes Squashfs aus Cache: $CACHE_SQUASHFS"
        cp "$CACHE_SQUASHFS" "$TMP_DIR/ubuntu.squashfs"
    else
        log "Lade Ubuntu-Squashfs herunter (${UBUNTU_VERSION})..."
        curl -fsSL --progress-bar "${S3_HTTPS}/${UBUNTU_KEY}" -o "$CACHE_SQUASHFS"
        cp "$CACHE_SQUASHFS" "$TMP_DIR/ubuntu.squashfs"
    fi

    log "Entpacke Squashfs..."
    sudo unsquashfs -d "$TMP_DIR/rootfs" "$TMP_DIR/ubuntu.squashfs" \
        || err "unsquashfs fehlgeschlagen – squashfs-tools installiert?"

    log "Konfiguriere Basis-Image (chroot)..."
    sudo chroot "$TMP_DIR/rootfs" /bin/bash <<'CHROOT'
set -e

mkdir -p /etc/ssh /etc/systemd/network /etc/sudoers.d

echo "root:root" | chpasswd

mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-firecracker.conf <<'SSHCFG'
PermitRootLogin yes
PasswordAuthentication yes
SSHCFG

systemctl enable ssh  2>/dev/null || \
systemctl enable sshd 2>/dev/null || true

systemctl enable systemd-networkd

# systemd-resolved verhindert DNS in der MicroVM (kein D-Bus, kein Stub-Resolver).
systemctl mask systemd-resolved 2>/dev/null || true
echo -e "nameserver 8.8.8.8\nnameserver 1.1.1.1" > /etc/resolv.conf

mkdir -p /etc/systemd/network
cat > /etc/systemd/network/20-eth0.network <<'NET'
[Match]
Name=eth0

[Network]
DHCP=yes
NET

mkdir -p /etc/systemd/system/getty@ttyS0.service.d
cat > /etc/systemd/system/getty@ttyS0.service.d/override.conf <<'GETTY'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --keep-baud ttyS0 115200 vt100
GETTY

echo "/dev/vda / ext4 defaults,noatime 0 1" > /etc/fstab

# SSH Host-Keys entfernen – jede VM generiert beim Start eigene Keys
rm -f /etc/ssh/ssh_host_*

# Entropy-Seeding via virtio-rng (/dev/hwrng) vor dem SSH-Start.
cat > /etc/systemd/system/seed-entropy.service <<'SVC'
[Unit]
Description=Seed kernel entropy pool from virtio-rng
DefaultDependencies=no
Before=ssh.service ssh.socket sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'dd if=/dev/hwrng of=/dev/random bs=512 count=1 2>/dev/null || true'
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
SVC

systemctl enable seed-entropy.service
CHROOT

    log "Erstelle ext4-Image (${BASE_DISK_SIZE})..."
    backup "$BASE_ROOTFS"
    truncate -s "$BASE_DISK_SIZE" "$BASE_ROOTFS"
    sudo mkfs.ext4 -q -F "$BASE_ROOTFS"

    sudo mount -t ext4 -o loop "$BASE_ROOTFS" "$MOUNT_DIR" \
        || err "Konnte ext4-Image nicht mounten."
    sudo cp -a "$TMP_DIR/rootfs/." "$MOUNT_DIR/"
    sudo umount "$MOUNT_DIR"

    trap - EXIT
    sudo rm -rf "$TMP_DIR" "$MOUNT_DIR"

    echo "$UBUNTU_VERSION" > "$ROOTFS_VERSION_FILE"
    ok "Basis-Rootfs erstellt: $BASE_ROOTFS (Ubuntu ${UBUNTU_VERSION}, Kernel ${KERNEL_VERSION})"
fi

# ── 8. IP-Forwarding dauerhaft aktivieren ───────────────────────────────────

log "Aktiviere IP-Forwarding..."

SYSCTL_FILE="/etc/sysctl.d/99-firecracker.conf"
if [ ! -f "$SYSCTL_FILE" ]; then
    sudo tee "$SYSCTL_FILE" > /dev/null <<'EOF'
net.ipv4.ip_forward = 1
EOF
    ok "IP-Forwarding-Konfiguration geschrieben."
else
    skip "sysctl-Konfiguration bereits vorhanden."
fi

if [ "$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)" != "1" ]; then
    sudo sysctl -p "$SYSCTL_FILE" > /dev/null
    ok "IP-Forwarding aktiviert."
else
    skip "IP-Forwarding bereits aktiv."
fi

# ── 9. Zusammenfassung ───────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════"
echo " Firecracker-Umgebung ist bereit"
echo "════════════════════════════════════════════════════════"
echo " Firecracker:  $FC_BINARY ($FC_VERSION)"
echo " Kernel:       $VMLINUX ($KERNEL_VERSION)"
echo " Basis-Image:  $BASE_ROOTFS (Ubuntu ${UBUNTU_VERSION})"
echo " VMs:          $FC_DIR/vms/"
echo ""
echo " Neue VM starten:"
echo "   ./addserver.sh <name> [vcpus] [mem_mib] [disk_gb]"
echo "   Beispiel: ./addserver.sh web01 2 1024 10"
echo "════════════════════════════════════════════════════════"

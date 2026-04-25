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
#     vmlinux          – Kernel-Binärdatei für alle VMs
#     base.ext4        – Goldenes Root-Image (Vorlage für addserver.sh)
#     vms/             – Verzeichnis für laufende VM-Instanzen

set -euo pipefail

# ── Konfiguration ────────────────────────────────────────────────────────────

# Konkrete Version; überschreibbar mit: FC_VERSION="v1.9.0" ./firecracker.sh
# "latest" löst automatisch die neueste Version über die GitHub-API auf.
FC_VERSION="${FC_VERSION:-v1.15.1}"
FC_DIR="${FC_DIR:-$HOME/firecracker}"
FC_BINARY="/usr/local/bin/firecracker"
ARCH=$(uname -m)   # x86_64 oder aarch64

# Kernel von Firecrackers öffentlichem S3-Bucket (getestet mit v1.15.x)
KERNEL_URL="https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/${ARCH}/kernels/vmlinux.bin"

# Ubuntu-Release für das Basis-Image
UBUNTU_RELEASE="noble"          # 24.04 LTS
UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu/"

# Basisgröße des goldenen Images (wird von addserver.sh pro VM angepasst)
BASE_DISK_SIZE="3G"

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
skip() { echo "[$(date '+%H:%M:%S')] – übersprungen: $*"; }

require_sudo() {
    # Sicherstellen, dass sudo-Credentials gecacht sind, damit spätere
    # Befehle nicht interaktiv fragen.
    sudo -v
}

# ── 1. KVM-Zugriff prüfen ────────────────────────────────────────────────────

log "Prüfe KVM-Zugriff..."

if [ ! -e /dev/kvm ]; then
    # Kernel-Modul laden, falls KVM-Device fehlt
    sudo modprobe kvm
    sudo modprobe kvm_intel 2>/dev/null || sudo modprobe kvm_amd 2>/dev/null || true
fi

if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
    log "Füge $USER zur Gruppe kvm hinzu – bitte danach neu anmelden."
    sudo usermod -aG kvm "$USER"
    # In der aktuellen Session sofort Zugriff gewähren ohne Re-Login
    sudo chmod o+rw /dev/kvm
fi

ok "KVM verfügbar."

# ── 2. Abhängigkeiten installieren ──────────────────────────────────────────

log "Prüfe System-Pakete..."

# Nur fehlende Pakete installieren; dpkg -s liefert Exit 0 wenn installiert
PACKAGES=(debootstrap e2fsprogs curl qemu-utils)
TO_INSTALL=()
for pkg in "${PACKAGES[@]}"; do
    dpkg -s "$pkg" &>/dev/null || TO_INSTALL+=("$pkg")
done

if [ ${#TO_INSTALL[@]} -gt 0 ]; then
    log "Installiere: ${TO_INSTALL[*]}"
    # DEBIAN_FRONTEND=noninteractive verhindert interaktive Dialoge (z. B. Zeitzone)
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${TO_INSTALL[@]}"
    ok "Pakete installiert: ${TO_INSTALL[*]}"
else
    skip "Alle Pakete bereits installiert."
fi

# ── 3. Firecracker-Binary installieren ──────────────────────────────────────

log "Prüfe Firecracker-Binary..."

# "latest" zur konkreten Versions-Tag auflösen (z. B. "v1.9.1")
if [ "$FC_VERSION" = "latest" ]; then
    FC_VERSION=$(curl -fsSL \
        "https://api.github.com/repos/firecracker-microvm/firecracker/releases/latest" \
        | grep '"tag_name"' | cut -d'"' -f4)
    log "Neueste Version: $FC_VERSION"
fi

INSTALLED_VERSION=""
if command -v firecracker &>/dev/null; then
    INSTALLED_VERSION=$(firecracker --version 2>&1 | grep -oP 'v[\d.]+' | head -1 || true)
fi

if [ "$INSTALLED_VERSION" = "$FC_VERSION" ]; then
    skip "Firecracker $FC_VERSION bereits installiert."
else
    log "Lade Firecracker $FC_VERSION herunter..."

    # Releases werden als .tgz-Archiv ausgeliefert.
    # Inhalt: release-<version>-<arch>/firecracker-<version>-<arch>
    TGZ_URL="https://github.com/firecracker-microvm/firecracker/releases/download/${FC_VERSION}/firecracker-${FC_VERSION}-${ARCH}.tgz"
    TGZ_TMP="/tmp/firecracker-${FC_VERSION}.tgz"
    EXTRACT_DIR="/tmp/firecracker-extract-$$"

    curl -fsSL "$TGZ_URL" -o "$TGZ_TMP"
    mkdir -p "$EXTRACT_DIR"
    tar -xzf "$TGZ_TMP" -C "$EXTRACT_DIR"

    # Binary aus dem Unterverzeichnis im Archiv holen
    sudo mv "${EXTRACT_DIR}/release-${FC_VERSION}-${ARCH}/firecracker-${FC_VERSION}-${ARCH}" "$FC_BINARY"
    sudo chmod +x "$FC_BINARY"

    rm -rf "$TGZ_TMP" "$EXTRACT_DIR"
    ok "Firecracker $FC_VERSION installiert: $FC_BINARY"
fi

# ── 4. Verzeichnisstruktur anlegen ──────────────────────────────────────────

log "Verzeichnisstruktur in $FC_DIR anlegen..."
mkdir -p "$FC_DIR/vms"
ok "Verzeichnis $FC_DIR bereit."

# ── 5. Kernel herunterladen ─────────────────────────────────────────────────

VMLINUX="$FC_DIR/vmlinux"

if [ -f "$VMLINUX" ]; then
    skip "Kernel bereits vorhanden: $VMLINUX"
else
    log "Lade Firecracker-Kernel herunter (vmlinux)..."
    curl -fsSL "$KERNEL_URL" -o "$VMLINUX"
    ok "Kernel gespeichert: $VMLINUX"
fi

# ── 6. Basis-Rootfs erstellen ────────────────────────────────────────────────
#
# Dieses "goldene" Image dient als Vorlage. addserver.sh kopiert es und
# passt Hostname sowie Netzwerk an. Das Original bleibt unverändert.

BASE_ROOTFS="$FC_DIR/base.ext4"

_base_ok=0
if [ -f "$BASE_ROOTFS" ]; then
    # Prüfen ob das Image tatsächlich ein befülltes Rootfs enthält (nicht nur mkfs).
    _tmp_check=$(mktemp -d)
    if sudo mount -t ext4 -o loop,ro "$BASE_ROOTFS" "$_tmp_check" 2>/dev/null; then
        [ -d "$_tmp_check/etc" ] && _base_ok=1
        sudo umount "$_tmp_check"
    fi
    rmdir "$_tmp_check"
fi

if [ "$_base_ok" = "1" ]; then
    skip "Basis-Rootfs bereits vorhanden: $BASE_ROOTFS"
else
    [ -f "$BASE_ROOTFS" ] && log "Basis-Rootfs unvollständig – wird neu erstellt..."
    log "Erstelle Basis-Rootfs (debootstrap, dauert einige Minuten)..."

    # Hängende Loop-Devices vom vorherigen Fehlversuch bereinigen
    sudo losetup -j "$BASE_ROOTFS" 2>/dev/null | cut -d: -f1 | xargs -r sudo losetup -d

    # Sparse-Datei anlegen; -F überspringt den interaktiven Überschreib-Dialog
    truncate -s "$BASE_DISK_SIZE" "$BASE_ROOTFS"
    mkfs.ext4 -q -F "$BASE_ROOTFS"

    MOUNT_DIR=$(mktemp -d)
    sudo mount -t ext4 -o loop "$BASE_ROOTFS" "$MOUNT_DIR"

    log "Führe debootstrap aus (${UBUNTU_RELEASE})..."
    sudo debootstrap "$UBUNTU_RELEASE" "$MOUNT_DIR" "$UBUNTU_MIRROR"

    log "Konfiguriere Basis-Image (chroot)..."
    sudo chroot "$MOUNT_DIR" /bin/bash <<'CHROOT'
set -e

# Vollständige sources.list mit updates und security setzen;
# debootstrap erzeugt nur "noble main" – damit fehlen viele Pakete.
cat > /etc/apt/sources.list <<'SOURCES'
deb http://archive.ubuntu.com/ubuntu noble main restricted universe
deb http://archive.ubuntu.com/ubuntu noble-updates main restricted universe
deb http://archive.ubuntu.com/ubuntu noble-security main restricted universe
SOURCES

# Paketliste aktualisieren und essentielle Pakete installieren.
# --no-install-recommends hält das Image klein.
apt-get update -q
apt-get install -y -q --no-install-recommends \
    iproute2 \
    iputils-ping \
    curl \
    ca-certificates \
    openssh-server \
    systemd-networkd \
    systemd-resolved

# Root-Passwort (nur für Entwicklung; in Produktion SSH-Key verwenden)
echo "root:root" | chpasswd

# SSH-Root-Login aktivieren
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl enable ssh

# systemd-networkd als Netzwerkdienst registrieren.
# Die eigentliche Konfiguration (IP, Gateway) schreibt addserver.sh vor
# dem ersten Start in das kopierte Image.
systemctl enable systemd-networkd
systemctl enable systemd-resolved

# Seriellen Konsolen-Login ohne Passwort-Prompt.
# Firecracker leitet stdout/stderr auf ttyS0 um – ohne diesen Override
# bleibt getty auf einem interaktiven Login-Prompt hängen.
mkdir -p /etc/systemd/system/getty@ttyS0.service.d
cat > /etc/systemd/system/getty@ttyS0.service.d/override.conf <<'GETTY'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --keep-baud ttyS0 115200 vt100
GETTY

# fstab: Firecracker stellt das Root-Device immer als /dev/vda bereit
echo "/dev/vda / ext4 defaults,noatime 0 1" > /etc/fstab

CHROOT

    sudo umount "$MOUNT_DIR"
    rmdir "$MOUNT_DIR"
    ok "Basis-Rootfs erstellt: $BASE_ROOTFS"
fi

# ── 7. IP-Forwarding dauerhaft aktivieren ───────────────────────────────────
#
# Ohne ip_forward=1 werden Pakete, die von der VM kommen, nicht an das
# externe Interface weitergeleitet – kein Internet-Zugriff aus der VM.

log "Aktiviere IP-Forwarding..."

SYSCTL_FILE="/etc/sysctl.d/99-firecracker.conf"
if [ -f "$SYSCTL_FILE" ]; then
    skip "sysctl-Konfiguration bereits vorhanden."
else
    sudo tee "$SYSCTL_FILE" > /dev/null <<'EOF'
# Aktiviert durch firecracker.sh – benötigt für VM-Netzwerk
net.ipv4.ip_forward = 1
EOF
    sudo sysctl -p "$SYSCTL_FILE"
    ok "IP-Forwarding aktiviert."
fi

# ── 8. Zusammenfassung ───────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════"
echo " Firecracker-Umgebung ist bereit"
echo "════════════════════════════════════════════════════════"
echo " Firecracker:  $FC_BINARY ($FC_VERSION)"
echo " Kernel:       $VMLINUX"
echo " Basis-Image:  $BASE_ROOTFS"
echo " VMs:          $FC_DIR/vms/"
echo ""
echo " Neue VM starten:"
echo "   ./addserver.sh <name> [vcpus] [mem_mib] [disk_gb]"
echo "   Beispiel: ./addserver.sh web01 2 1024 10"
echo "════════════════════════════════════════════════════════"

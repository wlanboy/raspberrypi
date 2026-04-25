# Firecracker auf Ubuntu Server – Vollständige Anleitung

Firecracker ist ein schlanker VMM (Virtual Machine Monitor) von AWS, der auf KVM aufbaut und
MicroVMs in Millisekunden startet. Diese Anleitung richtet eine vollständige Firecracker-Umgebung
auf Ubuntu 22.04 / 24.04 LTS ein, inklusive Netzwerk, Root-Dateisystem und Startkonfiguration.

---

## 1. Voraussetzungen prüfen

### Hardware-Virtualisierung und KVM-Zugriff

```bash
# CPU muss Intel VT-x oder AMD-V unterstützen
egrep -c '(vmx|svm)' /proc/cpuinfo
# Ergebnis > 0 bedeutet: Virtualisierung aktiv

# KVM-Kernel-Module laden (falls noch nicht aktiv)
sudo modprobe kvm
sudo modprobe kvm_intel   # Intel
# sudo modprobe kvm_amd   # AMD

# Zugriffsrechte auf /dev/kvm prüfen
# Ausgabe "Bereit!" = alles ok, sonst fehlt Benutzer in Gruppe kvm
[ -r /dev/kvm ] && [ -w /dev/kvm ] && echo "Bereit!" || echo "KVM Zugriff fehlt"

# Aktuellen Benutzer zur kvm-Gruppe hinzufügen (einmalig, danach neu anmelden)
sudo usermod -aG kvm $USER
```

### Abhängigkeiten installieren

```bash
# debootstrap: erzeugt ein minimales Ubuntu-Rootfs
# qemu-utils: stellt qemu-img für Image-Operationen bereit (optional)
sudo apt update && sudo apt install -y debootstrap qemu-utils curl
```

---

## 2. Firecracker-Binary installieren

```bash
# Aktuelle Releaseversion – bei Bedarf anpassen:
# https://github.com/firecracker-microvm/firecracker/releases
RELEASE_VERSION="v1.15.1"
RELEASE_URL="https://github.com/firecracker-microvm/firecracker/releases/download/${RELEASE_VERSION}"

# Architektur automatisch ermitteln (x86_64 oder aarch64)
ARCH=$(uname -m)

# Binary herunterladen und ausführbar machen
curl -L "${RELEASE_URL}/firecracker-${RELEASE_VERSION}-${ARCH}" -o firecracker
chmod +x firecracker

# Systemweit verfügbar machen
sudo mv firecracker /usr/local/bin/

# Installation prüfen
firecracker --version
```

---

## 3. Kernel herunterladen

Firecracker benötigt einen Linux-Kernel als flache Binärdatei (`vmlinux`), kein komprimiertes Image.
Die Firecracker-Entwickler stellen vorgefertigte Kernel über ihren S3-Bucket bereit.

```bash
ARCH=$(uname -m)
KERNEL_DIR="$HOME/firecracker"
mkdir -p "$KERNEL_DIR"

# Vorgefertigten Quickstart-Kernel herunterladen (empfohlen für den Einstieg)
curl -L \
  "https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/${ARCH}/kernels/vmlinux.bin" \
  -o "${KERNEL_DIR}/vmlinux"

# Alternativ: Kernel aus dem Firecracker-CI (spezifische Version)
# curl -L \
#   "https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.10/${ARCH}/vmlinux-6.1.102" \
#   -o "${KERNEL_DIR}/vmlinux"
```

---

## 4. Root-Dateisystem (rootfs) erstellen

Das Root-Dateisystem ist eine einfache ext4-Datei, die wie eine Festplatte in die VM eingehängt wird.

```bash
ROOTFS="${KERNEL_DIR}/ubuntu-rootfs.ext4"

# Leere 5-GB-Datei anlegen (sparse, belegt keinen echten Speicher sofort)
truncate -s 5G "$ROOTFS"

# Als ext4-Dateisystem formatieren
mkfs.ext4 "$ROOTFS"

# Temporäres Mountpoint-Verzeichnis anlegen
sudo mkdir -p /tmp/ubuntu-rootfs

# Image einhängen, damit wir es befüllen können
sudo mount "$ROOTFS" /tmp/ubuntu-rootfs

# Minimales Ubuntu 24.04 (noble) installieren
# Dieser Schritt lädt ~300 MB und dauert einige Minuten
sudo debootstrap noble /tmp/ubuntu-rootfs http://archive.ubuntu.com/ubuntu/
```

### Rootfs konfigurieren (im chroot)

```bash
sudo chroot /tmp/ubuntu-rootfs /bin/bash <<'EOF'

# --- Benutzer und Authentifizierung ---
# Root-Passwort setzen (für Testzwecke; in Produktion SSH-Keys verwenden)
echo "root:root" | chpasswd

# --- Pakete installieren ---
apt-get update -q
# Netzwerk-Tools, curl für k3s-Installation, SSH-Server, systemd-Netzwerkverwaltung
apt-get install -y --no-install-recommends \
    iproute2 iputils-ping curl ca-certificates \
    openssh-server systemd-networkd

# --- Hostname setzen ---
echo "firecracker-vm" > /etc/hostname

# Hosts-Datei anpassen, damit der Hostname lokal auflösbar ist
cat > /etc/hosts <<HOSTS
127.0.0.1   localhost
127.0.1.1   firecracker-vm
HOSTS

# --- Netzwerk: statische IP für eth0 ---
# Firecracker hat kein DHCP, daher statische Konfiguration notwendig.
# Die IP 172.16.0.2 gehört zur VM, 172.16.0.1 ist das Host-Gateway (tap0).
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/20-eth0.network <<NET
[Match]
Name=eth0

[Network]
Address=172.16.0.2/24
Gateway=172.16.0.1
DNS=8.8.8.8
NET

# systemd-networkd als Netzwerkdienst aktivieren
systemctl enable systemd-networkd

# --- Serielle Konsole: automatischer Root-Login ---
# Firecracker leitet die VM-Ausgabe auf ttyS0 um.
# Ohne diesen Override blockiert getty auf einen Login-Prompt.
mkdir -p /etc/systemd/system/getty@ttyS0.service.d
cat > /etc/systemd/system/getty@ttyS0.service.d/override.conf <<GETTY
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --keep-baud ttyS0 115200 vt100
GETTY

# --- SSH: Root-Login erlauben (nur für Testzwecke) ---
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl enable ssh

# --- fstab: rootfs eintragen ---
# Firecracker stellt das Root-Device als /dev/vda bereit
echo "/dev/vda / ext4 defaults,noatime 0 1" > /etc/fstab

EOF
```

```bash
# Image aushängen
sudo umount /tmp/ubuntu-rootfs
sudo rmdir /tmp/ubuntu-rootfs

echo "Rootfs fertig: $ROOTFS"
```

---

## 5. Netzwerk auf dem Host konfigurieren

### TAP-Interface anlegen (temporär, geht nach Reboot verloren)

```bash
# tap0: virtuelles Netzwerkinterface, das Firecracker mit dem Host verbindet
sudo ip tuntap add dev tap0 mode tap

# IP-Adresse des Hosts im VM-Netzwerk (= Standard-Gateway für die VM)
sudo ip addr add 172.16.0.1/24 dev tap0

# Interface aktivieren
sudo ip link set tap0 up

# IP-Forwarding aktivieren (ermöglicht Routing zwischen tap0 und externem Interface)
sudo sysctl -w net.ipv4.ip_forward=1

# NAT: VM-Traffic über das externe Interface ins Internet weiterleiten.
# WICHTIG: 'eth0' durch das tatsächliche externe Interface ersetzen.
# Aktuelles Interface ermitteln: ip route get 8.8.8.8 | awk '{print $5; exit}'
EXTERNAL_IF=$(ip route get 8.8.8.8 | awk '{print $5; exit}')
sudo iptables -t nat -A POSTROUTING -o "$EXTERNAL_IF" -j MASQUERADE

echo "Netzwerk bereit. Externes Interface: $EXTERNAL_IF"
```

### TAP-Interface dauerhaft machen (systemd-networkd)

```bash
# netdev-Datei: definiert das TAP-Interface
sudo tee /etc/systemd/network/10-tap0.netdev > /dev/null <<'EOF'
[NetDev]
Name=tap0
Kind=tap

[Tap]
# Ohne User-Einschränkung: Interface für alle zugänglich
EOF

# network-Datei: konfiguriert die IP-Adresse
sudo tee /etc/systemd/network/10-tap0.network > /dev/null <<'EOF'
[Match]
Name=tap0

[Network]
Address=172.16.0.1/24
# IPMasquerade leitet Traffic automatisch weiter (ersetzt iptables-Regel)
IPMasquerade=ipv4
IPForward=yes
EOF

sudo systemctl enable --now systemd-networkd
```

---

## 6. Firecracker-Konfigurationsdatei erstellen

```bash
KERNEL_DIR="$HOME/firecracker"

cat > "${KERNEL_DIR}/config.json" <<EOF
{
  "boot-source": {
    "kernel_image_path": "${KERNEL_DIR}/vmlinux",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off nomodule ipv6.disable=1 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory ip=172.16.0.2::172.16.0.1:255.255.255.0::eth0:off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "${KERNEL_DIR}/ubuntu-rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 2028
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "AA:FC:00:00:00:01",
      "host_dev_name": "tap0"
    }
  ],
  "logger": {
    "log_path": "/tmp/firecracker.log",
    "level": "Info",
    "show_level": true,
    "show_log_origin": false
  }
}
EOF

echo "Konfiguration erstellt: ${KERNEL_DIR}/config.json"
```

**Erklärung der wichtigsten Boot-Argumente:**

| Argument | Bedeutung |
|---|---|
| `console=ttyS0` | Konsolenausgabe auf seriellen Port (von Firecracker lesbar) |
| `reboot=k` | Bei Kernel-Panic: sauber beenden statt neu starten |
| `panic=1` | Kernel-Panic nach 1 Sekunde auslösen statt zu hängen |
| `pci=off` | Kein PCI-Bus (Firecracker verwendet Virtio direkt) |
| `nomodule` | Keine Kernel-Module laden (nicht vorhanden im vmlinux) |
| `cgroup_enable=...` | Cgroup-Unterstützung für k3s aktivieren |
| `ip=...` | Netzwerkkonfiguration direkt per Kernel-Parameter setzen |

---

## 7. Firecracker starten

```bash
KERNEL_DIR="$HOME/firecracker"
SOCKET="/tmp/firecracker.socket"

# Alten Socket entfernen, falls vorhanden
rm -f "$SOCKET"

# Firecracker starten
# --api-sock: Unix-Socket für die REST-API (Steuerung über curl möglich)
# --config-file: alle Einstellungen aus JSON laden
firecracker \
  --api-sock "$SOCKET" \
  --config-file "${KERNEL_DIR}/config.json"
```

Die VM startet sofort und gibt ihre Konsolenausgabe direkt im Terminal aus.
Mit `Ctrl+C` wird die VM beendet.

### VM im Hintergrund starten

```bash
SOCKET="/tmp/firecracker.socket"
rm -f "$SOCKET"

# Im Hintergrund starten, Ausgabe in Logdatei umleiten
firecracker \
  --api-sock "$SOCKET" \
  --config-file "${KERNEL_DIR}/config.json" \
  > /tmp/firecracker-console.log 2>&1 &

FIRECRACKER_PID=$!
echo "Firecracker PID: $FIRECRACKER_PID"
echo "Konsolenlog: tail -f /tmp/firecracker-console.log"

# Warten bis die VM hochgefahren ist, dann per SSH verbinden
sleep 5
ssh root@172.16.0.2
```

---

## 8. VM über die REST-API steuern

Firecracker bietet eine HTTP-API über den Unix-Socket.
Damit lässt sich die VM auch nach dem Start noch konfigurieren.

```bash
SOCKET="/tmp/firecracker.socket"

# Status der VM abfragen
curl --unix-socket "$SOCKET" http://localhost/

# VM pausieren
curl --unix-socket "$SOCKET" -X PATCH \
  http://localhost/vm \
  -H "Content-Type: application/json" \
  -d '{"state": "Paused"}'

# VM fortsetzen
curl --unix-socket "$SOCKET" -X PATCH \
  http://localhost/vm \
  -H "Content-Type: application/json" \
  -d '{"state": "Resumed"}'

# VM sauber herunterfahren (sendet Ctrl+Alt+Del an den Gast)
curl --unix-socket "$SOCKET" -X PUT \
  http://localhost/actions \
  -H "Content-Type: application/json" \
  -d '{"action_type": "SendCtrlAltDel"}'
```

---

## 9. k3s in der VM installieren (optional)

Nach dem Start der VM per SSH verbinden und k3s installieren:

```bash
# Verbindung zur VM
ssh root@172.16.0.2

# k3s Single-Node-Cluster installieren
# --write-kubeconfig-mode: kubeconfig für alle Benutzer lesbar
curl -sfL https://get.k3s.io | sh -s - \
  --write-kubeconfig-mode 644

# Status prüfen
systemctl status k3s
kubectl get nodes
```

---

## 10. Troubleshooting

### KVM-Zugriff fehlt

```bash
# Gruppe prüfen
groups $USER | grep kvm

# Falls nicht vorhanden: Gruppe hinzufügen und neu anmelden
sudo usermod -aG kvm $USER
newgrp kvm
```

### VM startet nicht / keine Konsolenausgabe

```bash
# Firecracker-Log prüfen
cat /tmp/firecracker.log

# Kernel-Pfad und Rootfs-Pfad in config.json auf absolute Pfade prüfen
grep "path" ~/firecracker/config.json
```

### Keine Netzwerkverbindung aus der VM

```bash
# Auf dem Host: tap0 und IP-Forwarding prüfen
ip addr show tap0
cat /proc/sys/net/ipv4/ip_forward   # muss "1" sein
sudo iptables -t nat -L POSTROUTING -n -v

# In der VM: Route und Gateway prüfen
ip route
ping 172.16.0.1   # Gateway erreichbar?
ping 8.8.8.8      # Internet erreichbar?
```

### VM bootet, aber kein SSH-Zugriff

```bash
# Konsolenlog ansehen (falls im Hintergrund gestartet)
tail -f /tmp/firecracker-console.log

# SSH-Dienst in der VM prüfen (über serielle Konsole sichtbar)
# Root-Login in /etc/ssh/sshd_config: PermitRootLogin yes
```

### Rootfs voll

```bash
# Image-Datei vergrößern (VM muss gestoppt sein)
truncate -s 10G ~/firecracker/ubuntu-rootfs.ext4

# Dateisystem auf neue Größe anpassen
e2fsck -f ~/firecracker/ubuntu-rootfs.ext4
resize2fs ~/firecracker/ubuntu-rootfs.ext4
```

---

## Übersicht der verwendeten Dateien

| Datei | Zweck |
|---|---|
| `/usr/local/bin/firecracker` | Firecracker-Binary |
| `~/firecracker/vmlinux` | Linux-Kernel für die MicroVM |
| `~/firecracker/ubuntu-rootfs.ext4` | Root-Dateisystem der VM |
| `~/firecracker/config.json` | Firecracker-Startkonfiguration |
| `/tmp/firecracker.socket` | Unix-Socket für die REST-API |
| `/tmp/firecracker.log` | Firecracker-Loglevel-Ausgaben |
| `/tmp/firecracker-console.log` | Serielle Konsolenausgabe der VM |

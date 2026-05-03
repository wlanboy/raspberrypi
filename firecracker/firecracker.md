# Firecracker MicroVM-Fleet auf Ubuntu Server

Firecracker ist ein schlanker VMM (Virtual Machine Monitor) von AWS, der auf KVM aufbaut und
echte VMs in unter 125 ms startet. Im Vergleich zu Docker-Containern bietet Firecracker:

- **Vollständige Kernel-Isolation** – jede VM läuft mit eigenem Kernel, eigenem Speicher-Namespace und eigenem Netzwerk-Stack; ein Angreifer, der aus einer VM ausbricht, landet nicht auf dem Host
- **Kein Kernel-Sharing** – Container teilen sich den Host-Kernel; Firecracker-VMs nicht; CVEs im Host-Kernel sind für den Gast-Kernel irrelevant
- **Vorhersehbares Ressourcen-Limit** – vCPU- und RAM-Obergrenzen sind hardware-erzwungen, nicht durch cgroups approximiert
- **Schlanke Angriffsfläche** – Firecracker hat ~50.000 Zeilen Rust-Code und keinen BIOS/UEFI-Stack, keine PCI-Bus-Emulation, keine USB-Unterstützung
- **Produktionsreif** – von AWS für Lambda und Fargate eingesetzt; jede Invocation läuft in einer eigenen MicroVM

Dieses Repository enthält drei Skripte für den kompletten Lebenszyklus einer MicroVM-Fleet:

| Skript | Zweck |
|---|---|
| [firecracker.sh](firecracker.sh) | Einmalige Host-Einrichtung: Binary, Kernel, goldenes Base-Image |
| [addserver.sh](addserver.sh) | Neue VM aus dem Base-Image klonen und starten |
| [removeserver.sh](removeserver.sh) | VM stoppen und alle Ressourcen sauber entfernen |

---

## Voraussetzungen

- Ubuntu 22.04 / 24.04 LTS (x86_64 oder aarch64)
- CPU mit Intel VT-x oder AMD-V (`egrep -c '(vmx|svm)' /proc/cpuinfo` → Wert > 0)
- Zugriff auf `/dev/kvm` (KVM-Gruppe oder `sudo`)
- `sudo`-Rechte für Netzwerk- und Package-Operationen

---

## Schnellstart

### 1. Host einrichten

```bash
./firecracker.sh
```

[firecracker.sh](firecracker.sh) erledigt alles einmalig und idempotent:

1. KVM-Zugriff prüfen und einrichten
2. Pakete installieren (`curl`, `jq`, `e2fsprogs`, `squashfs-tools`)
3. Firecracker-Binary in `/usr/local/bin/` installieren (neueste Version automatisch ermittelt)
4. Passenden Kernel aus dem Firecracker-CI-S3-Bucket laden
5. Goldenes Base-Image (`base.ext4`) aus dem CI-Ubuntu-Squashfs erstellen und konfigurieren
6. IP-Forwarding dauerhaft via `/etc/sysctl.d/99-firecracker.conf` aktivieren

Alle Artefakte landen in `~/firecracker/`:

| Datei | Inhalt |
|---|---|
| `firecracker.version` | Gecachte Firecracker-Version |
| `vmlinux` | Kernel-Binary für alle VMs |
| `kernel.key` / `kernel.version` | S3-Pfad und Version des Kernels |
| `base.ext4` | Goldenes Root-Image (Vorlage für jede neue VM) |
| `ubuntu.key` / `rootfs.version` | S3-Pfad und Version des Ubuntu-Squashfs |
| `vms/` | Verzeichnis für alle VM-Instanzen |

**Neustart / Reset:** `./firecracker.sh --reset` stoppt alle laufenden VMs, löst alle Loop-Mounts und entfernt Binary sowie `~/firecracker/` vollständig, bevor ein sauberer Neuaufbau beginnt.

### 2. VM starten

```bash
./addserver.sh <name> [vcpus] [mem_mib] [disk_gb]
# Beispiel:
./addserver.sh web01 2 1024 10
```

[addserver.sh](addserver.sh) klont das goldene Base-Image, passt es an und startet die VM:

- Automatischer VM-Index → eindeutiges `/30`-Subnetz und TAP-Interface (`tap0`, `tap1`, …)
- Hostname, statische IP und DNS werden direkt ins Rootfs geschrieben
- SSH-Public-Keys aus `~/.ssh/id_*.pub` bzw. `authorized_keys` werden für root **und** den aufrufenden Benutzer eingerichtet
- SSH-Host-Keys werden vorab auf dem Host generiert (kein Entropy-Engpass beim ersten Boot)
- systemd-networkd-Konfiguration für das TAP-Interface wird persistent gesetzt (überlebt Reboot)
- VM startet im Hintergrund; Konsolenausgabe landet in `~/firecracker/vms/<name>/console.log`

**Idempotent:** läuft eine VM mit diesem Namen bereits, gibt das Skript den SSH-Befehl aus und endet. Ist sie gestoppt, wird sie neu gestartet (TAP-Interface wird bei Bedarf neu angelegt).

Nach ca. 3–5 Sekunden ist die VM per SSH erreichbar:

```bash
ssh <user>@<guest-ip>     # Benutzer und IP werden am Ende ausgegeben
```

### 3. VM entfernen

```bash
./removeserver.sh <name>
```

[removeserver.sh](removeserver.sh) stoppt den Firecracker-Prozess und räumt sauber auf:

- Firecracker-Prozess beenden (SIGTERM → SIGKILL falls nötig)
- Verwaiste Loop-Mounts lösen
- systemd-networkd-Konfiguration für das TAP-Interface entfernen
- iptables-nft- und nft-Regeln der VM entfernen (Fallback für manuell gesetzte Regeln)
- TAP-Interface löschen
- VM-Verzeichnis (`~/firecracker/vms/<name>/`) entfernen

Das Skript funktioniert auch dann, wenn das VM-Verzeichnis bereits gelöscht wurde: TAP-Name und IPs werden aus `/etc/systemd/network/50-tap*.vm` wiederhergestellt.

---

## Netzwerk-Schema

Jede VM bekommt ein eigenes `/30`-Subnetz im Bereich `172.16.0.0/16`.
Der VM-Index `N` (0, 1, 2, …) bestimmt das Subnetz:

| Index N | TAP-Interface | Host-IP (Gateway) | Gast-IP |
|---|---|---|---|
| 0 | `tap0` | `172.16.0.1` | `172.16.0.2` |
| 1 | `tap1` | `172.16.0.5` | `172.16.0.6` |
| 2 | `tap2` | `172.16.0.9` | `172.16.0.10` |
| … | … | … | … |

NAT ins Internet wird per `IPMasquerade=ipv4` in der systemd-networkd-Konfiguration gesetzt – keine manuellen iptables-Regeln notwendig. Maximal 16.384 gleichzeitige VMs möglich.

---

## VM-Verzeichnis

Jede VM hat ein eigenes Verzeichnis `~/firecracker/vms/<name>/`:

| Datei | Inhalt |
|---|---|
| `rootfs.ext4` | VM-eigene Kopie des Base-Images (CoW auf btrfs/xfs) |
| `config.json` | Firecracker-Konfiguration (Kernel, Disk, Netzwerk, Entropy) |
| `firecracker.pid` | PID des laufenden Firecracker-Prozesses |
| `firecracker.socket` | Unix-Socket für die REST-API |
| `console.log` | Serielle Konsolenausgabe der VM |
| `firecracker.log` | Interne Firecracker-Logs (Level: Info) |
| `index`, `guest_ip`, `host_ip`, `tap_dev` | Metadaten für Restart und Cleanup |
| `vcpus`, `mem_mib`, `disk_gb`, `host_user` | Ressourcen-Konfiguration |

---

## REST-API

Firecracker stellt nach dem Start eine HTTP-API über den Unix-Socket bereit:

```bash
SOCKET=~/firecracker/vms/<name>/firecracker.socket

# VM-Status abfragen
curl --unix-socket "$SOCKET" http://localhost/

# VM pausieren / fortsetzen
curl --unix-socket "$SOCKET" -X PATCH http://localhost/vm \
  -H "Content-Type: application/json" -d '{"state": "Paused"}'
curl --unix-socket "$SOCKET" -X PATCH http://localhost/vm \
  -H "Content-Type: application/json" -d '{"state": "Resumed"}'

# VM sauber herunterfahren
curl --unix-socket "$SOCKET" -X PUT http://localhost/actions \
  -H "Content-Type: application/json" -d '{"action_type": "SendCtrlAltDel"}'
```

---

## k3s in der VM (optional)

```bash
ssh root@<guest-ip>
curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
kubectl get nodes
```

Die Boot-Argumente in [addserver.sh](addserver.sh) aktivieren bereits `cgroup_enable=cpuset`, `cgroup_memory=1` und `cgroup_enable=memory`, sodass k3s ohne weitere Kernel-Konfiguration startet.

---

## Troubleshooting

### KVM-Zugriff fehlt

```bash
groups $USER | grep kvm
sudo usermod -aG kvm $USER
newgrp kvm
```

### VM startet, aber kein SSH-Zugriff

```bash
# Konsolenausgabe live beobachten
tail -f ~/firecracker/vms/<name>/console.log

# Firecracker-interne Logs
cat ~/firecracker/vms/<name>/firecracker.log
```

Häufige Ursachen: SSH-Host-Keys fehlen (sollten von [addserver.sh](addserver.sh) vorab generiert werden), Root-Login nicht erlaubt (`PermitRootLogin yes` in `/etc/ssh/sshd_config.d/99-firecracker.conf`), VM noch nicht vollständig gebootet.

### Keine Netzwerkverbindung aus der VM

```bash
# Auf dem Host
ip addr show tap<N>
cat /proc/sys/net/ipv4/ip_forward   # muss "1" sein
sudo iptables-nft -t nat -L POSTROUTING -n -v

# In der VM
ip route
ping 172.16.0.1   # Gateway (Host-IP) erreichbar?
ping 8.8.8.8      # Internet erreichbar?
```

### Rootfs voll

```bash
# VM muss gestoppt sein
truncate -s 10G ~/firecracker/vms/<name>/rootfs.ext4
sudo e2fsck -f ~/firecracker/vms/<name>/rootfs.ext4
sudo resize2fs ~/firecracker/vms/<name>/rootfs.ext4
```

### Base-Image beschädigt

```bash
# Base-Image entfernen – firecracker.sh erstellt es neu
rm ~/firecracker/base.ext4
./firecracker.sh
```

### Verwaistes Loop-Device

```bash
sudo losetup -j ~/firecracker/base.ext4 | cut -d: -f1 | xargs -r sudo losetup -d
```

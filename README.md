# raspberrypi
Raspberry Pi projects I am using for my own homelab.

## Table of Contents
- [Raspberry Pi Setup](#raspberry-pi-setup)
- [Networking](#networking)
- [Hardware Support](#hardware-support)
- [Virtualization](#virtualization)
- [Container Services](#container-services)
- [Kubernetes](#kubernetes)
- [Certificate Authority](#certificate-authority)
- [Web Applications](#web-applications)
- [Windows Integration](#windows-integration)
- [Arduino](#arduino)
- [Linux Administration](#linux-administration)
- [Tools](#tools)

---

## Raspberry Pi Setup

Basic setup and configuration for Raspberry Pi devices.

* [Preconfigure WLAN client on Raspberry Pi SD card](headless-wlan-client.md) - Headless setup without monitor
* [Create Bluetooth serial console](bluetooth-serial.md) - Connect via Bluetooth from your phone
* [Switch to XFCE4 desktop](xfce4.md) - Lightweight desktop environment
* [Compile VICE C64 Emulator](vice-c64.md) - Commodore 64 emulation

---

## Networking

Network configuration, access points, and routing.

### WLAN & Access Points
* [WLAN Access Point with ad-filter](wlan-access-point.md) - Turn your Pi into a WiFi hotspot with Pi-hole
* [TP-Link TL-WN725N driver setup](tl-wn725n.md) - USB WiFi adapter support
* [TP-Link TL-WN823N driver setup](tl-wn823n.md) - USB WiFi adapter support

### Wired Networking
* [USB LAN Adapter in libvirt VM](usb-lan-adapter.md) - USB passthrough for VMs
* [Network Bridge for second LAN port](bridge-second-lan.md) - Create a dedicated bridge for VMs

### Special Services
* [Create Tor hidden service](tor-hidden-service.md) - Host a .onion service
* [Flash OpenWRT to Raspberry Pi](openwrt.md) - Turn your Pi into a router

---

## Hardware Support

Hardware-specific configurations and drivers.

* [Enable TRIM support for USB SATA Bridge](usb_bridge_trim_support.md) - SSD optimization
* [Create NTP server with USB GPS source](timing-server.md) - Stratum 1 time server
* [Create RAID 1 with two USB hard disks](create-raid1.md) - Software RAID mirror
* [Create floppy disk image](create-floppy-image.md) - Legacy media support

---

## Virtualization

Virtual machines and hypervisor configuration.

* [USB LAN Adapter passthrough for libvirt](usb-lan-adapter.md) - Direct hardware access in VMs
* [Network Bridge configuration](bridge-second-lan.md) - Bridged networking for VMs

---

## Container Services

Docker installation and containerized applications.

### Docker Setup
* [Install Docker on armhf or arm64](docker.md) - Docker installation guide

### Container Management
* [Run Portainer with Docker](portainer.md) - Web-based Docker management
* [Run Pi-hole with Docker](pi-hole.md) - DNS-based ad blocking
* [Run MinIO with Docker](minio.md) - S3-compatible object storage
* [Run MariaDB with Docker](mariadb-in-docker.md) - MySQL-compatible database
* [Git server with Gitea](gitea.md) - Self-hosted Git service

---

## Kubernetes

K3s cluster setup and cloud-native tooling.

### Cluster Setup
* [Create ARM64 based k3s Kubernetes cluster](k3s-cluster.md) - Lightweight Kubernetes
* [Install Argo CD on k3s](k3s-argocd.md) - GitOps continuous deployment
* [Install Tekton Pipelines on k3s](tekton/readme.md) - Cloud-native CI/CD

### Storage
* [Local Ceph installation](ceph.md) - Distributed storage with loopback devices

---

## Certificate Authority

Manage SSL/TLS certificates for your homelab.

### Local CA Setup
* [Create your own offline CA](ca/readme.md) - Self-signed root certificate authority
* [Create local CA web interface](https://github.com/wlanboy/caweb) - Web UI for certificate management

### Kubernetes Certificate Management
* [Install cert-manager with local CA](ca/cert-manager/readme.md) - Automated certificate provisioning
* [Use cert-manager with Istio Ingress Gateway](ca/istio/readme.md) - TLS for service mesh
* [Inject external CA to Istio sidecars](ca/external-ca/readme.md) - Trust external certificates
* [Configure local DNS in k3s](ca/local-dns/readme.md) - Pi-hole DNS integration

---

## Web Applications

Python-based web applications included in this repository.

* [MinIO Web Manager](minioaccess/README.md) - Web UI for MinIO user and bucket management
* [Simple WebSocket Chat](chat/README.md) - Flask-based real-time chat application

---

## Windows Integration

Services for Windows client support.

* [Create Windows share for RAID volume](windows-share.md) - Samba file sharing
* [Create virtual PDF printer for Windows](windows-pdf-printer.md) - Network PDF printing

---

## Arduino

Arduino development resources.

* [Additional Boards Manager URLs](arduino/boards-manager-urls.md) - Sparkfun, Adafruit, Seeed Studio
* [Useful Arduino libraries](arduino/useful-libs.md) - Tested and working libraries

---

## Linux Administration

System administration and monitoring tools.

* [Java process monitoring](java-process-info.md) - Monitor JVM heap, CPU, RAM, threads, and OOM scores
* [tmux cheat sheet](tmux.md) - Terminal multiplexer usage

---

## Tools

Utility scripts for repository and Git management.

* [git_pull_all.py](tools/git_pull_all.py) - Run git pull on all subdirectories
* [scan_git_repos.py](tools/scan_git_repos.py) - Scan directory for Git repositories
* [mirror_git_repos.py](tools/mirror_git_repos.py) - Mirror Git repositories
* [find_big_files_in_git_history.sh](tools/find_big_files_in_git_history.sh) - Find large files in Git history
* [tools.sh](tools/tools.sh) - General shell utilities

---

## Project Structure

```
raspberrypi/
├── arduino/              # Arduino board manager URLs and libraries
├── ca/                   # Certificate Authority setup
│   ├── cert-manager/     # Kubernetes cert-manager configuration
│   ├── external-ca/      # External CA injection for Istio
│   ├── istio/            # Istio ingress with TLS
│   └── local-dns/        # Local DNS configuration
├── chat/                 # Python WebSocket chat application
├── chrony/               # Chrony time sync scripts
├── gitea/                # Gitea Docker Compose setup
├── minioaccess/          # MinIO web management interface
├── tekton/               # Tekton Pipelines documentation
├── tools/                # Utility scripts
└── *.md                  # Tutorial documentation files
```

---

## License

See [LICENSE](LICENSE) file for details.

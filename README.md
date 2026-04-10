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
- [GPU Setup](#gpu-setup)
- [Chromebook](#chromebook)
- [AI & Agents](#ai--agents)
- [Tools](#tools)

---

## Raspberry Pi Setup

Basic setup and configuration for Raspberry Pi devices.

- [Preconfigure WLAN client on Raspberry Pi SD card](headless-wlan-client.md) - Headless setup without monitor
- [Create Bluetooth serial console](bluetooth-serial.md) - Connect via Bluetooth from your phone
- [Switch to XFCE4 desktop](xfce4.md) - Lightweight desktop environment
- [Compile VICE C64 Emulator](vice-c64.md) - Commodore 64 emulation

---

## Networking

Network configuration, access points, and routing.

### WLAN & Access Points

- [WLAN Access Point with ad-filter](wlan-access-point.md) - Turn your Pi into a WiFi hotspot with Pi-hole
- [TP-Link TL-WN725N driver setup](tl-wn725n.md) - USB WiFi adapter support
- [TP-Link TL-WN823N driver setup](tl-wn823n.md) - USB WiFi adapter support

### Wired Networking

- [USB LAN Adapter in libvirt VM](usb-lan-adapter.md) - USB passthrough for VMs
- [Network Bridge for second LAN port](bridge-second-lan.md) - Create a dedicated bridge for VMs

### Special Services

- [Create Tor hidden service](tor-hidden-service.md) - Host a .onion service
- [Flash OpenWRT to Raspberry Pi](openwrt.md) - Turn your Pi into a router

---

## Hardware Support

Hardware-specific configurations and drivers.

- [Enable TRIM support for USB SATA Bridge](usb_bridge_trim_support.md) - SSD optimization
- [Create NTP server with USB GPS source](timing-server.md) - Stratum 1 time server
- [GPS-based NTP with Chrony](chrony/chrony.md) - Detailed chrony configuration with GPS offset calibration and statistics
- [Create RAID 1 with two USB hard disks](create-raid1.md) - Software RAID mirror
- [Create floppy disk image](create-floppy-image.md) - Legacy media support

---

## Virtualization

Virtual machines and hypervisor configuration.

- [USB LAN Adapter passthrough for libvirt](usb-lan-adapter.md) - Direct hardware access in VMs
- [Network Bridge configuration](bridge-second-lan.md) - Bridged networking for VMs

---

## Container Services

Docker installation and containerized applications.

### Docker Setup

- [Install Docker on armhf or arm64](docker.md) - Docker installation guide

### Container Management

- [Run Portainer with Docker](portainer.md) - Web-based Docker management
- [Run Pi-hole with Docker](pi-hole.md) - DNS-based ad blocking
- [Run MinIO with Docker](minio.md) - S3-compatible object storage
- [Run MariaDB with Docker](mariadb-in-docker.md) - MySQL-compatible database
- [Git server with Gitea](gitea/gitea.md) - Self-hosted Git service

---

## Kubernetes

K3s cluster setup and cloud-native tooling.

### Cluster Setup

- [Create ARM64 based k3s Kubernetes cluster](k3s-cluster.md) - Lightweight Kubernetes
- [Install Argo CD on k3s](k3s-argocd.md) - GitOps continuous deployment
- [Install Tekton Pipelines on k3s](tekton/readme.md) - Cloud-native CI/CD

### Storage

- [Local Ceph installation](ceph.md) - Distributed storage with loopback devices

---

## Certificate Authority

Manage SSL/TLS certificates for your homelab.

### Local CA Setup

- [Create your own offline CA](ca/readme.md) - Self-signed root certificate authority
- [Create local CA web interface](https://github.com/wlanboy/caweb) - Web UI for certificate management

### Kubernetes Certificate Management

- [Install cert-manager with local CA](ca/cert-manager/readme.md) - Automated certificate provisioning
- [Use cert-manager with Istio Ingress Gateway](ca/istio/readme.md) - TLS for service mesh
- [Inject external CA to Istio sidecars](ca/external-ca/readme.md) - Trust external certificates
- [Configure local DNS in k3s](ca/local-dns/readme.md) - Pi-hole DNS integration

---

## Web Applications

Python-based web applications included in this repository.

- MinIO Web Manager - Web UI for MinIO user and bucket management *(directory removed)*
- [Simple WebSocket Chat](chat/README.md) - Flask-based real-time chat application
- [Keep Export](keep-export/README.md) - Convert Google Keep notes (Takeout JSON) to Markdown; optional upload to HedgeDoc with FastAPI browse UI

---

## Windows Integration

Services for Windows client support.

- [Create Windows share for RAID volume](windows-share.md) - Samba file sharing
- [Create virtual PDF printer for Windows](windows-pdf-printer.md) - Network PDF printing

---

## Arduino

Arduino development resources.

- [Additional Boards Manager URLs](arduino/boards-manager-urls.md) - Sparkfun, Adafruit, Seeed Studio
- [Useful Arduino libraries](arduino/useful-libs.md) - Tested and working libraries

---

## Linux Administration

System administration and monitoring tools.

- [Java process monitoring](java-process-info.md) - Monitor JVM heap, CPU, RAM, threads, and OOM scores
- [tmux cheat sheet](tmux.md) - Terminal multiplexer usage
- [Hadoop/ZooKeeper log analyzer](hadoop/log-analyze.py) - Analyze NameNode, JournalNode, DataNode, and ZooKeeper log files
- [Prometheus cardinality analyzer](prometheus/series-analyze.py) - Find metrics and label combinations with the highest memory usage

---

## Tools

Utility scripts for repository, Git, Docker, and Maven management. See [tools/tools.md](tools/tools.md) for full documentation.

- [add_aliases.sh](tools/add_aliases.sh) - Register all tools as shell aliases in `~/.bashrc`
- [git_pull_all.py](tools/git_pull_all.py) - Run `git pull` on all subdirectories
- [git_status_all.py](tools/git_status_all.py) - Show `git status` for all repositories at a glance
- [scan_git_repos.py](tools/scan_git_repos.py) - List Git repositories with branch and remote URLs
- [mirror_git_repos.py](tools/mirror_git_repos.py) - Mirror GitHub repositories (topic `mirror`) to Gitea
- [gh-no-mirror.py](tools/gh-no-mirror.py) - Find GitHub repositories not yet tagged for mirroring
- [local_push.py](tools/local_push.py) - Push repositories to a local remote
- [update-pom.py](tools/update-pom.py) - Update Maven `pom.xml` dependencies to latest releases
- [scan_external_urls.py](tools/scan_external_urls.py) - Scan a repository for external URLs, emails, and IP addresses
- [docker-volumes-backup.py](tools/docker-volumes-backup.py) - Backup and restore Docker/Podman volumes
- [find_big_files_in_git_history.sh](tools/find_big_files_in_git_history.sh) - Find files larger than 50 KB in Git history

---

## GPU Setup

Intel Arc GPU driver installation and tooling on Ubuntu.

- [Intel Arc Pro B60 setup](intel_arc_pro_b60/intel-arc.md) - Full Ubuntu 24.04 driver setup (OpenCL, Level Zero, VA-API), GPU monitoring with nvtop, Steam via Flatpak, and LLM inference via Intel LLM Scaler

---

## Chromebook

Running Linux workloads on Chromebook via the Crostini container.

- [Local LLM on Chromebook (Intel N150)](chromebook/Crostini-LLM.md) - Run Ollama models (phi4-mini, Qwen, Gemma, LLaMA) locally on a Chromebook via CPU inference — no GPU required

---

## AI & Agents

Agent-to-Agent (A2A) protocol documentation for building multi-agent systems.

- [A2A protocol overview](mcp-a2a/a2a.md) - Architecture, data model, JSON-RPC methods, task lifecycle, and multi-agent composition
- [A2A AgentCard](mcp-a2a/a2a-agentcard.md) - AgentCard interface: how agents advertise their identity and skills

---

## Project Structure

```txt
raspberrypi/
├── arduino/              # Arduino board manager URLs and libraries
├── ca/                   # Certificate Authority setup
│   ├── cert-manager/     # Kubernetes cert-manager configuration
│   ├── external-ca/      # External CA injection for Istio
│   ├── istio/            # Istio ingress with TLS
│   └── local-dns/        # Local DNS configuration
├── chat/                 # Python WebSocket chat application
├── chromebook/           # LLM on Chromebook via Crostini (Ollama)
├── chrony/               # GPS-based NTP with Chrony — setup and stats script
├── gitea/                # Gitea Docker Compose setup
├── hadoop/               # Hadoop/ZooKeeper log analyzer
├── intel_arc_pro_b60/    # Intel Arc Pro B60 GPU setup on Ubuntu
├── keep-export/          # Google Keep → Markdown converter and HedgeDoc uploader
├── mcp-a2a/              # A2A Agent-to-Agent protocol documentation
├── minioaccess/          # MinIO web management interface
├── prometheus/           # Prometheus cardinality/memory analyzer
├── tekton/               # Tekton Pipelines documentation
├── tools/                # Utility scripts (Git, Docker, Maven)
└── *.md                  # Tutorial documentation files
```

---

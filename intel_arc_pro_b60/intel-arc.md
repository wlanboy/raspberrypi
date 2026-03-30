# Intel Arc Pro B60 – Einrichtung unter Ubuntu 24.04 (Noble)

Diese Anleitung beschreibt die vollständige Einrichtung einer Intel Arc Pro B60 GPU
(Battlemage / Xe2-Architektur) unter Ubuntu 24.04 LTS, inklusive OpenCL/Level-Zero-Treiber,
GPU-Monitoring und Steam-Gaming-Setup.

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Intel GPU-Treiber installieren](#2-intel-gpu-treiber-installieren)
3. [Compute-Runtime manuell installieren (NEO)](#3-compute-runtime-manuell-installieren-neo)
4. [GPU-Monitoring mit nvtop](#4-gpu-monitoring-mit-nvtop)
5. [Steam via Flatpak einrichten](#5-steam-via-flatpak-einrichten)
6. [Verifikation & Fehlerbehebung](#6-verifikation--fehlerbehebung)
7. [LLM Scaler – LLM-Inferenz auf der iGPU](#7-llm-scaler--llm-inferenz-auf-der-igpu)

---

## 1. Voraussetzungen

- Ubuntu 24.04 LTS (Noble Numbat), 64-Bit
- Intel Arc Pro B60 GPU installiert (PCIe)
- Internetverbindung
- Benutzer mit `sudo`-Rechten

Kernel-Version prüfen (Minimum: 6.8, empfohlen: 6.11+ für vollständige Xe2/Battlemage-Unterstützung):

```bash
uname -r
```

Aktuelle Kernel-Version anzeigen und ggf. aktualisieren:

```bash
sudo apt update && sudo apt upgrade -y
```

Für bessere B60-Unterstützung den HWE-Kernel installieren (Ubuntu 24.04):

```bash
sudo apt install linux-generic-hwe-24.04
sudo reboot
```

---

## 2. Intel GPU-Treiber installieren

Das Script [`drivers.sh`](drivers.sh) richtet das offizielle Intel GPU-Repository ein und installiert
alle notwendigen Treiber- und Laufzeit-Pakete.

### Schritte im Detail

#### 2.1 Alte Repositories entfernen

Bestehende, möglicherweise fehlerhafte Intel-GPU-Quellen werden zuerst bereinigt:

```bash
sudo rm -f /etc/apt/sources.list.d/intel-graphics.list
sudo rm -f /etc/apt/sources.list.d/intel-gpu-noble.list
```

#### 2.2 GPG-Schlüssel importieren

```bash
sudo mkdir -p /usr/share/keyrings
wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | \
  sudo gpg --dearmor --yes --output /usr/share/keyrings/intel-graphics.gpg
sudo chmod 644 /usr/share/keyrings/intel-graphics.gpg
```

#### 2.3 Intel GPU-Repository (Unified Stack) hinzufügen

Der "unified" Stack ist für die Battlemage/Xe2-Architektur optimiert:

```bash
echo "deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg] \
  https://repositories.intel.com/gpu/ubuntu noble/lts/2350 unified" | \
  sudo tee /etc/apt/sources.list.d/intel-gpu-noble.list
```

#### 2.4 OneAPI-Repository hinzufügen (optional)

> **Wann nötig?** Das OneAPI-Repository wird nur benötigt, wenn du SYCL/DPC++-Entwicklung betreiben
> oder Intel-optimierte Bibliotheken (MKL, oneDNN) nutzen möchtest – z.B. für KI/ML-Workloads,
> OpenVINO oder das LLM Scaler Framework (siehe [Abschnitt 7](#7-llm-scaler--llm-inferenz-auf-der-igpu)).
> Für reines Gaming oder OpenCL-Nutzung ist dieses Repository nicht erforderlich.

```bash
wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB | \
  gpg --dearmor | sudo tee /usr/share/keyrings/oneapi-archive-keyring.gpg > /dev/null

echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] \
  https://apt.repos.intel.com/oneapi all main" | \
  sudo tee /etc/apt/sources.list.d/oneAPI.list
```

#### 2.5 Pakete installieren

```bash
sudo apt update

sudo apt install -y \
    intel-opencl-icd \
    libze-intel-gpu1 \
    libze1 \
    intel-media-va-driver-non-free \
    libigdgmm12 \
    clinfo \
    intel-gpu-tools \
    mesa-utils
```

| Paket | Funktion |
| --- | --- |
| `intel-opencl-icd` | OpenCL-Treiber (ICD) für Intel GPU |
| `libze-intel-gpu1` | Level Zero GPU-Laufzeit |
| `libze1` | Level Zero API |
| `intel-media-va-driver-non-free` | Hardware-Videodekodierung (VA-API) |
| `libigdgmm12` | Intel Graphics Memory Management |
| `clinfo` | OpenCL-Informations-Tool |
| `intel-gpu-tools` | Diagnose-Tools (`intel_gpu_top` etc.) |
| `mesa-utils` | OpenGL-Diagnosewerkzeuge (`glxinfo`, `glxgears`) |

#### 2.6 OneAPI Entwicklungstools (optional)

Für SYCL/DPC++-Entwicklung und optimierte Mathematik-Bibliotheken:

```bash
sudo apt install -y intel-oneapi-compiler-dpcpp-cpp intel-oneapi-mkl
```

Nach der Installation die Umgebungsvariablen laden:

```bash
source /opt/intel/oneapi/setvars.sh
```

Um verfügbare SYCL-Geräte zu prüfen:

```bash
sycl-ls
```

#### 2.7 Benutzer den GPU-Gruppen hinzufügen

Damit die GPU ohne `sudo` genutzt werden kann:

```bash
sudo usermod -aG render $USER
sudo usermod -aG video $USER
```

**Neustart erforderlich**, damit die Gruppenmitgliedschaft aktiv wird.

#### Installation per Script ausführen

```bash
chmod +x drivers.sh
./drivers.sh
sudo reboot
```

---

## 3. Compute-Runtime manuell installieren (NEO)

Falls die Repository-Version veraltet ist oder Probleme auftreten, kann die Intel Compute-Runtime
direkt von GitHub installiert werden. Das Script [`neo.sh`](neo.sh) enthält die entsprechenden
Befehle.

> **Wann nötig?** Bei neuen GPU-Generationen wie Battlemage dauert es oft, bis die Repository-Pakete
> aktuell sind. Manuelle Installation bietet immer die neueste Version.

### Installation im Detail

#### 3.1 Arbeitsverzeichnis anlegen

```bash
mkdir neo && cd neo
```

#### 3.2 Pakete herunterladen

Intel Graphics Compiler (IGC):

```bash
wget https://github.com/intel/intel-graphics-compiler/releases/download/v2.28.4/intel-igc-core-2_2.28.4+20760_amd64.deb
wget https://github.com/intel/intel-graphics-compiler/releases/download/v2.28.4/intel-igc-opencl-2_2.28.4+20760_amd64.deb
```

Intel Compute-Runtime (NEO):

```bash
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/intel-ocloc_26.05.37020.3-0_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/intel-opencl-icd_26.05.37020.3-0_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/libigdgmm12_22.9.0_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/libze-intel-gpu1_26.05.37020.3-0_amd64.deb
```

> Aktuelle Versionen immer auf den GitHub-Release-Seiten prüfen:
> [intel/compute-runtime](https://github.com/intel/compute-runtime/releases) |
> [intel/intel-graphics-compiler](https://github.com/intel/intel-graphics-compiler/releases)

#### 3.3 Konflikte mit bestehenden Paketen lösen

Alte Repository-Pakete entfernen, um Konflikte zu vermeiden:

```bash
sudo apt install ocl-icd-libopencl1
sudo apt remove intel-opencl-icd intel-level-zero-gpu level-zero
sudo apt remove intel-igc-core intel-igc-opencl
sudo apt remove libigdgmm12
```

#### 3.4 Pakete installieren

```bash
sudo dpkg -i *.deb
```

Bei fehlenden Abhängigkeiten:

```bash
sudo apt install -f
```

---

## 4. GPU-Monitoring mit nvtop

`nvtop` ist ein interaktiver GPU-Monitor ähnlich `htop`. Das Script [`nvtop.sh`](nvtop.sh) baut
`nvtop` aus dem Quellcode mit Intel-GPU-Unterstützung.

### Abhängigkeiten installieren

```bash
sudo apt install -y \
    cmake \
    libncurses5-dev \
    libncursesw5-dev \
    libdrm-dev \
    libsystemd-dev \
    pkg-config
```

### Aus Quellcode bauen und installieren

```bash
git clone https://github.com/Syllo/nvtop.git
cd nvtop/
mkdir -p build && cd build
cmake .. -DENABLE_INTEL=ON -DENABLE_NVIDIA=OFF -DENABLE_AMDGPU=OFF
make -j$(nproc)
sudo make install
```

> Die Flags `-DENABLE_NVIDIA=OFF -DENABLE_AMDGPU=OFF` sind optional. Wenn keine anderen GPUs
> verbaut sind, kann die Build-Zeit damit reduziert werden.

### nvtop starten

```bash
nvtop
```

Alternativ für schnelle Auslastungsanzeige ohne nvtop:

```bash
sudo intel_gpu_top
```

---

## 5. Steam via Flatpak einrichten

Das Script [`steam.sh`](steam.sh) installiert Steam als Flatpak-Anwendung mit einem eigenen
Speicherverzeichnis für Spiele.

### 5.1 Spieleverzeichnis anlegen

```bash
sudo mkdir /data/steam
sudo chown -R $USER:$USER /data/steam
```

> `/data/steam` kann nach Bedarf angepasst werden, z.B. auf eine separate SSD/HDD.

### 5.2 Flatpak und Steam installieren

```bash
sudo apt install flatpak
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub com.valvesoftware.Steam
```

### 5.3 Zugriff auf das Spieleverzeichnis gewähren

```bash
sudo flatpak override com.valvesoftware.Steam --filesystem=/data/steam
```

Damit kann Steam Spiele in `/data/steam` installieren. In den Steam-Einstellungen unter
**Einstellungen → Downloads → Steam-Bibliotheksordner** den Pfad `/data/steam` hinzufügen.

Um den Zugriff wieder zu entziehen:

```bash
sudo flatpak override com.valvesoftware.Steam --nofilesystem=/data/steam
```

### 5.4 Steam-Geräteunterstützung installieren

```bash
sudo apt update
sudo apt install steam-devices
```

Das Paket `steam-devices` enthält udev-Regeln für Controller, VR-Headsets und andere Steam-Hardware.

### 5.5 Proton / Steam Play für Linux-Kompatibilität

In Steam unter **Einstellungen → Steam Play** die Option
"Steam Play für alle anderen Titel aktivieren" einschalten und Proton Experimental oder die
neueste stabile Proton-Version auswählen.

Für optimale Leistung mit Intel Arc empfiehlt sich der Umgebungsvariable:

```bash
PROTON_ENABLE_NVAPI=0 %command%
```

Diese kann pro Spiel unter **Eigenschaften → Startoptionen** gesetzt werden.

---

## 6. Verifikation & Fehlerbehebung

### OpenCL prüfen

```bash
clinfo -l
```

Erwartete Ausgabe (gekürzt):

```text
Platform #0: Intel(R) OpenCL Graphics
 `-- Device #0: Intel(R) Arc(TM) Pro B60 Graphics
```

### Level Zero prüfen

```bash
sycl-ls
```

Erwartete Ausgabe (erfordert installiertes OneAPI):

```text
[opencl:gpu:0] Intel(R) OpenCL Graphics, Intel(R) Arc(TM) Pro B60 Graphics ...
[level_zero:gpu:0] Intel(R) Level-Zero, Intel(R) Arc(TM) Pro B60 Graphics ...
```

Ohne OneAPI alternativ via `clinfo`:

```bash
clinfo -l
```

DRI-Devices prüfen:

```bash
ls /dev/dri/
```

Es sollten Einträge wie `card0`, `renderD128` vorhanden sein.

### Mesa / OpenGL prüfen

```bash
glxinfo | grep "OpenGL renderer"
```

### Hardware-Video-Dekodierung prüfen (VA-API)

```bash
sudo apt install vainfo
vainfo
```

### GPU-Auslastung in Echtzeit

```bash
sudo intel_gpu_top
```

### Häufige Probleme

| Problem | Lösung |
| --- | --- |
| `clinfo` zeigt keine Intel-Plattform | Neustart prüfen; Benutzer in Gruppe `render` (`groups` prüfen) |
| `Permission denied` auf `/dev/dri/renderD128` | `sudo usermod -aG render $USER` und neu anmelden |
| Treiber-Paketkonflikt bei `dpkg -i` | `sudo apt install -f` ausführen |
| Steam startet nicht | `flatpak run com.valvesoftware.Steam` im Terminal starten, Fehlerausgabe prüfen |
| Niedrige Gaming-Performance | Mesa-Version prüfen (`glxinfo \| grep version`); ggf. neuere Mesa-PPA einbinden |

### Kernel-Module prüfen

```bash
lspci -k | grep -A 3 "Intel.*Graphics"
```

Das Modul `xe` (für Xe2/Battlemage) oder `i915` sollte als Kernel-Treiber angezeigt werden.

---

## 7. LLM Scaler – LLM-Inferenz auf der iGPU

**[intel/llm-scaler](https://github.com/intel/llm-scaler)** ist ein von Intel entwickeltes Framework,
das Large Language Models effizient auf Intel Arc GPUs ausführt – optimiert für die Xe2-Architektur
(Battlemage) der B60.

### Was es bietet

- Inferenz von LLMs (z.B. LLaMA, Mistral, Qwen) direkt auf der Intel GPU via Level Zero / SYCL
- Nutzung der B60-Speicherbandbreite (48 GB GDDR6) für große Modelle ohne CPU-Flaschenhals
- Integration mit HuggingFace-Modellen und GGUF-Format
- Optimierte Kernel für Intel Xe-Matrix Extensions (XMX / Tensor-Einheiten der B60)

### Voraussetzungen

- OneAPI-Stack installiert (siehe [Abschnitt 2.4](#24-oneapi-repository-hinzufügen-optional))
- Level Zero Laufzeit aktiv (`sycl-ls` zeigt die GPU)

### Installation

```bash
git clone https://github.com/intel/llm-scaler.git
cd llm-scaler
pip install -e .
```

Umgebungsvariablen für OneAPI laden:

```bash
source /opt/intel/oneapi/setvars.sh
```

### Nutzung (Beispiel)

```bash
python run.py --model <modellpfad> --device gpu
```

> Aktuelle Installations- und Nutzungshinweise direkt im
> [GitHub-Repository](https://github.com/intel/llm-scaler) prüfen, da sich das Projekt aktiv
> weiterentwickelt.

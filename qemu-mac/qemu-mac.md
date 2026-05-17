# Mac OS 9.1 unter Ubuntu virtualisieren mit QEMU

Anleitung zum Extrahieren einer `.sit`-Datei und Erstellen einer performanten virtuellen Mac-Umgebung mit Internetanbindung.

---

## Voraussetzungen

### Benötigte Tools installieren

```bash
sudo apt update
sudo apt install -y \
  unar \
  qemu-system-ppc \
  qemu-utils \
  wget \
  curl
```

| Tool | Zweck |
|------|-------|
| `unar` | Entpackt `.sit`-Archive (StuffIt-Format) |
| `qemu-system-ppc` | PowerPC-Emulation für Classic Mac OS |
| `qemu-utils` | Hilfswerkzeuge (qemu-img etc.) |

> **Alternative zu `unar`:** Das proprietäre `stuffit` von Smith Micro kann `.sit`-Dateien ebenfalls entpacken, ist aber nicht frei verfügbar. `unar` aus dem Paket `unar` (libarchive-basiert) unterstützt die meisten StuffIt-Formate.

---

## Schritt 1: .sit-Datei entpacken

```bash
# .sit extrahieren
unar MacOS9.1.sit

# Inhalt prüfen
ls -lh MacOS9.1/
```

Nach dem Entpacken sollte sich entweder:
- eine `.img`- oder `.iso`-Datei befinden, oder
- ein `.toast`- oder `.dmg`-Image

### Toast/DMG zu ISO konvertieren (falls nötig)

```bash
# .toast ist oft direkt ein ISO
cp MacOS9.1.toast MacOS9.1.iso

# .dmg konvertieren (benötigt hfsutils oder dmg2img)
sudo apt install -y dmg2img
dmg2img MacOS9.1.dmg MacOS9.1.iso
```

---

## Schritt 2: Festplatten-Image erstellen

```bash
# 2 GB Festplatte für Mac OS 9.1 (reicht komfortabel)
qemu-img create -f qcow2 macos9.qcow2 2G
```

---

## Schritt 3: QEMU starten und Mac OS 9.1 installieren

Mac OS 9 läuft auf dem emulierten PowerPC-Modell `mac99` (Power Mac G4).

```bash
qemu-system-ppc \
  -machine mac99,via=pmu \
  -cpu g4 \
  -m 512 \
  -hda macos9.qcow2 \
  -cdrom MacOS9.1.iso \
  -boot d \
  -net nic,model=sungem \
  -net user \
  -vga std \
  -display sdl
```

> **Maus-Steuerung:** Mit `-display sdl,grab-on-hover=on` wird die Maus automatisch gefangen, sobald der Cursor das Fenster betritt. Freigabe mit `Strg+Alt`. Alternativ: Klick ins Fenster zum Greifen, `Strg+Alt` zum Loslassen.

### Parameter erklärt

| Parameter | Bedeutung |
|-----------|-----------|
| `-machine mac99,via=pmu` | Power Mac G4 mit PMU-Chip |
| `-cpu g4` | PowerPC G4-Prozessor |
| `-m 256` | 256 MB RAM (Mac OS 9 Maximum war 1,5 GB, 256 MB optimal) |
| `-hda macos9.qcow2` | Festplatten-Image |
| `-cdrom MacOS9.1.iso` | Installations-ISO |
| `-boot d` | Von CD booten |
| `-net nic,model=sungem` | Netzwerkkarte (von Mac OS 9 unterstützt) |
| `-net user` | NAT-Netzwerk (kein Setup nötig, Internet funktioniert sofort) |

---

## Schritt 4: Installation durchführen

1. QEMU startet vom ISO
2. Im Mac OS Installer: Festplatte mit dem **Disk Setup**-Tool initialisieren und formatieren (HFS+)
3. Installation starten
4. Nach Abschluss: Neustart, dann `-boot d` durch `-boot c` ersetzen

---

## Schritt 5: System nach Installation starten

```bash
qemu-system-ppc \
  -machine mac99,via=pmu \
  -cpu g4 \
  -m 256 \
  -hda macos9.qcow2 \
  -net nic,model=sungem \
  -net user \
  -vga std \
  -display sdl,grab-on-hover=on
```

---

## Schritt 6: Programm-ISO einlegen und installieren

Um ein Programm aus einer ISO/CD nachträglich zu installieren, einfach die ISO als `-cdrom` anhängen:

```bash
qemu-system-ppc \
  -machine mac99,via=pmu \
  -cpu g4 \
  -m 256 \
  -hda macos9.qcow2 \
  -cdrom MeinProgramm.iso \
  -net nic,model=sungem \
  -net user \
  -vga std \
  -display sdl,grab-on-hover=on
```

Die CD erscheint nach dem Start automatisch als Icon auf dem Mac-Desktop. Installer doppelklicken und wie gewohnt installieren.

### ISO aus einem .sit-Archiv extrahieren

Falls das Programm als `.sit` vorliegt:

```bash
unar MeinProgramm.sit
# Prüfen ob eine .iso/.img/.toast enthalten ist
ls -lh MeinProgramm/

# .toast direkt als ISO verwenden
cp MeinProgramm.toast MeinProgramm.iso
```

### CD während des Betriebs wechseln (QEMU-Monitor)

```bash
# Monitor öffnen: Strg+Alt+2
# CD wechseln:
change ide1-cd0 /pfad/zu/anderes.iso
# CD auswerfen:
eject ide1-cd0
# Zurück zur VM: Strg+Alt+1
```

---

## Performance-Optimierung

### SMP (mehrere CPUs)

Mac OS 9 unterstützt kein SMP, daher bringt `-smp` keinen Vorteil.

### Beschleunigung mit KVM (nicht möglich für PPC auf x86)

Da QEMU hier PowerPC auf x86_64 emuliert, ist KVM-Beschleunigung **nicht verfügbar**. Die Emulation läuft in Software. Für flüssigeren Betrieb:

```bash
# Prozessor-Affinität setzen (QEMU-Prozess an CPU-Kern binden)
taskset -c 0 qemu-system-ppc ...
```

### Display und Maus-Steuerung

```bash
# SDL mit automatischem Maus-Grab (empfohlen)
-display sdl

# GTK mit Maus-Grab
-display gtk

# Vollbild
-display sdl -full-screen

# VNC für Remote-Zugriff
-display vnc=:0
```

| Aktion | Tastenkürzel (SDL) | Tastenkürzel (GTK) |
|--------|-------------------|-------------------|
| Maus greifen | Klick ins Fenster | Klick ins Fenster |
| Maus freigeben | `Strg+Alt` | `Strg+Alt+G` |
| Vollbild ein/aus | `Strg+Alt+F` | `Strg+Alt+F` |
| QEMU-Monitor | `Strg+Alt+2` | `Strg+Alt+2` |

---

## Internetanbindung konfigurieren

### In Mac OS 9: TCP/IP einstellen

1. **Apfelmenü → Kontrollfelder → TCP/IP** öffnen
2. Verbinden via: **Ethernet**
3. Konfigurieren: **DHCP-Server**
4. Schließen und speichern

QEMU's User-Mode-Netzwerk (SLIRP) stellt automatisch einen DHCP-Server bereit:
- Gateway: `10.0.2.2`
- DNS: `10.0.2.3`
- IP-Range: `10.0.2.x`

### Ports von Host zu Guest weiterleiten (optional)

```bash
-net user,hostfwd=tcp::5900-:5900
```

---

## Dateiaustausch zwischen Ubuntu und Mac OS 9

### Methode 1: Shared Folder via FAT-Image

```bash
# FAT-Image erstellen
qemu-img create -f raw shared.img 512M
mkfs.fat shared.img

# Als zweite Festplatte einbinden
-hdb shared.img
```

In Mac OS 9 erscheint das Volume automatisch auf dem Desktop.

### Methode 2: HTTP-Server auf Ubuntu

```bash
# Einfacher HTTP-Server auf Ubuntu starten
python3 -m http.server 8080

# In Mac OS 9: Browser öffnen, URL: http://10.0.2.2:8080
```

---

## Komplettes Startskript

```bash
#!/bin/bash
# macos9-start.sh

DISK="macos9.qcow2"
ISO="${1:-}"  # Optional: ISO als erstes Argument

BOOT_OPTS="-boot c"
CDROM_OPTS=""

if [ -n "$ISO" ]; then
  BOOT_OPTS="-boot d"
  CDROM_OPTS="-cdrom $ISO"
fi

qemu-system-ppc \
  -machine mac99,via=pmu \
  -cpu g4 \
  -m 256 \
  -hda "$DISK" \
  $CDROM_OPTS \
  $BOOT_OPTS \
  -net nic,model=sungem \
  -net user \
  -vga std \
  -display sdl \
  -name "Mac OS 9.1"
```

```bash
chmod +x macos9-start.sh

# Installation: ISO übergeben
./macos9-start.sh MacOS9.1.iso

# Normaler Start
./macos9-start.sh
```

---

## Bekannte Probleme

| Problem | Lösung |
|---------|--------|
| Schwarzer Bildschirm beim Start | OpenFirmware-Meldung abwarten (kann 30s dauern) |
| Keine Netzwerkverbindung in Mac OS 9 | TCP/IP Kontrollfeld auf DHCP setzen |
| `.sit` lässt sich nicht entpacken | `unar` statt `unzip` verwenden; ältere `.sit`-Formate mit `unstuff` aus dem AUR |
| Maus verlässt das Fenster | `-display sdl,grab-on-hover=on` verwenden — Maus wird beim Überfahren automatisch gegriffen |
| Maus freigeben | `Strg+Alt` (SDL) oder `Strg+Alt+G` (GTK) |
| Maus nicht synchron (Offset) | Nur bei relativem Modus — mit `grab-on-hover=on` behoben |
| System startet nicht von HDD | Im QEMU-Monitor: `boot c` eingeben (Strg+Alt+2) |

---

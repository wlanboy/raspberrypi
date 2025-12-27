# Erstellen und Befüllen eines DOS‑Disketten‑Images
Diese Anleitung beschreibt, wie du mit mtools ein 1,44‑MB‑Disketten‑Image erstellst und anschließend Dateien hinein kopierst.
Sie eignet sich z. B. für DOS‑Treiber, Bootdisketten oder virtuelle Maschinen.

## Voraussetzungen
- Installierte mtools
- Dateien, die auf das Image kopiert werden sollen (z. B. MOUSE.COM, MOUSE.SYS, Ordner ssh2021b)

## 1. Disketten‑Image erstellen
Mit folgendem Befehl erzeugst du ein neues 1,44‑MB‑FAT‑Disketten‑Image mit dem Volume‑Label WINVBLOCK:

```bash
mformat -C -f 1440 -v WINVBLOCK -i treiber.img
```

Parameter‑Erklärung:
-C	Erstellt das Image, falls es noch nicht existiert
-f 1440	Größe: 1,44 MB (Standard‑Floppy)
-v WINVBLOCK	Volume‑Label setzen
-i treiber.img	Ziel‑Image

## 2. Dateien in das Disk‑Image kopieren
Maus‑Treiber kopieren
```bash
mcopy -i treiber.img MOUSE.COM MOUSE.SYS ::
```
:: steht für das Root‑Verzeichnis des Disk‑Images.

Weitere Dateien (z. B. SSH‑Tools) kopieren
```bash
mcopy -i treiber.img .\ssh2021b\*.* ::
```
Damit wird der gesamte Inhalt des Ordners ssh2021b ins Root des Images übertragen.


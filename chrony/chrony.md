# GPS-gestützter NTP-Zeitserver mit Chrony

Diese Anleitung beschreibt den Aufbau eines präzisen NTP-Zeitservers unter Linux,
der ein USB-GPS-Modul als primäre Zeitquelle nutzt. Chrony synchronisiert die
Systemzeit mit dem GPS-Signal und stellt sie im lokalen Netzwerk bereit.

---

## Inhaltsverzeichnis

1. [Funktionsprinzip](#1-funktionsprinzip)
2. [Voraussetzungen & Hardware](#2-voraussetzungen--hardware)
3. [Software installieren](#3-software-installieren)
4. [GPS-Gerät identifizieren](#4-gps-gerät-identifizieren)
5. [gpsd konfigurieren](#5-gpsd-konfigurieren)
6. [Chrony konfigurieren](#6-chrony-konfigurieren)
7. [Dienste starten und prüfen](#7-dienste-starten-und-prüfen)
8. [Fehlerbehebung](#8-fehlerbehebung)
9. [Statistik-Analyse](#9-statistik-analyse)
10. [Referenz: chrony.conf Parameter](#10-referenz-chronyconf-parameter)

---

## 1. Funktionsprinzip

```text
GPS-Modul (USB)
      │
      ▼
  gpsd (Daemon)
      │  liefert Zeitdaten über Shared Memory (SHM 0)
      ▼
  chrony (NTP-Daemon)
      │  synchronisiert Systemzeit, kompensiert USB-Latenz
      ▼
  Netzwerk-Clients (NTP-Anfragen)
```

`gpsd` liest die NMEA-Sätze des GPS-Moduls und schreibt die Zeitinformation in
ein Shared-Memory-Segment. Chrony liest dieses Segment als Referenzuhr (`refclock SHM 0`)
und kompensiert dabei die bekannte USB-Bus-Latenz über den `offset`-Parameter.

---

## 2. Voraussetzungen & Hardware

- Linux-System (Ubuntu/Debian, Raspberry Pi OS)
- USB-GPS-Modul (empfohlen: **VK-162 mit TCXO EEPROM**)
  - TCXO sorgt für temperaturkompensierte Frequenz → geringerer Drift
  - EEPROM ermöglicht persistente Konfiguration
- Internetverbindung für die initiale Installation
- GPS-Empfang am Aufstellungsort (Fensterplatz oder Außenantenne)

> **Tipp:** Für beste Genauigkeit das GPS-Modul möglichst nahe am Fenster oder
> mit einer Außenantenne betreiben. Kalter Start kann bis zu 15 Minuten dauern,
> bis ein 3D-Fix erreicht wird.

---

## 3. Software installieren

```bash
sudo apt update
sudo apt install gpsd gpsd-clients chrony pps-tools
```

| Paket | Funktion |
| --- | --- |
| `gpsd` | GPS-Daemon: liest das GPS-Modul und stellt Daten bereit |
| `gpsd-clients` | Tools wie `gpsmon`, `gpspipe` zur Diagnose |
| `chrony` | NTP-Daemon: empfängt GPS-Zeit und verteilt sie im Netz |
| `pps-tools` | Tools für PPS-Signale (Pulse Per Second) bei präzisen Modulen |

---

## 4. GPS-Gerät identifizieren

Nach dem Anstecken des USB-GPS-Moduls das Gerät finden:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Typische Ausgabe:

```text
/dev/ttyACM0
```

Weitere Details zum Gerät:

```bash
dmesg | grep -i "tty\|usb" | tail -20
```

Das Gerät (`/dev/ttyACM0` oder `/dev/ttyUSB0`) wird in den folgenden Schritten
als `DEVICES`-Wert verwendet.

---

## 5. gpsd konfigurieren

### 5.1 Hauptkonfiguration

```bash
sudo nano /etc/default/gpsd
```

Inhalt:

```bash
START_DAEMON="true"
USBAUTO="false"
DEVICES="/dev/ttyACM0"
GPSD_OPTIONS="-n"
```

| Option | Bedeutung |
| --- | --- |
| `START_DAEMON="true"` | gpsd wird beim Systemstart automatisch gestartet |
| `USBAUTO="false"` | Kein automatisches USB-Hotplug (stabiler für feste Zeitserver) |
| `DEVICES="/dev/ttyACM0"` | Pfad zum GPS-Gerät |
| `GPSD_OPTIONS="-n"` | GPS-Modul sofort pollen, ohne auf eine Client-Verbindung zu warten |

### 5.2 Socket-Konfiguration bei deaktiviertem IPv6

Falls IPv6 auf dem System deaktiviert ist (z.B. durch Provider-Einstellung),
startet `gpsd.socket` möglicherweise nicht korrekt. Lösung:

```bash
sudo systemctl edit gpsd.socket
```

Folgenden Inhalt einfügen:

```ini
[Socket]
ListenStream=
ListenStream=/run/gpsd.sock
ListenStream=127.0.0.1:2947
BindIPv6Only=no
```

Danach neu laden:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gpsd.socket
sudo systemctl restart gpsd
```

### 5.3 GPS-Empfang prüfen

Live-Ansicht mit vollständigen Satelliteninfos:

```bash
gpsmon
```

Oder nur die Positionsdaten im JSON-Format:

```bash
gpspipe -w | grep TPV
```

Wichtig ist der `"mode"`-Wert:

| Mode | Bedeutung |
| --- | --- |
| `0` | Unknown – keine Daten |
| `1` | No Fix – Zeit/Satelliten sichtbar, aber kein GPS-Fix |
| `2` | 2D Fix – mindestens 3 Satelliten (keine Höhe) |
| `3` | **3D Fix** – mindestens 4 Satelliten, vollständiger Fix |

Erst ab `"mode":3` liefert das Modul zuverlässige Zeitinformationen.

---

## 6. Chrony konfigurieren

### 6.1 Konfigurationsdatei bearbeiten

```bash
sudo nano /etc/chrony/chrony.conf
```

Relevante Zeilen hinzufügen bzw. anpassen:

```text
# GPS-Zeitquelle über Shared Memory (SHM) von gpsd
refclock SHM 0 refid GPS precision 1e-3 offset 0.0668 delay 0.1 poll 3 filter 16 trust prefer

# Zugriff für das lokale Netzwerk erlauben
allow 192.168.178.0/24
```

### 6.2 Parameter im Detail

| Parameter | Wert | Beschreibung |
| --- | --- | --- |
| `refclock SHM 0` | – | Liest aus dem Shared-Memory-Segment (NTP0), das `gpsd` beschreibt |
| `refid GPS` | `GPS` | 4-stellige ID, sichtbar in `chronyc sources` |
| `precision` | `1e-3` | Deklarierte Genauigkeit (1 ms); realistisch für USB-GPS |
| `offset` | `0.0668` | **Kalibrierung:** Kompensiert ~66,8 ms USB-Bus-Latenz (muss ggf. angepasst werden) |
| `delay` | `0.1` | Geschätzte feste Verzögerung; niedrig → bevorzugt gegenüber Netzwerk-Peers |
| `poll` | `3` | Abfrageintervall: 2³ = 8 Sekunden |
| `filter` | `16` | Medianfilter über 16 Proben → dämpft USB-Scheduling-Jitter |
| `trust` | – | Quelle wird als vertrauenswürdig eingestuft |
| `prefer` | – | GPS bleibt primäre Zeitquelle gegenüber Netzwerk-Servern |

> **Offset-Kalibrierung:** Der `offset`-Wert von `0.0668` ist ein Startwert.
> Nach einigen Stunden Betrieb kann er mit dem [`stats.sh`](stats.sh)-Script
> präzise ermittelt werden (siehe [Abschnitt 9](#9-statistik-analyse)).

### 6.3 Chrony neu starten

```bash
sudo systemctl restart chrony
```

---

## 7. Dienste starten und prüfen

### 7.1 Shared Memory auf Datenfluss prüfen

Stellt sicher, dass `gpsd` Daten in den Shared-Memory-Bereich schreibt:

```bash
sudo ntpshmmon
```

Es sollten sich regelmäßig Zeitstempel aktualisieren (Spalte `clock` ändert sich).

### 7.2 Benutzer in die richtige Gruppe eintragen

Damit `gpsd` auf das serielle GPS-Gerät zugreifen kann:

```bash
sudo usermod -aG dialout gpsd
sudo systemctl restart gpsd
sudo systemctl restart chrony
```

### 7.3 Chrony-Quellen prüfen

```bash
chronyc sources -v
```

Beispielausgabe nach erfolgreichem GPS-Lock:

```text
  .-- Source mode  '^' = server, '=' = peer, '#' = local clock.
 / .- Source state '*' = current best, '+' = combined, '-' = not combined,
| /             'x' = may be in error, '~' = too variable, '?' = unusable.
||                                                 .- xxxx [ yyyy ] +/- zzzz
||      Reachability register (octal) -.           |  xxxx = adjusted offset,
||      Log2(Polling interval) --.      |          |  yyyy = measured offset,
||                                \     |          |  zzzz = estimated error.
||                                 |    |           \
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
#* GPS                           0   3   377     5   +549us[+1029us] +/-   51ms
^- ntp1.example.com              2   6   377    37  +1455us[ +257us] +/- 9430us
```

| Symbol | Bedeutung |
| --- | --- |
| `#*` | Lokale Referenzuhr, aktiv als primäre Quelle |
| `^-` | Netzwerk-Server, verfügbar aber nicht aktiv genutzt |
| `377` | Reachability-Register: alle 8 der letzten 8 Polls erfolgreich |

### 7.4 Synchronisierungsstatus

```bash
chronyc tracking
```

Wichtige Felder:

```text
Reference ID    : 47505300 (GPS)
Stratum         : 1
System time     : 0.000123456 seconds fast of NTP time
Last offset     : +0.000045678 seconds
RMS offset      : 0.000234567 seconds
Frequency       : 12.345 ppm fast
```

Stratum 1 bedeutet: direkte GPS-Referenz, höchste Präzisionsstufe.

### 7.5 Statistik-Log ansehen

```bash
cat /var/log/chrony/statistics.log | grep GPS
```

---

## 8. Fehlerbehebung

### GPS-Quelle im Status `?` (unusable)

Ausgabe:

```text
#? GPS   0   4   0   -   +0ns[ +0ns] +/- 0ns
```

Ursachen und Lösungen:

1. **gpsd schreibt keine Daten in SHM** → `sudo ntpshmmon` prüfen
2. **GPS hat noch keinen Fix** → `gpsmon` starten, auf `mode: 3` warten
3. **Falsches Gerät** → `/etc/default/gpsd` → `DEVICES` prüfen
4. **gpsd ohne `-n` gestartet** → `GPSD_OPTIONS="-n"` setzen

### `ntpshmmon` zeigt keine Daten

```bash
# gpsd-Status prüfen
sudo systemctl status gpsd

# Gerätezugriff testen
sudo gpsd -N -D5 /dev/ttyACM0
```

### Permission Denied auf /dev/ttyACM0

```bash
ls -la /dev/ttyACM0
# crw-rw---- 1 root dialout ...

sudo usermod -aG dialout gpsd
sudo usermod -aG dialout $USER  # Falls auch manuell getestet wird
```

### Hoher Offset (> 100 ms)

Der `offset`-Wert in der `chrony.conf` muss kalibriert werden.
Vorgehen: [`stats.sh`](stats.sh) ausführen und den empfohlenen Wert übernehmen.

---

## 9. Statistik-Analyse

Das Script [`stats.sh`](stats.sh) analysiert das Chrony-Statistiklog und bewertet
die Qualität der GPS-Synchronisation anhand der letzten 100 Proben.

### Logging in Chrony aktivieren

In `/etc/chrony/chrony.conf` sicherstellen:

```text
log statistics
logdir /var/log/chrony
```

### Script ausführen

```bash
chmod +x stats.sh
./stats.sh
```

### Beispielausgabe

```text
----------------------------------------------------------
Chrony GPS Statistik Analyse (Letzte 100 Proben)
----------------------------------------------------------
Anzahl Proben: 100
Durchschn. Abweichung (Offset): 0.412 ms
Durchschn. Jitter (Std Dev):    1.203 ms
----------------------------------------------------------
Bewertung: GUT (Stabil im Betrieb)
----------------------------------------------------------
EMPFEHLUNG: Dein GPS hinkt minimal. Erhöhe den 'offset' in
der chrony.conf um ca. 0.0005 bis 0.001 für Latenzoptimierung.
----------------------------------------------------------
```

### Bewertungsskala

| Durchschn. Offset | Bewertung | Maßnahme |
| --- | --- | --- |
| < 0,5 ms | **Exzellent** | Keine Änderung nötig |
| 0,5–1,5 ms | **Gut** | `offset` um 0,0005–0,001 erhöhen |
| > 1,5 ms | **Optimierungsbedarf** | `offset` deutlich anpassen |

Bei hohem Jitter (Std Dev > 5 ms) den `filter`-Wert in der `chrony.conf`
erhöhen (z.B. von `16` auf `32`).

### Offset-Wert anpassen

Nach der Analyse den Wert in der `chrony.conf` aktualisieren:

```bash
sudo nano /etc/chrony/chrony.conf
# offset 0.0668  →  offset 0.0673  (Beispiel)

sudo systemctl restart chrony
```

---

## 10. Referenz: chrony.conf Parameter

Vollständige Konfigurationszeile:

```text
refclock SHM 0 refid GPS precision 1e-3 offset 0.0668 delay 0.1 poll 3 filter 16 trust prefer
```

| Parameter | Wert | Typ | Beschreibung |
| --- | --- | --- | --- |
| `refclock SHM 0` | – | Pflicht | Shared-Memory-Segment 0 (von gpsd) |
| `refid` | `GPS` | Optional | Anzeigename in chronyc (max. 4 Zeichen) |
| `precision` | `1e-3` | Optional | Deklarierte Genauigkeit in Sekunden |
| `offset` | `0.0668` | Kalibrierung | Statische Offset-Kompensation in Sekunden |
| `delay` | `0.1` | Optional | Geschätzte Übertragungsverzögerung |
| `poll` | `3` | Optional | Log₂ des Abfrageintervalls (3 = 8 Sek.) |
| `filter` | `16` | Optional | Anzahl Proben für den Medianfilter |
| `trust` | – | Optional | Quelle wird nie als fehlerhaft markiert |
| `prefer` | – | Optional | Bevorzugte Quelle gegenüber Netzwerk-Peers |

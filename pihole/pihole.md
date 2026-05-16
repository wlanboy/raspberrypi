# Pi-hole

Pi-hole ist ein netzwerkweiter Werbeblocker, der als DNS-Sinkhole fungiert. Er blockiert Werbe- und Tracking-Domains für alle Geräte im lokalen Netzwerk.

## Voraussetzungen

- Docker und Docker Compose installiert
- Feste IP-Adresse des Servers bekannt

## Konfiguration

Die Konfiguration erfolgt über Umgebungsvariablen. Erstelle dazu eine `.env`-Datei im Verzeichnis `pihole/`:

```env
SERVER_IP=192.168.1.100
WEBPASSWORD=mein-sicheres-passwort
```

| Variable | Pflicht | Standard | Beschreibung |
|---|---|---|---|
| `SERVER_IP` | ja | — | IP-Adresse des Servers im lokalen Netzwerk |
| `WEBPASSWORD` | nein | `pihole` | Passwort für das Web-Interface |

## Ports

| Port (Host) | Port (Container) | Protokoll | Funktion |
|---|---|---|---|
| `8080` | `80` | TCP | Web-Interface (HTTP) |
| `8443` | `443` | TCP | Web-Interface (HTTPS) |
| `SERVER_IP:53` | `53` | TCP/UDP | DNS-Anfragen |
| `SERVER_IP:67` | `67` | UDP | DHCP (optional) |

Die DNS- und DHCP-Ports sind an `SERVER_IP` gebunden, damit kein Konflikt mit dem Host-Resolver entsteht.

## Volumes

| Host-Pfad | Container-Pfad | Inhalt |
|---|---|---|
| `/pihole/etc` | `/etc/pihole/` | Pi-hole-Konfiguration und Blocklisten |
| `/pihole/dns` | `/etc/dnsmasq.d/` | dnsmasq-Konfigurationsdateien |

Die Verzeichnisse werden beim ersten Start automatisch angelegt.

## Starten

```bash
docker compose up -d
```

Oder ohne `.env`-Datei mit direkter Variablenübergabe:

```bash
SERVER_IP=192.168.1.100 docker compose up -d
```

## Stoppen

```bash
docker compose down
```

## Web-Interface

Nach dem Start ist das Web-Interface erreichbar unter:

```
http://SERVER_IP:8080/admin
```

Beim ersten Login das Standard-Passwort `pihole` sofort ändern, sofern kein eigenes `WEBPASSWORD` gesetzt wurde.

## DNS-Server im Router eintragen

Damit Pi-hole für alle Geräte im Netzwerk aktiv ist, muss `SERVER_IP` als primärer DNS-Server im Router eingetragen werden. Die Einstellung findet sich üblicherweise unter:

```
Router-Oberfläche → DHCP-Einstellungen → DNS-Server
```

Als Fallback-DNS empfiehlt sich ein öffentlicher Resolver (z. B. `8.8.8.8`), der greift, wenn Pi-hole nicht erreichbar ist.

## Upstream-DNS-Server

Die voreingestellten Upstream-DNS-Server sind:

| Variable | Wert | Anbieter |
|---|---|---|
| `DNS1` | `192.168.178.1` | Lokaler Router (Fritz!Box) |
| `DNS2` | `8.8.8.8` | Google Public DNS |

Diese können in der `docker-compose.yml` angepasst werden.

## Logs ansehen

```bash
docker compose logs -f
```

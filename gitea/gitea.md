# Gitea – Self-hosted Git-Server mit Docker Compose

Diese Anleitung beschreibt die Einrichtung einer eigenen Gitea-Instanz mit MariaDB als
Datenbank, HTTPS über eigene Zertifikate und persistentem Datenspeicher auf einem
SATA-Laufwerk.

---

## Inhaltsverzeichnis

1. [Architektur & Überblick](#1-architektur--überblick)
2. [Voraussetzungen](#2-voraussetzungen)
3. [Verzeichnisse anlegen](#3-verzeichnisse-anlegen)
4. [TLS-Zertifikate bereitstellen](#4-tls-zertifikate-bereitstellen)
5. [Docker Compose starten](#5-docker-compose-starten)
6. [Gitea Web-Einrichtung](#6-gitea-web-einrichtung)
7. [Konfiguration im Detail](#7-konfiguration-im-detail)
8. [Betrieb & Wartung](#8-betrieb--wartung)
9. [Alternative: Native Installation (ohne Docker)](#9-alternative-native-installation-ohne-docker)

---

## 1. Architektur & Überblick

```text
Browser / Git-Client
        │  HTTPS :3300
        ▼
  ┌─────────────┐        internes Netz "gitea"
  │   gitea     │ ──────────────────────────────┐
  │  Container  │                               │
  └─────────────┘                               ▼
        │                              ┌──────────────┐
        │  /data  →  /mnt/sata/gitea/git│   mariadb    │
        │  /certs →  /local-ca/...     │  Container   │
        └───────────────────────────── └──────────────┘
```

- **Gitea** läuft als App-Container auf Port 3300 (HTTPS)
- **MariaDB** läuft als separater Datenbank-Container im selben Docker-Netz
- Beide Container kommunizieren über das interne Bridge-Netz `gitea`
- SSH ist deaktiviert – ausschließlich HTTPS für Git-Operationen
- Daten liegen persistent auf `/mnt/sata/gitea/` (SATA-Laufwerk)

---

## 2. Voraussetzungen

- Docker und Docker Compose installiert
- SATA-Laufwerk eingebunden unter `/mnt/sata/`
- Eigene CA und TLS-Zertifikat für `git.gmk.lan` vorhanden
  (siehe [ca/](../ca/) für die CA-Einrichtung)
- DNS-Eintrag oder `/etc/hosts`-Eintrag für `git.gmk.lan`

Docker installieren (falls noch nicht vorhanden):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

---

## 3. Verzeichnisse anlegen

Persistente Datenverzeichnisse auf dem SATA-Laufwerk erstellen:

```bash
sudo mkdir -p /mnt/sata/gitea/git
sudo mkdir -p /mnt/sata/gitea/db
```

Berechtigungen setzen – Gitea läuft im Container als UID/GID 1000:

```bash
sudo chown -R 1000:1000 /mnt/sata/gitea/git
sudo chown -R 999:999 /mnt/sata/gitea/db
```

> **Hinweis:** MariaDB verwendet intern UID 999. Gitea verwendet UID 1000
> (konfiguriert über `USER_UID` / `USER_GID` in der Compose-Datei).

---

## 4. TLS-Zertifikate bereitstellen

Gitea ist für HTTPS konfiguriert und erwartet Zertifikat und Key an diesen Pfaden:

```text
/local-ca/git.gmk.lan/git.crt   ← Zertifikat
/local-ca/git.gmk.lan/git.key   ← Privater Schlüssel
```

Diese werden schreibgeschützt in den Container eingebunden (`:ro`).

Falls die Zertifikate noch nicht existieren, mit der lokalen CA erstellen
(siehe [ca/](../ca/)). Beispiel mit `openssl`:

```bash
sudo mkdir -p /local-ca/git.gmk.lan

# Privaten Schlüssel erzeugen
sudo openssl genrsa -out /local-ca/git.gmk.lan/git.key 4096

# CSR erzeugen
sudo openssl req -new \
  -key /local-ca/git.gmk.lan/git.key \
  -out /local-ca/git.gmk.lan/git.csr \
  -subj "/CN=git.gmk.lan/O=GMK/C=DE"

# Zertifikat mit der lokalen CA signieren (Laufzeit: 10 Jahre)
sudo openssl x509 -req -days 3650 \
  -in /local-ca/git.gmk.lan/git.csr \
  -CA /local-ca/ca.crt \
  -CAkey /local-ca/ca.key \
  -CAcreateserial \
  -out /local-ca/git.gmk.lan/git.crt
```

---

## 5. Docker Compose starten

### 5.1 Passwörter setzen

In der [`docker-compose.yml`](docker-compose.yml) die Platzhalter
`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` durch sichere Passwörter ersetzen:

```bash
# Zufälliges Passwort generieren
openssl rand -base64 32
```

Folgende Stellen anpassen:

| Variable | Beschreibung |
| --- | --- |
| `MYSQL_ROOT_PASSWORD` | Root-Passwort der MariaDB |
| `MYSQL_PASSWORD` | Passwort für den Gitea-Datenbankbenutzer |
| `GITEA__database__PASSWD` | Muss identisch mit `MYSQL_PASSWORD` sein |

### 5.2 Compose starten

```bash
cd /home/$USER/git/raspberrypi/gitea
docker compose up -d
```

Logs beobachten:

```bash
docker compose logs -f
```

Beide Container sollten nach kurzer Zeit laufen:

```bash
docker compose ps
```

```text
NAME         IMAGE                  STATUS          PORTS
gitea        gitea/gitea:latest     Up              0.0.0.0:3300->3300/tcp
gitea-db     mariadb:12-noble       Up              3306/tcp
```

---

## 6. Gitea Web-Einrichtung

Nach dem Start die Gitea-Oberfläche im Browser öffnen:

```text
https://git.gmk.lan:3300
```

Beim ersten Aufruf erscheint der **Installationsassistent**. Die meisten Werte
sind bereits durch die Umgebungsvariablen vorausgefüllt. Folgendes prüfen:

| Feld | Wert |
| --- | --- |
| Datenbanktyp | MySQL |
| Datenbankhost | `mariadb:3306` |
| Datenbankname | `gitea` |
| Datenbankbenutzer | `gitea` |
| Site-URL | `https://git.gmk.lan:3300/` |

Am Ende des Formulars den **Administrator-Account** anlegen und auf
**Gitea installieren** klicken.

> **Tipp:** Falls der Browser der selbstsignierten CA nicht vertraut,
> das CA-Zertifikat im System oder Browser importieren.

---

## 7. Konfiguration im Detail

### 7.1 Server-Einstellungen

| Umgebungsvariable | Wert | Bedeutung |
| --- | --- | --- |
| `GITEA__server__PROTOCOL` | `https` | Ausschließlich HTTPS, kein HTTP |
| `GITEA__server__DOMAIN` | `git.gmk.lan` | Hostname der Instanz |
| `GITEA__server__ROOT_URL` | `https://git.gmk.lan:3300/` | Basis-URL für alle Links |
| `GITEA__server__HTTP_PORT` | `3300` | Interner Port im Container |
| `GITEA__server__CERT_FILE` | `/certs/git.crt` | Pfad zum TLS-Zertifikat (im Container) |
| `GITEA__server__KEY_FILE` | `/certs/git.key` | Pfad zum privaten TLS-Schlüssel |
| `GITEA__server__DISABLE_SSH` | `true` | SSH komplett deaktiviert |
| `GITEA__server__START_SSH_SERVER` | `false` | Kein interner SSH-Server |

### 7.2 Datenbank-Einstellungen

| Umgebungsvariable | Wert |
| --- | --- |
| `GITEA__database__DB_TYPE` | `mysql` |
| `GITEA__database__HOST` | `mariadb:3306` (Container-Name im Docker-Netz) |
| `GITEA__database__NAME` | `gitea` |
| `GITEA__database__USER` | `gitea` |
| `GITEA__database__PASSWD` | (gesetztes Datenbankpasswort) |

### 7.3 Volumes

| Host-Pfad | Container-Pfad | Inhalt |
| --- | --- | --- |
| `/mnt/sata/gitea/git` | `/data` | Git-Repositories, Gitea-Daten |
| `/mnt/sata/gitea/db` | `/var/lib/mysql` | MariaDB-Datenbank |
| `/local-ca/git.gmk.lan/git.crt` | `/certs/git.crt` | TLS-Zertifikat (read-only) |
| `/local-ca/git.gmk.lan/git.key` | `/certs/git.key` | TLS-Schlüssel (read-only) |
| `/etc/timezone` | `/etc/timezone` | Zeitzone des Hosts übernehmen |
| `/etc/localtime` | `/etc/localtime` | Lokalzeit des Hosts übernehmen |

---

## 8. Betrieb & Wartung

### Container-Status prüfen

```bash
docker compose ps
docker compose logs gitea
docker compose logs mariadb
```

### Neustart

```bash
docker compose restart
```

### Update auf neue Gitea-Version

```bash
docker compose pull
docker compose up -d
```

> Da `gitea/gitea:latest` verwendet wird, zieht `docker compose pull` immer
> die aktuellste Version. Für Produktivumgebungen empfiehlt sich eine gepinnte
> Version wie `gitea/gitea:1.22`.

### Backup

Für ein vollständiges Backup müssen zwei Bereiche gesichert werden:

```bash
# 1. Gitea-Daten (Repositories, Konfiguration, Uploads)
sudo tar czf gitea-data-$(date +%F).tar.gz /mnt/sata/gitea/git

# 2. Datenbank-Dump (Container muss laufen)
docker exec gitea-db mysqldump -u gitea -p gitea > gitea-db-$(date +%F).sql
```

### Zertifikat erneuern

Nach dem Erneuern des Zertifikats unter `/local-ca/git.gmk.lan/`:

```bash
docker compose restart gitea
```

Das neue Zertifikat wird beim Start eingelesen (Volume-Mount).

---

## 9. Alternative: Native Installation (ohne Docker)

Für Systeme ohne Docker kann Gitea direkt als Systemdienst betrieben werden.

### Service-Benutzer anlegen

```bash
sudo adduser --system --shell /bin/bash \
  --gecos 'Git Version Control' \
  --group --disabled-password \
  --home /home/git git

sudo mkdir /gitea
sudo chown git:git -R /gitea
sudo chmod 755 -R /gitea
```

### Gitea-Binary herunterladen

```bash
cd /gitea

# Für Raspberry Pi (ARM 64-bit)
wget -O gitea https://dl.gitea.io/gitea/1.22.3/gitea-1.22.3-linux-arm64

# Für Raspberry Pi (ARM 32-bit / ARMv6)
# wget -O gitea https://dl.gitea.io/gitea/1.22.3/gitea-1.22.3-linux-arm-6

chmod +x gitea
```

> Aktuelle Versionsnummern unter [dl.gitea.io/gitea/](https://dl.gitea.io/gitea/) prüfen.

### Systemd-Dienst erstellen

```bash
sudo tee /etc/systemd/system/gitea.service > /dev/null << 'EOF'
[Unit]
Description=Gitea (Git with a cup of tea)
After=syslog.target
After=network.target

[Service]
RestartSec=2s
Type=simple
User=git
Group=git
WorkingDirectory=/gitea
ExecStart=/gitea/gitea web
Restart=always
Environment=USER=git HOME=/home/git GITEA_WORK_DIR=/gitea

[Install]
WantedBy=multi-user.target
EOF
```

### Dienst aktivieren und starten

```bash
sudo systemctl daemon-reload
sudo systemctl enable gitea
sudo systemctl start gitea
sudo systemctl status gitea
```

Gitea ist dann unter `http://<IP>:3000` erreichbar.

# Git & Maven Toolsammlung

Diese Sammlung enthält Python- und Shell-Scripte für den täglichen Umgang mit mehreren
Git-Repositories sowie für die automatische Pflege von Maven-Abhängigkeiten.

---

## Inhaltsverzeichnis

1. [Schnellstart: Aliases einrichten](#1-schnellstart-aliases-einrichten)
2. [Übersicht aller Tools](#2-übersicht-aller-tools)
3. [git_pull_all.py – Alle Repos aktualisieren](#3-git_pull_allpy--alle-repos-aktualisieren)
4. [git_status_all.py – Status aller Repos](#4-git_status_allpy--status-aller-repos)
5. [scan_git_repos.py – Repos auflisten](#5-scan_git_repospy--repos-auflisten)
6. [mirror_git_repos.py – GitHub → Gitea spiegeln](#6-mirror_git_repospy--github--gitea-spiegeln)
7. [gh-no-mirror.py – Repos ohne Mirror-Tag finden](#7-gh-no-mirrorpy--repos-ohne-mirror-tag-finden)
8. [update-pom.py – Maven-Abhängigkeiten aktualisieren](#8-update-pompy--maven-abhängigkeiten-aktualisieren)
9. [find_big_files_in_git_history.sh – Große Dateien in Git-History finden](#9-find_big_files_in_git_historysh--große-dateien-in-git-history-finden)

---

## 1. Schnellstart: Aliases einrichten

Das Script [`add_aliases.sh`](add_aliases.sh) trägt alle Tools als kurze Shell-Aliases
in `~/.bashrc` ein, sodass sie von überall aufrufbar sind.

```bash
chmod +x add_aliases.sh
./add_aliases.sh
source ~/.bashrc
```

Mit `-f` werden bestehende Aliases überschrieben:

```bash
./add_aliases.sh -f
```

Nach der Einrichtung stehen folgende Kurzbefehle zur Verfügung:

| Alias | Befehl | Bedeutung |
| --- | --- | --- |
| `gu` | `git_pull_all.py ~/git` | Alle Repos **u**pdaten (pull) |
| `gs` | `git_status_all.py ~/git` | **S**tatus aller Repos anzeigen |
| `gl` | `scan_git_repos.py ~/git` | Repos **l**isten (Branch + Remote) |
| `gm` | `mirror_git_repos.py ~/git` | GitHub → Gitea **m**irroren |
| `gnm` | `gh-no-mirror.py` | Repos ohne Mirror-Tag anzeigen |
| `up` | `update-pom.py` | Maven-Abhängigkeiten **up**daten |

---

## 2. Übersicht aller Tools

| Script | Sprache | Zweck |
| --- | --- | --- |
| [`add_aliases.sh`](add_aliases.sh) | Bash | Aliases in `~/.bashrc` eintragen |
| [`git_pull_all.py`](git_pull_all.py) | Python | `git pull` in allen Unterordner-Repos |
| [`git_status_all.py`](git_status_all.py) | Python | `git status` für alle Repos auf einen Blick |
| [`scan_git_repos.py`](scan_git_repos.py) | Python | Branch und Remote-URLs aller Repos auflisten |
| [`mirror_git_repos.py`](mirror_git_repos.py) | Python | GitHub-Repos mit Topic `mirror` nach Gitea spiegeln |
| [`gh-no-mirror.py`](gh-no-mirror.py) | Python | GitHub-Repos ohne `mirror`-Topic finden |
| [`update-pom.py`](update-pom.py) | Python | Maven `pom.xml` auf neueste Versionen aktualisieren |
| [`find_big_files_in_git_history.sh`](find_big_files_in_git_history.sh) | Bash | Dateien > 50 KB in der Git-History aufspüren |

---

## 3. git_pull_all.py – Alle Repos aktualisieren

Führt `git pull` in jedem Git-Repository aus, das sich als direkter Unterordner
im angegebenen Basisverzeichnis befindet. Repos ohne Remote werden übersprungen.

```bash
python3 git_pull_all.py [VERZEICHNIS]
# oder per Alias:
gu
```

Ohne Argument wird das aktuelle Verzeichnis verwendet.

```text
📂 Pulling in raspberrypi
Already up to date.
📂 Pulling in my-app
Updating abc1234..def5678
⏭️  local-only hat kein Remote konfiguriert – wird übersprungen
```

### Verhalten bei Sonderfällen

- Verzeichnisse ohne `.git`-Ordner werden stillschweigend übersprungen
- Repos ohne Remote (`git remote` leer) werden mit Hinweis übersprungen
- Fehler beim Pull werden gemeldet, das Script läuft aber weiter

---

## 4. git_status_all.py – Status aller Repos

Zeigt `git status --short` für alle Git-Repos im Basisverzeichnis, alphabetisch sortiert.
Repos ohne Änderungen werden als "sauber" markiert.

```bash
python3 git_status_all.py [VERZEICHNIS]
# oder per Alias:
gs
```

```text
✅ my-clean-repo [main] – sauber
📂 my-changed-repo [feature/xyz] – Änderungen:
    M src/main/App.java
   ?? new-untracked-file.txt
✅ raspberrypi [main] – sauber
```

Jede Zeile enthält den Repo-Namen und den aktuellen Branch in eckigen Klammern.

---

## 5. scan_git_repos.py – Repos auflisten

Listet alle Git-Repositories im angegebenen Verzeichnis mit Branch-Name und
konfigurierten Remote-URLs auf. Ohne Argument wird das Home-Verzeichnis durchsucht.

```bash
python3 scan_git_repos.py [VERZEICHNIS]
# oder per Alias:
gl
```

```text
🔍 Scanning Git repositories in: /home/samuel/git

📁 raspberrypi
   🌿 Branch: main
   🔗 Remote: https://github.com/wlanboy/raspberrypi.git

📁 my-app
   🌿 Branch: develop
   🔗 Remote: https://git.gmk.lan:3300/github/my-app.git
   🔗 Remote: https://github.com/wlanboy/my-app.git

📁 local-only
   🌿 Branch: main
   🔗 Kein Remote konfiguriert
```

---

## 6. mirror_git_repos.py – GitHub → Gitea spiegeln

Liest alle eigenen GitHub-Repositories, filtert nach dem Topic `mirror` und erstellt
für jedes gefundene Repo einen Mirror in der Gitea-Instanz (Organisation `github`).
Bereits vorhandene Mirrors werden übersprungen.

### Umgebungsvariablen

Drei Variablen müssen vor dem Start gesetzt sein:

```bash
export GITHUB_USERNAME="dein-github-username"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITEA_TOKEN="dein-gitea-api-token"
```

Den Gitea-Token erstellen unter: `https://git.gmk.lan:3300/user/settings/applications`

```bash
python3 mirror_git_repos.py
# oder per Alias:
gm
```

### Sync-Ablauf

1. Optional: Alle bestehenden Repos in der Gitea-Org `github` löschen
2. Alle eigenen GitHub-Repos abrufen
3. Repos **ohne** Topic `mirror` überspringen
4. Für jeden gefundenen Repo einen Mirror in Gitea anlegen (alle 8 Stunden synchronisiert)

```text
🚀 Starte Mirror-Sync...
❓ Alle Repos in Gitea-Org löschen? (ja/[nein]): nein
⏭ Überspringe raspberrypi (existiert bereits)
➕ Erstelle Mirror für my-app (Private: False)...
✔ Spiegel erstellt: my-app
```

### Konfiguration

In [`mirror_git_repos.py`](mirror_git_repos.py) anpassbar:

| Variable | Standardwert | Bedeutung |
| --- | --- | --- |
| `TOPIC_FILTER` | `"mirror"` | Nur Repos mit diesem GitHub-Topic werden gespiegelt |
| `GITEA_URL` | `"https://git.gmk.lan:3300"` | URL der Gitea-Instanz |
| `GITEA_ORG` | `"github"` | Ziel-Organisation in Gitea |
| `MIRROR_INTERVAL` | `"8h0m0s"` | Wie oft Gitea den Mirror aktualisiert |

> **Hinweis:** Das Script verwendet `ssl._create_unverified_context()`, da die
> Gitea-Instanz ein selbstsigniertes Zertifikat nutzt.

---

## 7. gh-no-mirror.py – Repos ohne Mirror-Tag finden

Listet alle eigenen GitHub-Repos, die das Topic `mirror` **nicht** haben. Nützlich,
um zu prüfen, welche Repos noch nicht für den Mirror-Sync vorgemerkt sind.

Voraussetzung: GitHub CLI installiert und eingeloggt mit `gh auth login`.

```bash
python3 gh-no-mirror.py
# oder per Alias:
gnm
```

```text
=== Kein 'mirror' Topic (aber andere Tags vorhanden) ===
  wlanboy/my-private-tool
  wlanboy/work-in-progress

=== Gar keine Topics ===
  wlanboy/old-experiment
  wlanboy/untitled-project
```

### Repo für Mirror vorbereiten

```bash
# Topic auf GitHub setzen
gh repo edit wlanboy/my-private-tool --add-topic mirror

# Danach mirror_git_repos.py ausführen
gm
```

---

## 8. update-pom.py – Maven-Abhängigkeiten aktualisieren

Liest eine `pom.xml`, prüft für jede Dependency, jedes Plugin und das Parent-POM
die aktuelle Release-Version auf Maven Central und aktualisiert die Datei in-place.
Anschließend wird `mvn package -DskipTests` ausgeführt, um den Build zu validieren.
Bei Fehlschlag wird die Original-`pom.xml` automatisch wiederhergestellt.

Voraussetzungen: Python 3.10+ und Maven (`mvn`) im PATH.

```bash
python3 update-pom.py [VERZEICHNIS]
# oder per Alias (im aktuellen Verzeichnis):
up
```

Ohne Argument wird im aktuellen Verzeichnis nach `pom.xml` gesucht.

### Ausführungsschritte

1. Backup der `pom.xml` erstellen (`pom.xml.bak`)
2. Alle `<dependency>`, `<plugin>` und `<parent>`-Versionen prüfen
3. Neueste stabile Version von Maven Central abfragen
4. Downgrades werden automatisch abgelehnt
5. `pom.xml` mit aktualisierten Versionen schreiben
6. `mvn package -DskipTests` ausführen
7. Bei **Erfolg**: Backup löschen, fertige Commit-Message ausgeben
8. Bei **Fehler**: `pom.xml.bak` wiederherstellen

```text
Backup erstellt: pom.xml.bak

Lese pom.xml und prüfe Abhängigkeiten ...

  Prüfe org.springframework.boot:spring-boot-starter-parent  (3.3.0)
    -> Update: 3.3.0 → 3.4.1
  Prüfe org.springframework.boot:spring-boot-starter-web  (3.3.0)
    -> bereits aktuell (3.3.0)
  Prüfe com.fasterxml.jackson.core:jackson-databind  (2.17.0)
    -> Update: 2.17.0 → 2.18.2

2 Update(s) in pom.xml geschrieben.

Starte Maven-Build: mvn package -DskipTests ...
Build erfolgreich.

============================================================
COMMIT MESSAGE
============================================================
pom updater: bump dependencies to latest releases

- org.springframework.boot:spring-boot-starter-parent: 3.3.0 → 3.4.1
- com.fasterxml.jackson.core:jackson-databind: 2.17.0 → 2.18.2

Verified with: mvn package -DskipTests
============================================================
```

### Was wird aktualisiert?

| Element | Bedingung |
| --- | --- |
| `<parent>` | Immer, wenn Version explizit angegeben |
| `<dependency>` | Nur bei expliziter Version (kein `${...}`-Platzhalter) |
| `<plugin>` | Nur bei expliziter Version (kein `${...}`-Platzhalter) |

Versions-Platzhalter wie `${spring.version}` werden nicht angefasst –
diese müssen manuell in `<properties>` gepflegt werden.

---

## 9. find_big_files_in_git_history.sh – Große Dateien in Git-History finden

Durchsucht alle Git-Repositories im aktuellen Verzeichnis nach Dateien, die
in der Git-History größer als **50 KB** sind – auch wenn sie inzwischen gelöscht wurden.
Nützlich vor dem Spiegeln oder Aufräumen eines Repos.

Im übergeordneten Verzeichnis ausführen, das die Git-Repos enthält:

```bash
cd ~/git
bash find_big_files_in_git_history.sh
```

```text
===== Prüfe Git-Repo: my-app/ =====
blob a1b2c3d4  102400 src/main/resources/large-fixture.json
blob e5f6a7b8   75320 old-binary.jar

===== Prüfe Git-Repo: raspberrypi/ =====

Überspringe not-a-repo/ (kein Git-Repo)
```

### Große Dateien aus der History entfernen

Nach dem Identifizieren unerwünschter großer Dateien:

```bash
# Mit git-filter-repo (empfohlen, muss installiert werden)
pip install git-filter-repo
git filter-repo --path path/to/large-file.jar --invert-paths

# Danach force-push (nur nach Abstimmung mit dem Team!)
git push origin --force --all
```

> **Warnung:** Das Umschreiben der Git-History ändert alle Commit-Hashes.
> Nur in Repos ohne aktive Zusammenarbeit oder nach Abstimmung mit dem Team durchführen.

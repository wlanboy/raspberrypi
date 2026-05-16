# Git & Maven Toolsammlung

Diese Sammlung enthält Python- und Shell-Scripte für den täglichen Umgang mit mehreren
Git-Repositories sowie für die automatische Pflege von Maven- und Python-Abhängigkeiten,
Docker-Images und GitHub Actions.

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
9. [update-pom-all.py – Maven-Abhängigkeiten in allen Projekten](#9-update-pom-allpy--maven-abhängigkeiten-in-allen-projekten)
10. [update-uv.py – Python-Abhängigkeiten aktualisieren](#10-update-uvpy--python-abhängigkeiten-aktualisieren)
11. [update-uv-all.py – Python-Abhängigkeiten in allen Projekten](#11-update-uv-allpy--python-abhängigkeiten-in-allen-projekten)
12. [git_github_action_status.py – GitHub Actions Status](#12-git_github_action_statuspy--github-actions-status)
13. [git_github_action_update.py – GitHub Actions aktualisieren](#13-git_github_action_updatepy--github-actions-aktualisieren)
14. [docker-image-status.py – Docker-Image-Status prüfen](#14-docker-image-statuspy--docker-image-status-prüfen)
15. [docker-image-update.py – Docker-Images aktualisieren](#15-docker-image-updatepy--docker-images-aktualisieren)
16. [update-stack.py – Docker Compose Stacks verwalten](#16-update-stackpy--docker-compose-stacks-verwalten)
17. [git_zizmor.py – GitHub Actions Security-Audit](#17-git_zizmory--github-actions-security-audit)
18. [local_push.py – Lokale Repos nach Gitea pushen](#18-local_pushpy--lokale-repos-nach-gitea-pushen)
19. [gitea-update-github-token.py – GitHub-Token in Mirrors aktualisieren](#19-gitea-update-github-tokenpyGitHub-token-in-mirrors-aktualisieren)
20. [git_clone.py – Alle GitHub-Repos klonen](#20-git_clonepy--alle-github-repos-klonen)
21. [check_and_add_license.sh – Lizenz zu Repos hinzufügen](#21-check_and_add_licensesh--lizenz-zu-repos-hinzufügen)
22. [find_big_files_in_git_history.sh – Große Dateien in Git-History finden](#22-find_big_files_in_git_historysh--große-dateien-in-git-history-finden)

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
| `gitstatus` | `git_status_all.py ~/git` | **S**tatus aller Repos anzeigen |
| `gitscan` | `scan_git_repos.py ~/git` | Repos **l**isten (Branch + Remote) |
| `gm` | `mirror_git_repos.py ~/git` | GitHub → Gitea **m**irroren |
| `gitnom` | `gh-no-mirror.py` | Repos ohne Mirror-Tag anzeigen |
| `up` | `update-pom.py` | Maven-Abhängigkeiten **up**daten |
| `lp` | `local_push.py` | Lokale Repos nach Gitea **p**ushen |
| `hh` | `python3 -m http.server` | Einfachen **H**TTP-Server starten |
| `dockerstatus` | `docker-image-status.py` | Docker-Image-Status prüfen |
| `dockerupdate` | `docker-image-update.py` | Docker-Images aktualisieren |
| `updatestack` | `update-stack.py` | Docker Compose Stacks updaten |
| `aa` | `alias` | Alle aktiven **A**liases anzeigen |
| `giteaupdate` | `gitea-update-github-token.py` | GitHub-Token in Gitea-Mirrors erneuern |
| `uu` | `uv lock --upgrade && uv pip compile ...` | Python-Abhängigkeiten updaten |
| `gz` | `git_zizmor.py ~/git` | GitHub Actions Security-Audit (zizmor) |
| `gha` | `git_github_action_update.py ~/git` | **G**itHub **A**ctions aktualisieren |
| `ghas` | `git_github_action_status.py ~/git` | **G**itHub **A**ctions **S**tatus anzeigen |

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
| [`update-pom-all.py`](update-pom-all.py) | Python | `update-pom.py` für alle Java-Projekte in einem Verzeichnis |
| [`update-uv.py`](update-uv.py) | Python | `uv.lock` eines Python-Projekts aktualisieren und validieren |
| [`update-uv-all.py`](update-uv-all.py) | Python | `update-uv.py` für alle Python-Projekte in einem Verzeichnis |
| [`git_github_action_status.py`](git_github_action_status.py) | Python | Letzten GitHub Actions Run je Pipeline für alle Repos anzeigen |
| [`git_github_action_update.py`](git_github_action_update.py) | Python | Veraltete GitHub Actions auf neue Major-Versionen aktualisieren |
| [`docker-image-status.py`](docker-image-status.py) | Python | Laufende Container auf neuere Image-Versionen prüfen |
| [`docker-image-update.py`](docker-image-update.py) | Python | Veraltete Docker-Images pullen (liest `docker-image.status`) |
| [`update-stack.py`](update-stack.py) | Python | Docker Compose Stacks interaktiv auswählen, pullen und neu starten |
| [`git_zizmor.py`](git_zizmor.py) | Python | GitHub Actions Workflows mit zizmor auf Sicherheitsprobleme prüfen |
| [`local_push.py`](local_push.py) | Python | Lokale Git-Repos in Gitea-Organisation pushen |
| [`gitea-update-github-token.py`](gitea-update-github-token.py) | Python | GitHub-Token in allen Gitea-Mirror-Repos aktualisieren |
| [`git_clone.py`](git_clone.py) | Python | Alle eigenen GitHub-Repos nach `~/github/public` und `~/github/private` klonen |
| [`check_and_add_license.sh`](check_and_add_license.sh) | Bash | Apache-2.0-Lizenz zu öffentlichen Repos ohne Lizenz hinzufügen |
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
gitstatus
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
gitscan
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
gitnom
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

## 9. update-pom-all.py – Maven-Abhängigkeiten in allen Projekten

Durchsucht ein Verzeichnis rekursiv nach `pom.xml`-Dateien und ruft
[`update-pom.py`](#8-update-pompy--maven-abhängigkeiten-aktualisieren) für jedes
gefundene Java-Projekt auf. Am Ende wird eine Zusammenfassung ausgegeben und
optional ein `git push` für alle Projekte mit nicht gepushten Commits angeboten.

```bash
python3 update-pom-all.py [VERZEICHNIS]
```

Ohne Argument wird das aktuelle Verzeichnis verwendet.

```text
🔍 3 Java-Projekt(e) gefunden in /home/samuel/git

==============================
📦 /home/samuel/git/my-app
==============================
...

📊 Zusammenfassung (3 Projekt(e))

✔ Erfolgreich (2):
   /home/samuel/git/my-app
   /home/samuel/git/other-app

❌ Fehlgeschlagen (1):
   /home/samuel/git/broken-app

🚀 git push ausstehend (2 Projekt(e)):
   /home/samuel/git/my-app
   /home/samuel/git/other-app

❓ git push für alle ausstehenden Projekte ausführen? [j/N]:
```

---

## 10. update-uv.py – Python-Abhängigkeiten aktualisieren

Aktualisiert `uv.lock` eines Python-Projekts auf die neuesten verfügbaren Versionen
(`uv lock --upgrade`), prüft anschließend mit `uv sync` und führt optionale Checks
mit `ruff` und `pyright` aus (falls im Projekt vorhanden). Bei Fehlschlag wird das
Original-`uv.lock` automatisch wiederhergestellt.

Voraussetzungen: `uv` im PATH, `pyproject.toml` und `uv.lock` im Projektverzeichnis.

```bash
python3 update-uv.py [VERZEICHNIS]
```

Ohne Argument wird das aktuelle Verzeichnis verwendet.

### Ausführungsschritte

1. Backup von `uv.lock` erstellen (`uv.lock.bak`)
2. `uv lock --upgrade` ausführen
3. Versionsunterschiede ermitteln
4. `uv sync` zur Validierung ausführen
5. `ruff check` und `pyright` ausführen (wenn vorhanden)
6. Bei **Erfolg**: Backup löschen, Git-Commit erstellen, Commit-Message ausgeben
7. Bei **Fehler**: `uv.lock.bak` wiederherstellen

```text
Backup erstellt: uv.lock.bak

Starte uv lock --upgrade ...

Prüfe mit uv sync ...
Sync erfolgreich.

============================================================
COMMIT MESSAGE
============================================================
uv updater: bump dependencies to latest releases

- requests: 2.31.0 → 2.32.3
- ruff: 0.4.0 → 0.5.7
============================================================
```

---

## 11. update-uv-all.py – Python-Abhängigkeiten in allen Projekten

Durchsucht ein Verzeichnis rekursiv nach Projekten, die sowohl eine `pyproject.toml`
als auch eine `uv.lock` besitzen, und ruft
[`update-uv.py`](#10-update-uvpy--python-abhängigkeiten-aktualisieren) für jedes auf.
Am Ende wird eine Zusammenfassung ausgegeben und optional ein `git push` angeboten.

```bash
python3 update-uv-all.py [VERZEICHNIS]
```

```text
🔍 2 Python-Projekt(e) gefunden in /home/samuel/git

==================================================
🐍 /home/samuel/git/my-tool
==================================================
...

📊 Zusammenfassung (2 Projekt(e))

✔ Erfolgreich (2):
   /home/samuel/git/my-tool
   /home/samuel/git/other-tool

🚀 git push ausstehend (1 Projekt(e)):
   /home/samuel/git/my-tool

❓ git push für alle ausstehenden Projekte ausführen? [j/N]:
```

---

## 12. git_github_action_status.py – GitHub Actions Status

Zeigt für alle Git-Repositories im angegebenen Verzeichnis den Status des letzten
GitHub Actions Runs je Workflow. Verwendet die `gh` CLI für die API-Abfragen.

Voraussetzung: GitHub CLI installiert und eingeloggt mit `gh auth login`.

```bash
python3 git_github_action_status.py [VERZEICHNIS]
# oder per Alias:
ghas
```

```text
🔍 3 Repository/ies gefunden

📂 my-app
  Status          Workflow                                  Branch               Event               Alter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ success      Build and Deploy                          main                 push                2d ago
  ❌ failure      Code Quality                              feature/xyz          pull_request        5h ago

📂 other-repo
  — Keine Runs gefunden
```

### Status-Symbole

| Symbol | Bedeutung |
| --- | --- |
| ✅ | Erfolgreich (success) |
| ❌ | Fehlgeschlagen (failure) |
| ⚠️ | Abgebrochen (cancelled) |
| 🔄 | Läuft gerade (in_progress) |
| ⏳ | Wartend (queued/waiting) |

Mit `--no-color` wird die farbige Ausgabe deaktiviert.

---

## 13. git_github_action_update.py – GitHub Actions aktualisieren

Durchsucht alle `.github/workflows`-Verzeichnisse im angegebenen Basisverzeichnis
nach veralteten GitHub Actions (nur **Major-Version-Sprünge**) und aktualisiert die
Workflow-Dateien interaktiv. Optional werden die Änderungen committed und gepusht.

Voraussetzung: GitHub CLI installiert (für Token-Authentifizierung).

```bash
python3 git_github_action_update.py [VERZEICHNIS]
# oder per Alias:
gha
```

```text
🔑 GitHub Token gefunden – Online-Checks aktiviert.

🔍 Suche nach Workflow-Dateien ...
✅ 5 Workflow-Datei(en), 8 eindeutige Action(s).

🌐 Prüfe aktuelle Versionen via GitHub API ...
   actions/checkout: v4
   actions/setup-java: v4
   ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Neue Major-Versionen verfügbar:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1] actions/upload-artifact
       v3 → v4
       my-app/.github/workflows/build.yml

Welche Actions aktualisieren? (Nummern kommasepariert, "a" = alle, "n" = keine): a

✅ my-app/.github/workflows/build.yml (actions/upload-artifact: v3 → v4)

Sollen die Änderungen committed und gepusht werden? [j/N]:
```

> **Hinweis:** Es werden ausschließlich Major-Versionswechsel angezeigt (z. B. v3 → v4).
> Patch- und Minor-Updates werden bewusst ignoriert.

---

## 14. docker-image-status.py – Docker-Image-Status prüfen

Vergleicht für alle laufenden Docker-Container den lokalen Image-Digest mit dem
aktuellen Remote-Digest auf Docker Hub, GHCR oder einer selbst gehosteten Registry.
Das Ergebnis wird in `docker-image.status` (JSON) gespeichert und dient als Eingabe
für [`docker-image-update.py`](#15-docker-image-updatepy--docker-images-aktualisieren).

```bash
python3 docker-image-status.py [--json]
# oder per Alias:
dockerstatus
```

```text
CONTAINER        IMAGE                STATUS
-----------------------------------------------
nginx            nginx:latest         UP TO DATE
my-app           myrepo/app:v2.1      UPDATE AVAILABLE
custom-service   ghcr.io/org/svc:1    UNKNOWN  (digest not available)

Status written to: /path/to/tools/docker-image.status
```

Mit `--json` wird die Ausgabe als JSON statt als Tabelle ausgegeben.

### Unterstützte Registries

| Registry | Authentifizierung |
| --- | --- |
| Docker Hub (`docker.io`) | Anonym via Token-Challenge |
| GitHub Container Registry (`ghcr.io`) | Anonym via Bearer-Challenge |
| Selbst gehostete OCI-Registry | Anonym, falls ohne Auth |

---

## 15. docker-image-update.py – Docker-Images aktualisieren

Liest die von [`docker-image-status.py`](#14-docker-image-statuspy--docker-image-status-prüfen)
erstellte Statusdatei und führt für alle veralteten Container `docker pull` aus.

```bash
python3 docker-image-update.py [--dry-run]
# oder per Alias:
dockerupdate
```

Die Statusdatei darf nicht älter als 1 Stunde sein; andernfalls wird eine Warnung ausgegeben.

```text
Status from: 2025-05-16T10:00:00+00:00

Containers up to date : 2
Containers to update  : 1
Containers unknown    : 1

Updating my-app (myrepo/app:v2.1)
  Pulling image ...
  $ docker pull myrepo/app:v2.1
  Done
```

Mit `--dry-run` werden die Befehle nur angezeigt, aber nicht ausgeführt.

---

## 16. update-stack.py – Docker Compose Stacks verwalten

Interaktives TUI-Tool zum Verwalten von Docker Compose Stacks unter `/mnt/sata`.
Zeigt alle verfügbaren `docker-compose*.yml`-Dateien in einer Auswahlliste.
Die Auswahl wird in `~/.update-stack-selection` gespeichert und beim nächsten Aufruf
automatisch geladen.

```bash
python3 update-stack.py [-s]
# oder per Alias:
updatestack        # lädt gespeicherte Auswahl und führt pull + up -d aus
updatestack -s     # öffnet TUI zur Neuauswahl
```

### Modi

| Aufruf | Verhalten |
| --- | --- |
| `updatestack` | Lädt gespeicherte Auswahl → `docker compose pull` → fragt nach `up -d` |
| `updatestack -s` | Öffnet TUI → Auswahl speichern → optional sofort ausführen |

### TUI-Steuerung

| Taste | Funktion |
| --- | --- |
| `↑` / `↓` | Cursor bewegen |
| `Leertaste` | Stack ein-/abwählen |
| `A` | Alle auswählen |
| `N` | Keine auswählen |
| `Enter` | Auswahl bestätigen und speichern |
| `Q` / `Esc` | Abbrechen |

---

## 17. git_zizmor.py – GitHub Actions Security-Audit

Führt das Tool [zizmor](https://github.com/woodruffw/zizmor) via `uvx` in allen
Git-Repositories mit GitHub Actions Workflows aus, um Sicherheitsprobleme zu finden.

Voraussetzung: `uv` im PATH (zizmor wird automatisch via `uvx` heruntergeladen).

```bash
python3 git_zizmor.py [VERZEICHNIS] [--gh-token TOKEN] [--format sarif|json] [-b]
# oder per Alias:
gz
```

```text
⏭️  my-plain-repo hat keine GitHub Actions Workflows – wird übersprungen

🔍 Prüfe Workflows in my-app ...
...
⚠️  my-app: Probleme gefunden (siehe oben)

🔍 Prüfe Workflows in secure-repo ...
✅ secure-repo: keine Probleme gefunden
```

### Optionen

| Option | Bedeutung |
| --- | --- |
| `--gh-token TOKEN` | GitHub Token für erweiterte Online-Checks (Impostor-Commits, CVEs) |
| `--format sarif\|json` | Maschinenlesbares Ausgabeformat (Standard: menschenlesbar) |
| `-b` | Unterdrückt "required by blanket policy"-Findings (`--persona=regular`) |

---

## 18. local_push.py – Lokale Repos nach Gitea pushen

Durchsucht ein lokales Verzeichnis nach Git-Repositories und pusht jedes in die
Gitea-Organisation `local`. Repos, die bereits in `local` oder `github` vorhanden
sind, werden übersprungen.

### Umgebungsvariablen

```bash
export GITEA_TOKEN="dein-gitea-api-token"
```

```bash
python3 local_push.py [VERZEICHNIS]
# oder per Alias:
lp
```

Ohne Argument wird `/mnt/z/github` als Quellverzeichnis verwendet.

```text
🚀 Lokale Repos aus /mnt/z/github nach Gitea (local) pushen...

⏭ Überspringe existing-repo (existiert bereits in local)
➕ new-project
  ✔ Gepusht

📊 Fertig: 1 gepusht, 1 übersprungen, 0 Fehler
```

> **Hinweis:** Verwendet `GIT_SSL_NO_VERIFY=true` und `ssl._create_unverified_context()`,
> da die Gitea-Instanz ein selbstsigniertes Zertifikat nutzt.

---

## 19. gitea-update-github-token.py – GitHub-Token in Mirrors aktualisieren

Aktualisiert den GitHub-Token in allen Mirror-Repos der Gitea-Organisation `github`.
Da die Gitea-API keinen direkten Token-Update unterstützt, wird jeder Mirror gelöscht
und mit dem neuen Token neu erstellt.

### Umgebungsvariablen

```bash
export GITHUB_USERNAME="dein-github-username"
export GITHUB_GITEA_TOKEN="ghp_neuer-token"
export GITEA_TOKEN="dein-gitea-api-token"
```

```bash
python3 gitea-update-github-token.py
# oder per Alias:
giteaupdate
```

```text
🔑 GitHub-Token-Update für Gitea-Mirrors...
📋 42 Mirror-Repos in Org 'github' gefunden

❓ Token für alle 42 Repos aktualisieren? (ja/[nein]): ja

🔄 my-app... ✔
🔄 other-repo... ✔
🔄 broken-repo... ❌ Neu erstellen fehlgeschlagen: ...

📊 Zusammenfassung:
   Aktualisiert:   41
   Fehlgeschlagen: 1
```

> **Warnung:** Der Vorgang löscht und erstellt Mirror-Repos neu. Kurzzeitige
> Sync-Unterbrechungen sind möglich.

---

## 20. git_clone.py – Alle GitHub-Repos klonen

Lädt über die `gh` CLI die Liste aller eigenen GitHub-Repositories und klont
jedes in `~/github/public` (öffentliche Repos) oder `~/github/private` (private Repos).
Bereits vorhandene Verzeichnisse werden übersprungen.

Voraussetzung: GitHub CLI installiert und eingeloggt mit `gh auth login`.

```bash
python3 git_clone.py
```

```text
🔍 Lade Repository-Liste via gh CLI...
   87 Repos gefunden

📥 Klone my-app → /home/samuel/github/public/my-app
⏭️  raspberrypi existiert bereits – wird übersprungen
📥 Klone secret-project → /home/samuel/github/private/secret-project

📊 Zusammenfassung:
   Geklont:       12
   Übersprungen:  74
   Fehler:        1

📁 Zielordner:
   Public:  /home/samuel/github/public
   Private: /home/samuel/github/private
```

---

## 21. check_and_add_license.sh – Lizenz zu Repos hinzufügen

Prüft alle öffentlichen, nicht archivierten GitHub-Repositories auf fehlende Lizenzen
und fügt automatisch eine Apache-2.0-Lizenz hinzu. Der Lizenztext wird direkt von der
GitHub API geladen.

Voraussetzungen: GitHub CLI (`gh`), `curl`, `jq`.

```bash
bash check_and_add_license.sh [--dry-run]
```

Mit `--dry-run` werden Commits erstellt, aber nicht gepusht.

```text
Lade Apache-2.0 Lizenztext...
Rufe Repositories ohne Lizenz ab...
-----------------------------------------------
Bearbeite: wlanboy/old-project
  Lizenz erfolgreich hinzugefügt.
-----------------------------------------------
Bearbeite: wlanboy/another-repo
  Lizenz erfolgreich hinzugefügt.
-----------------------------------------------
Fertig.
```

> **Hinweis:** Repos, die bereits eine `LICENSE`-, `LICENSE.txt`- oder
> `LICENSE.md`-Datei enthalten, werden auch dann übersprungen, wenn die GitHub API
> keine Lizenz meldet.

---

## 22. find_big_files_in_git_history.sh – Große Dateien in Git-History finden

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

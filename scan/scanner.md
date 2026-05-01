# Scanner-Übersicht

Dieses Verzeichnis enthält drei spezialisierte Security-Scanner sowie eine Whitelist-Konfiguration. Alle Scanner sind als eigenständige Python-Skripte ausgeführt werden und liefern strukturierte Berichte (Text oder JSON).

---

## 1. `scan-external-urls.py` — Externe Referenz-Scanner

### Zweck

Scannt ein komplettes Git-Repository nach externen Referenzen, die in Produktions- oder Testcode nichts verloren haben: URLs, E-Mail-Adressen, Hostnamen und IP-Adressen. Das Ziel ist es, unbeabsichtigte Datenabflüsse, hartcodierte Endpunkte und versehentlich commitete persönliche Daten zu finden.

### Einsatzgebiet

- **CI/CD-Pipelines**: Vor jedem Merge prüfen, ob neue externe Abhängigkeiten eingebracht wurden.
- **Code-Reviews**: Schnell einen Überblick verschaffen, welche Domains und IPs ein Repository kennt.
- **Compliance-Audits**: Sicherstellen, dass keine personenbezogenen Daten (E-Mails) im Code liegen.
- **Infrastructure-as-Code-Repos**: Ansible, Terraform, Kubernetes-Manifeste auf unerwünschte externe Endpunkte prüfen.

### Erkannte Kategorien

| Kategorie | Beschreibung | Beispiel |
|-----------|-------------|---------|
| `url` | HTTP/HTTPS-URLs | `https://api.example.com/v2/data` |
| `email` | E-Mail-Adressen | `admin@company.com` |
| `hostname` | Vollqualifizierte Hostnamen mit bekannten TLDs | `internal.corp.io` |
| `ip` | IPv4-Adressen | `10.0.5.12` |

### Besonderheiten

- Nutzt `git ls-files` — prüft nur versionskontrollierte Dateien, respektiert `.gitignore`.
- Binäre Dateien (Null-Byte-Erkennung) und bekannte Binär-Extensions (`.png`, `.jar`, `.lock` usw.) werden übersprungen.
- **Whitelist-System** (`whitelist.json`): IP-Ranges (CIDR), Hostnamen (mit Wildcard-Unterstützung `*.domain.com`) und E-Mail-Domains können dauerhaft erlaubt werden. Die Datei `whitelist.json` im selben Verzeichnis wird automatisch geladen.
- **TLD-Allowlist**: Hostnamen werden nur gemeldet, wenn ihre TLD in einer curated Liste bekannter TLDs steht. Dadurch werden Python-Methodenaufrufe (`os.path`, `subprocess.run`) oder Java-Paketnamen nicht fälschlicherweise als Hostnamen erkannt.
- Intelligente Ausschlusslogik: Import-Statements (`from textual.app import`), Kubernetes-API-Groups (`rbac.authorization.k8s.io/`), YAML-Listenelemente und Dateipfad-Komponenten werden nicht als Hostnamen gewertet.

### Konfigurationsoptionen

```bash
# Alle Kategorien, Textausgabe
python3 scan-external-urls.py /pfad/zum/repo

# Nur URLs und E-Mails, JSON-Ausgabe für CI
python3 scan-external-urls.py --categories url email --format json

# Testdateien überspringen, interne Domain erlauben
python3 scan-external-urls.py --skip-tests --allow "mycompany\\.com"

# Alle IP-Adressen ignorieren (z. B. Ansible/Infrastruktur-Repos)
python3 scan-external-urls.py --ignore-all-ips

# Externe Whitelist-Datei laden
python3 scan-external-urls.py --whitelist custom-whitelist.json
```

### Exit-Codes

| Code | Bedeutung |
|------|-----------|
| `0` | Keine Befunde (oder `--no-fail` gesetzt) |
| `1` | Befunde gefunden |
| `2` | Skriptfehler (kein Git-Repo, ungültige Argumente) |

---

## 2. `scan-npm.py` — NPM/JavaScript Supply-Chain-Scanner

### Zweck

Scannt Node.js-Projekte auf Indikatoren für bekannte JavaScript-Trojaner und Supply-Chain-Angriffe. Der Scanner erkennt sowohl Konfigurations-Level-Probleme (verdächtige `package.json`-Hooks) als auch Code-Level-Bedrohungen (Verschleierung, Exfiltration, Reverse Shells) direkt in JS/TS-Quelldateien.

### Einsatzgebiet

- **Abhängigkeits-Audits**: Vor dem Einbinden fremder npm-Pakete deren Code auf Schadsoftware prüfen.
- **Supply-Chain-Security**: Erkennen, ob ein Paket über einen Nicht-Standard-Registry-Mirror installiert wird.
- **Entwickler-Workstations**: Den lokalen npm-Cache auf kompromittierte Pakete untersuchen (`--scan-cache`).
- **Open-Source-Beiträge**: PRs von externen Kontributoren auf eingebrachte Backdoors prüfen.
- **Post-Incident-Forensik**: Nach einem Sicherheitsvorfall schnell alle JS-Dateien nach bekannten Angriffsvektoren durchsuchen.

### Erkannte Bedrohungskategorien

#### `LIFECYCLE_HOOKS_FOUND` (INFO)
Inventarisiert alle npm-Lifecycle-Hooks (`preinstall`, `install`, `postinstall`, `prepare`, `prepack`, `postpack`). Hooks werden bei `npm install` **automatisch ohne Benutzerbestätigung ausgeführt** — jeder Hook ist potenziell ein Angriffspunkt.

#### `INSTALL_SCRIPT` (HIGH/MEDIUM)
Prüft Lifecycle-Hooks auf gefährliche Muster:
- `curl`/`wget` — Download-Vektoren für Payloads
- `netcat`/`nc` — Reverse-Shell-Indikator
- `eval()` in Shell-Skripten
- `base64 --decode` — Verschleierung von Payloads
- `chmod` mit ausführbaren Bits
- `python3 -c` — Inline-Ausführung
- Zugriff auf `/etc/passwd`, `~/.ssh/`
- Krypto-Mining-Keywords (`stratum+tcp://`, `xmrig`)
- `node -e` / `node --eval` — Inline-JavaScript-Ausführung (MEDIUM)
- `process.env` + HTTP-Aufruf im selben Skript (HIGH)
- **`binding.gyp`**: Bloße Existenz löst einen MEDIUM-Befund aus, da npm automatisch `node-gyp rebuild` beim Install triggert — auch ohne Eintrag in `scripts`
- **`"gypfile": true`**: Ebenso ein versteckter Install-Hook

#### `OBFUSCATION` (HIGH/MEDIUM/LOW)
Erkennt JavaScript-Verschleierungstechniken:
- `eval(Buffer.from(..., 'base64'))` — klassisches Payload-Delivery-Muster (HIGH)
- Lange Hex-/Base64-Strings via `Buffer.from` (HIGH)
- `String.fromCharCode(115, 101, ...)` mit vielen Argumenten (HIGH)
- `_0x`-Variablennamen (Ausgabe von JS-Obfuskatoren) (MEDIUM)
- Bracket-Notation mit String-Konkatenation: `obj["ex"+"ec"]` (HIGH)
- `require("child_"+"process")` — verschleierter Modulname (HIGH)
- `unescape()` mit prozentkodierten Sequenzen (LOW)
- Zweistufiges Muster: `var cp = 'child_'+'process'; require(cp)` (HIGH)
- Minifizierte Zeilen > 1000 Zeichen (LOWe, statische Analyse eingeschränkt)

#### `EXFILTRATION` (HIGH/MEDIUM)
Kombinationen, die auf Credential- oder Datendiebstahl hinweisen:
- `process.env` + HTTP-Aufruf auf einer Zeile (HIGH)
- Sensitive Umgebungsvariablen (`GITHUB_TOKEN`, `AWS_SECRET`, `NPM_TOKEN`) neben Netzwerkaufrufen (HIGH)
- `readFileSync` auf SSH-Schlüssel-, AWS-, `.npmrc`-Pfaden (HIGH)
- `os.homedir()` + `.ssh`/`.aws` (MEDIUM)
- `require('keytar')` — OS-Schlüsselbund-Zugriff (MEDIUM)
- Hardcodierte `_authToken` in `.npmrc`, `.yarnrc`, `.yarnrc.yml` (MEDIUM)
- `process.env` in Datei mit Netzwerkfunktionen (MEDIUM, kontextsensitiv)

#### `FILESYSTEM_ATTACK` (HIGH/MEDIUM)
Schreiben in kritische Systemdateien:
- `/etc/passwd`, `/etc/shadow`, `/etc/cron.*` (HIGH)
- `~/.ssh/authorized_keys` — SSH-Backdoor (HIGH)
- `~/.bashrc`, `~/.profile`, `~/.zshrc` — Persistenzmechanismus (MEDIUM)
- Cron-Verzeichnisse (MEDIUM)

#### `REMOTE_EXEC` (HIGH/MEDIUM)
Dynamische Code- und Befehlsausführung:
- `require('child_process').exec/spawn` (HIGH)
- `new Function()` mit Netzwerk-/Dekodierungsinhalt (HIGH)
- TCP-Socket an stdio weitergeleitet — Reverse Shell (HIGH)
- `/bin/sh -i` + Socket/Connect (HIGH)
- `vm.runInNewContext()` / `vm.runInThisContext()` (MEDIUM)
- Remote-Code-Fetch + eval (MEDIUM)

#### `CRYPTOMINING` (HIGH/MEDIUM)
- `stratum+tcp://` — Mining-Protokoll (HIGH)
- Bekannte Miner-Binärnamen: `xmrig`, `xmr-stak`, `cpuminer` (HIGH)
- Bekannte Mining-Dienst-Domains: `coinhive.com`, `cryptoloot.pro` (HIGH)
- Mining-Algorithmusnamen + Mining-Keywords (MEDIUM)

#### `SUPPLY_CHAIN` (HIGH/MEDIUM)
- `Module._compile()` mit verschlüsseltem Buffer — Event-Stream-Angriffsmuster (HIGH)
- `require.extensions[]` / `Module._extensions[]` — require-Hook-Injektion (HIGH)
- Yarn-Plugins von externen URLs (HIGH)
- Git-URL-Abhängigkeiten in `package.json` (MEDIUM)
- Nicht-Standard-Registry in `.npmrc`, `.yarnrc`, `.yarnrc.yml` (MEDIUM)
- Nicht-Standard-resolved-URLs in `package-lock.json` (MEDIUM)
- Native `.node`-Addons (MEDIUM, nicht statisch analysierbar)
- `npm_lifecycle_event` + Netzwerkaufruf (MEDIUM)

### npm-Cache-Scan

Mit `--scan-cache` wird zusätzlich der lokale npm-Cache (`~/.npm/_cacache/content-v2/`) gescannt. Jeder Blob im Cache ist ein gzip-komprimierter Tarball eines installierten Pakets — der Scanner entpackt diese on-the-fly und wendet alle Prüfungen an, ohne den Cache zu verändern.

### Konfigurationsoptionen

```bash
# Aktuelles Repo scannen
python3 scan-npm.py

# Nur HIGH-Befunde, node_modules einschließen
python3 scan-npm.py --min-severity HIGH --include-modules

# npm-Cache ebenfalls scannen
python3 scan-npm.py --scan-cache

# JSON-Ausgabe für CI-Integration
python3 scan-npm.py --format json --no-fail
```

### Exit-Codes

| Code | Bedeutung |
|------|-----------|
| `0` | Keine Befunde (oder `--no-fail` gesetzt) |
| `1` | Befunde gefunden |
| `2` | Skriptfehler |

---

## 3. `scan-proxy.py` — Proxy-Konfiguration-Scanner

### Zweck

Inventarisiert alle Proxy-Einstellungen auf einem System. Der Scanner liest Umgebungsvariablen, Shell-Konfigurationsdateien, Paketmanager-Konfigurationen (yum, dnf, wget, curl), Maven-Settings und Ansible-Konfigurationen aus und erstellt eine konsolidierte Übersicht.

### Einsatzgebiet

- **Netzwerk-Debugging**: Verstehen, warum ein Tool den falschen Proxy nutzt oder gar keinen.
- **Onboarding**: Schnell herausfinden, welche Proxy-Einstellungen auf einem neuen System oder in einem Container aktiv sind.
- **CI/CD-Runner**: Sicherstellen, dass Build-Agenten die richtigen Proxy-Einstellungen haben.
- **Compliance**: Nachweisen, dass kein unerlaubter Proxy für ausgehende Verbindungen konfiguriert ist.
- **Infrastruktur-Audits**: Überblick über alle Proxy-Konfigurationen auf einem Server verschaffen.

### Gescannte Quellen

| Quelle | Dateien / Variablen |
|--------|---------------------|
| **Umgebungsvariablen** | `http_proxy`, `https_proxy`, `ftp_proxy`, `no_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` |
| **System-Shell** | `/etc/environment`, `/etc/profile`, `/etc/bashrc`, `/etc/bash.bashrc`, `/etc/profile.d/*.sh` |
| **Benutzer-Shell** | `~/.bashrc`, `~/.bash_profile`, `~/.profile` |
| **yum/dnf** | `/etc/yum.conf`, `/etc/dnf/dnf.conf` (inkl. `proxy_username`, `proxy_password`) |
| **wget** | `/etc/wgetrc`, `~/.wgetrc` |
| **curl** | `/etc/curlrc`, `~/.curlrc` |
| **systemd-Umgebung** | `/etc/environment.d/*.conf` |
| **Maven** | `~/.m2/settings.xml`, `/etc/maven/settings.xml`, `$MAVEN_HOME/conf/settings.xml` — liest `<proxies>`-Block inkl. Host, Port, Protokoll, aktiv-Status, nonProxyHosts |
| **Ansible** | `/etc/ansible/ansible.cfg`, `~/.ansible.cfg`, `./ansible.cfg` |

### Ausgabeformat

```
=== PROXY SCAN REPORT: mein-hostname ===
RESULT: PROXY_FOUND
SOURCE=ENV KEY=http_proxy VALUE=http://proxy.corp.example.com:8080
SOURCE=/etc/environment KEY=HTTPS_PROXY VALUE=http://proxy.corp.example.com:8080
SOURCE=/home/user/.m2/settings.xml KEY=proxy.host VALUE=proxy.corp.example.com
SOURCE=/home/user/.m2/settings.xml KEY=proxy.port VALUE=8080
```

Wenn keine Proxy-Konfiguration gefunden wird:
```
=== PROXY SCAN REPORT: mein-hostname ===
RESULT: NO_PROXY_FOUND
```

### Konfigurationsoptionen

Der Scanner hat keine Kommandozeilenargumente — er läuft direkt und gibt das Ergebnis auf stdout aus. Geeignet für den Einbau in Shell-Skripte:

```bash
python3 scan-proxy.py | grep "RESULT:"
```

---

## 4. `whitelist.json` — Gemeinsame Whitelist

Zentrale Konfigurationsdatei für den External-URL-Scanner. Wird automatisch geladen, wenn sie sich im selben Verzeichnis wie `scan-external-urls.py` befindet.

### Struktur

```json
{
  "ip_ranges":     ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
  "hostnames":     ["localhost", "github.com", "download.docker.com"],
  "email_domains": ["example.com"],
  "urls":          ["http://10.100.0.100"]
}
```

| Feld | Wirkung |
|------|---------|
| `ip_ranges` | CIDR-Ranges — alle IP-Adressen in diesen Netzen werden nicht gemeldet |
| `hostnames` | Exakte Hostnamen oder Wildcard-Basis (`*.domain.com`). Betrifft auch den Host-Teil von URLs. |
| `email_domains` | Domain-Teile von E-Mail-Adressen, die ignoriert werden sollen |
| `urls` | Vollständige URL-Präfixe, die erlaubt sind |

Die aktuell konfigurierte Whitelist enthält private IP-Ranges (RFC 1918), Loopback, Standard-Infrastruktur-Hosts (GitHub, Docker, Helm, k3s usw.) und projektspezifische lokale Adressen.

---

## 5. `test_scan_npm.py` — Unit-Tests für den NPM-Scanner

Vollständige pytest/unittest-Test-Suite für `scan-npm.py` mit 10 Testklassen und über 40 Testmethoden.

### Ausführung

```bash
python3 -m pytest test_scan_npm.py -v
# oder
python3 -m unittest test_scan_npm -v
```

### Abgedeckte Testklassen

| Klasse | Abgedeckter Scanner |
|--------|---------------------|
| `TestScanPackageJson` | `_scan_package_json_lines()` — Lifecycle-Hooks, Gefahrenmuster, Git-URLs, gypfile |
| `TestScanNpmrc` | `_scan_npmrc_lines()` — Registry-Umleitungen, hardcodierte Tokens |
| `TestScanYarnrc` | `_scan_yarnrc_lines()` — Yarn v1 Registry und Token |
| `TestScanYarnrcYml` | `_scan_yarnrc_yml_lines()` — Yarn v2/v3, Plugin-URLs |
| `TestScanPackageLock` | `_scan_package_lock_lines()` — v1 und v2 Lock-Format, Non-Standard-Resolved-URLs |
| `TestScanBindingGyp` | `_scan_binding_gyp_lines()` — Existenz und verdächtige Aktionen |
| `TestScanJsLines` | `_scan_js_lines()` — alle 7 Bedrohungskategorien |
| `TestScanJsSplitVar` | `_scan_js_split_var()` — zweistufige Verschleierung |
| `TestScanJsCooccurrence` | `_scan_js_cooccurrence()` — kontextsensitive Erkennung |
| `TestCheckMinifiedLines` | `_check_minified_lines()` — Minimierungserkennung |

Jede Testmethode enthält einen Docstring, der erklärt: **was** geprüft wird, **welche Eingaben** verwendet werden und **warum** das Ergebnis so erwartet wird.

---

## Zusammenfassung: Welcher Scanner für welchen Zweck?

| Frage | Scanner |
|-------|---------|
| Hat dieses Repository externe URLs/IPs/E-Mails, die nicht dort sein sollten? | `scan-external-urls.py` |
| Enthält dieses npm-Paket oder JS-Projekt Schadsoftware oder Supply-Chain-Risiken? | `scan-npm.py` |
| Welche Proxy-Einstellungen sind auf diesem System aktiv? | `scan-proxy.py` |
| Welche Hosts und IPs sind für den URL-Scanner erlaubt? | `whitelist.json` |

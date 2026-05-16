# uv – Installation und sichere Konfiguration

## Warum Sicherheit beim Paketmanager wichtig ist

Python-Pakete werden von jedermann auf PyPI veröffentlicht. Angreifer nutzen das aus:

- **Typosquatting** – ein Paket heißt `reqeusts` statt `requests` und enthält Schadcode
- **Dependency Confusion** – ein internes Paket wird öffentlich auf PyPI hochgeladen mit höherer Versionsnummer, um es in CI-Pipelines einzuschleusen
- **Account-Übernahme** – der Account eines legitimen Paketautors wird kompromittiert, eine neue Version mit Backdoor veröffentlicht
- **Poisoned Updates** – ein verbreitetes Paket wird kurz nach Veröffentlichung nachträglich manipuliert

Das Zeitfenster, in dem Schadpakete aktiv sind, ist kurz: Die meisten werden innerhalb von Stunden bis Tagen entdeckt und entfernt. Wer jedoch sofort nach Veröffentlichung aktualisiert, ist genau in diesem Fenster exponiert.

Verteidigung bedeutet daher: **Zeit kaufen** (Cooldown), **exakt pinnen** (Hashes), **bekannte Lücken scannen** (Audit) und **Quellen kontrollieren** (Index-Konfiguration).

---

## Installation

### Empfohlene Methode (offizielle Installer-Skripte)

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Über pip (wenn Python bereits vorhanden):**
```bash
pip install uv
```

**Über pipx:**
```bash
pipx install uv
```

Nach der Installation prüfen:
```bash
uv --version
```

---

## Sicherheitsmaßnahmen – Schritt für Schritt

### 1. Dependency Cooldown mit `exclude-newer`

Das ist die wichtigste Einzelmaßnahme. Sie verhindert, dass Pakete installiert werden, die erst kürzlich auf PyPI hochgeladen wurden – also genau in dem Zeitfenster, in dem Schadpakete noch aktiv sind.

**Angriffszeitlinie (typisch):**
- T+0h: Schadpaket wird hochgeladen
- T+1–2h: Automatisierte Scanner beginnen
- T+4–6h: Community-Entdeckung
- T+6–8h: Paket wird entfernt, Warnungen werden veröffentlicht

Ein Cooldown von 7–14 Tagen schützt zuverlässig gegen dieses Fenster.

**Globale Konfiguration** (`~/.config/uv/uv.toml` auf Linux/macOS, `%APPDATA%\uv\uv.toml` auf Windows):
```toml
exclude-newer = "7 days"
```

**Projektspezifisch** (`pyproject.toml`):
```toml
[tool.uv]
exclude-newer = "7 days"
```

**Für Releases – fester Zeitstempel** (reproduzierbare Builds):
```toml
[tool.uv]
exclude-newer = "2026-01-15T00:00:00Z"
```

**Per-Paket-Ausnahmen** (für interne oder vertrauenswürdige Pakete):
```toml
[tool.uv]
exclude-newer = "7 days"

[tool.uv.exclude-newer-package]
my-internal-pkg = false        # keine Einschränkung
some-trusted-pkg = "2026-03-30"  # eigener Cutoff
```

**Auf der Kommandozeile:**
```bash
uv lock --exclude-newer "7 days"
uv sync --exclude-newer "7 days"
```

**Wichtig:** `uv lock --upgrade` umgeht `exclude-newer`-Beschränkungen. Diesen Befehl nur mit Bedacht und Begründung ausführen.

---

### 2. Lockfile immer committen

Ein Lockfile (`uv.lock`) fixiert exakte Versionen aller direkten und transitiven Abhängigkeiten. Ohne Lockfile ist `exclude-newer` allein unvollständig.

```bash
# Lockfile erstellen
uv lock

# Mit gesperrtem Lockfile synchronisieren (kein implizites Upgrade)
uv sync --locked

# Im CI verwenden
uv run --locked python main.py
```

`uv.lock` gehört in die Versionskontrolle – immer zusammen mit Konfigurationsänderungen committen.

---

### 3. Hash-Verifikation

`uv` speichert kryptografische Hashes im Lockfile standardmäßig. Das verhindert, dass ein Paket nach dem Pinnen nachträglich manipuliert werden kann.

```bash
# Lockfile mit Hashes generieren (Standard)
uv lock

# In requirements.txt mit Hashes exportieren (für Deployment)
uv export --format requirements-txt -o requirements.txt

# Mit pip-compile-kompatiblen Hashes
uv pip compile --generate-hashes requirements.in -o requirements.txt
```

Beispiel einer sicheren `requirements.txt`-Zeile:
```
flask==3.1.1 \
    --hash=sha256:abc123... \
    --hash=sha256:def456...
```

---

### 4. Index-Konfiguration und Dependency-Confusion-Schutz

uv verwendet standardmäßig eine **First-Match-Strategie**: Sobald ein Paket im ersten Index gefunden wird, wird nicht weitergesucht. Das schützt bereits gegen viele Dependency-Confusion-Angriffe.

Für interne Pakete zusätzlich explizit konfigurieren:

```toml
[[tool.uv.index]]
name = "internal"
url = "https://intern.example.com/pypi"
explicit = true

[tool.uv.sources]
my-internal-package = { index = "internal" }
```

`explicit = true` bedeutet: Dieses Paket wird *nur* von diesem Index bezogen, nie von PyPI.

---

### 5. Vulnerability-Scanning mit pip-audit

Bekannte CVEs in Abhängigkeiten aufspüren:

```bash
# Direkt über uvx (kein separates Install nötig)
uvx pip-audit --requirement requirements.txt

# Als JSON-Report
uvx pip-audit --format json --requirements requirements.txt > audit-report.json
```

**GitHub Actions Integration:**
```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uvx pip-audit --requirement requirements.txt
```

---

### 6. Regelmäßige Aktualisierungen

`exclude-newer` mit relativem Zeitfenster (z. B. `"7 days"`) verschiebt den Cutoff bei jedem `uv lock`-Aufruf automatisch. Empfohlener Rhythmus:

```bash
# Alle zwei Wochen ausführen, um den Cutoff voranzuschieben
uv lock
```

So bleiben Abhängigkeiten aktuell, ohne das Schutzfenster aufzugeben.

---

## Vollständige Referenzkonfiguration

**`~/.config/uv/uv.toml` (global, für alle Projekte):**
```toml
# Pakete, die jünger als 7 Tage sind, werden ignoriert
exclude-newer = "7 days"
```

**`pyproject.toml` (projektspezifisch):**
```toml
[tool.uv]
# Cooldown für dieses Projekt
exclude-newer = "7 days"

# Ausnahmen für interne oder vertrauenswürdige Pakete
[tool.uv.exclude-newer-package]
my-internal-pkg = false

# Interne Paketquellen
[[tool.uv.index]]
name = "internal"
url = "https://intern.example.com/pypi"
explicit = true

[tool.uv.sources]
my-internal-package = { index = "internal" }
```

---

### 7. Software Bill of Materials (SBOM) generieren

Ein SBOM ist ein maschinenlesbares Inventar aller Abhängigkeiten – direkt und transitiv. Es ermöglicht bei bekannt werdenden Sicherheitslücken sofort zu prüfen, ob das eigene Projekt betroffen ist.

```bash
# cyclonedx-bom über uvx ausführen (kein separates Install nötig)
uvx cyclonedx-py environment --output-file sbom.json

# Alternativ explizit installieren und ausführen
uv pip install cyclonedx-bom
cyclonedx-py environment --output-file sbom.json --format json
```

**GitHub Actions Integration:**
```yaml
- name: Generate SBOM
  run: uvx cyclonedx-py environment --output-file sbom.json

- name: Upload SBOM
  uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```

SBOMs sind besonders nützlich für:
- **Compliance-Nachweise** – bei internen Audits oder Kundenanforderungen
- **Schnelle Incident-Response** – wenn eine neue CVE bekannt wird, sofort prüfen ob betroffen
- **Vollständige Transparenz** – auch transitive Abhängigkeiten sind sichtbar

---

## Schnell-Checkliste

| Maßnahme | Wo | Befehl / Einstellung |
|---|---|---|
| Cooldown aktivieren | `~/.config/uv/uv.toml` | `exclude-newer = "7 days"` |
| Lockfile committen | Versionskontrolle | `uv lock && git add uv.lock` |
| Mit Lockfile deployen | CI / Produktion | `uv sync --locked` |
| Hashes exportieren | Deployment | `uv export --format requirements-txt` |
| Vulnerability-Scan | CI | `uvx pip-audit --requirement requirements.txt` |
| Interne Pakete pinnen | `pyproject.toml` | `explicit = true` + `sources` |
| SBOM generieren | CI / Release | `uvx cyclonedx-py environment --output-file sbom.json` |
| Alle 2 Wochen updaten | lokal / CI | `uv lock` |

---

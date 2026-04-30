#!/usr/bin/env python3
"""
scan-npm.py - Durchsucht ein Node.js-Projekt / Git-Repository nach Indikatoren
für bekannte JS/NPM-Trojaner, Supply-Chain-Angriffe und schädliche Code-Muster.

Durchgeführte Prüfungen:
  - Gefährliche Lifecycle-Hooks (postinstall/preinstall)
  - Code-Verschleierungstechniken (Hex/Base64-eval, _0x-Muster)
  - Exfiltration von Umgebungsvariablen
  - Krypto-Mining-Indikatoren
  - Dateisystem-Angriffe (Schreiben in ~/.ssh, /etc/passwd usw.)
  - Verdächtige Registry- / .npmrc-Konfiguration
  - Yarn-Konfiguration (.yarnrc, .yarnrc.yml)
  - package-lock.json aufgelöste URLs
  - Abhängigkeiten mit Git-URLs / Nicht-Registry-Quellen
  - npm-Cache (optional via --scan-cache)

Exit-Codes:
  0 - Keine Befunde (oder --no-fail gesetzt)
  1 - Befunde erkannt
  2 - Skriptfehler
"""

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Suspicious patterns in package.json lifecycle scripts
# ---------------------------------------------------------------------------

LIFECYCLE_HOOKS = frozenset({
    "preinstall", "install", "postinstall",
    "prepare", "prepack", "postpack",
})

INSTALL_SCRIPT_RULES: list[tuple[str, str]] = [
    # (regex, Beschreibung)
    (r'\bcurl\b',                         "curl im Install-Skript — häufiger Exfiltrations-/Download-Vektor"),
    (r'\bwget\b',                         "wget im Install-Skript"),
    (r'\bnc\b|\bncat\b|\bnetcat\b',       "netcat im Install-Skript — Hinweis auf Reverse-Shell"),
    (r'\bbase64\b.*\bdecode\b|\bdecode\b.*\bbase64\b',
                                          "base64-Dekodierung im Install-Skript — verschleierter Payload"),
    (r'eval\s*\(',                        "eval() im Install-Skript"),
    (r'python[23]?\s+-c\b',              "Inline-Python-Ausführung im Install-Skript"),
    (r'\bchmod\s+[0-9]*[67][0-9]*\s',    "chmod setzt ausführbare Bits im Install-Skript"),
    (r'/etc/passwd|/etc/shadow',          "Zugriff auf sensible Systemdateien"),
    (r'\.ssh[/\\]',                       "Zugriff auf SSH-Verzeichnis"),
    (r'http[s]?://(?!registry\.npmjs\.org|registry\.yarnpkg\.com|npm\.pkg\.github\.com)',
                                          "Ausgehender HTTP-Aufruf an Nicht-NPM-Registry im Install-Skript"),
    (r'\bstratum\+tcp\b|\bmonero\b|\bxmrig\b|\bcoinhive\b|\bcryptominer\b',
                                          "Krypto-Mining-Schlüsselwörter im Install-Skript"),
]

# Network indicators used for context-aware checks.
# _SCRIPT_NET_PAT  — matches inside a package.json lifecycle script string.
# _FILE_NET_PAT    — matches anywhere inside a JS/TS source file.
_SCRIPT_NET_PAT = re.compile(
    r'\bcurl\b|\bwget\b'
    r'|fetch\s*\('
    r'|require\s*\(\s*["\'](?:https?|http)["\']'
    r'|https?://',
    re.IGNORECASE,
)

_FILE_NET_PAT = re.compile(
    r'\b(?:fetch|axios|got|superagent)\s*\('
    r'|require\s*\(\s*["\'](?:https?|http|node-fetch|axios|got|superagent|request)["\']'
    r'|(?:from|import)\s+["\'](?:node-fetch|axios|got|superagent|request)["\']'
    r'|(?:https?|net)\.(?:get|request|connect)\s*\('
    r'|new\s+WebSocket\s*\(',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Code-level threat patterns for JS/TS/CJS files
# ---------------------------------------------------------------------------

@dataclass
class ThreatRule:
    category: str
    severity: str   # HIGH | MEDIUM | LOW
    pattern: re.Pattern
    description: str


def _rule(category: str, severity: str, pattern: str, description: str) -> ThreatRule:
    return ThreatRule(category, severity, re.compile(pattern, re.IGNORECASE), description)


CODE_THREAT_RULES: list[ThreatRule] = [
    # --- Verschleierung ---
    _rule("OBFUSCATION", "HIGH",
          r'\beval\s*\(\s*(?:Buffer\.from|atob|unescape)\s*\(',
          "eval() eines dekodierten Puffers — klassische verschleierte Payload-Auslieferung"),
    _rule("OBFUSCATION", "HIGH",
          r'\bBuffer\.from\s*\(\s*["\'][0-9a-fA-F]{32,}["\'],\s*["\']hex["\']',
          "Langer Hex-String via Buffer.from dekodiert — verschleierter Payload"),
    _rule("OBFUSCATION", "HIGH",
          r'\bBuffer\.from\s*\(\s*["\'][A-Za-z0-9+/]{40,}={0,2}["\'],\s*["\']base64["\']',
          "Langer Base64-String via Buffer.from dekodiert — verschleierter Payload"),
    _rule("OBFUSCATION", "HIGH",
          r'\bString\.fromCharCode\s*\(\s*(?:\d+\s*,\s*){5,}',
          "String.fromCharCode mit vielen Argumenten — Zeichencode-Verschleierung"),
    _rule("OBFUSCATION", "MEDIUM",
          r'\b_0x[0-9a-fA-F]{4,}\b',
          "Verschleierte _0x-Variablennamen — typische Ausgabe von JS-Obfuskatoren"),
    _rule("OBFUSCATION", "MEDIUM",
          r'(?:var|let|const)\s+[a-zA-Z_$][a-zA-Z0-9_$]*\s*=\s*["\'][0-9a-fA-F]{64,}["\']',
          "Sehr langer Hex-String einer Variablen zugewiesen"),
    _rule("OBFUSCATION", "LOW",
          r'\bunescape\s*\(%[0-9a-fA-F]{2}(?:%[0-9a-fA-F]{2}){5,}\)',
          "unescape() eines prozentkodierten Payloads"),

    # --- Exfiltration / Diebstahl von Anmeldedaten ---
    _rule("EXFILTRATION", "HIGH",
          r'process\.env\b.{0,120}(?:require\s*\(["\'](?:https?|http)["\']|fetch\s*\(|axios|request\s*\()',
          "process.env-Lesen kombiniert mit HTTP-Aufruf — Exfiltration von Umgebungsvariablen"),
    _rule("EXFILTRATION", "HIGH",
          r'(?:HOME|npm_config_registry|npm_token|NPM_TOKEN|AWS_SECRET|GITHUB_TOKEN'
          r'|GITLAB_TOKEN|CI_JOB_TOKEN|DOCKER_PASSWORD).{0,80}(?:http|fetch|axios|send)',
          "Sensibler Umgebungsvariablenname neben Netzwerkaufruf — Exfiltration von Anmeldedaten"),
    _rule("EXFILTRATION", "HIGH",
          r'(?:readFile|readFileSync)\s*\(["\'].*?(?:\.ssh|\.aws|\.npmrc|\.gitconfig|passwd|shadow)',
          "Lesen sensibler Konfigurations- oder Anmeldedatendateien"),
    _rule("EXFILTRATION", "MEDIUM",
          r'os\.homedir\(\).{0,60}(?:\.ssh|\.aws|\.npmrc|\.gitconfig)',
          "Zugriff auf Anmeldedatendateien im Home-Verzeichnis"),
    _rule("EXFILTRATION", "MEDIUM",
          r'require\s*\(["\']keytar["\']',
          "keytar (OS-Schlüsselbund-Zugriff) — kann legitim sein, aber prüfenswert"),

    # --- Dateisystem-Angriffe ---
    _rule("FILESYSTEM_ATTACK", "HIGH",
          r'(?:writeFile|appendFile|createWriteStream)\s*\(["\'](?:/etc/(?:passwd|shadow|cron)|'
          r'~?/\.(?:ssh|bashrc|bash_profile|profile|zshrc|zprofile|config/git))',
          "Schreiben in System-/Anmeldedatendateien — Hinweis auf Backdoor"),
    _rule("FILESYSTEM_ATTACK", "HIGH",
          r'(?:writeFile|appendFile|createWriteStream).{0,80}authorized_keys',
          "Schreiben in authorized_keys — SSH-Backdoor"),
    _rule("FILESYSTEM_ATTACK", "MEDIUM",
          r'(?:writeFile|appendFile).{0,80}(?:crontab|cron\.d|cron\.hourly)',
          "Schreiben in Cron-Verzeichnisse — Persistenzmechanismus"),
    _rule("FILESYSTEM_ATTACK", "MEDIUM",
          r'(?:writeFile|appendFile).{0,80}~?/\.(?:bashrc|profile|zshrc)',
          "Schreiben in Shell-RC-Dateien — Persistenzmechanismus"),

    # --- Krypto-Mining ---
    _rule("CRYPTOMINING", "HIGH",
          r'stratum\+tcp://',
          "Stratum-Mining-Protokoll-URL — Krypto-Miner"),
    _rule("CRYPTOMINING", "HIGH",
          r'\bxmrig\b|\bxmr-stak\b|\bcpuminer\b|\bnsfminer\b',
          "Bekannter Krypto-Miner-Binärname"),
    _rule("CRYPTOMINING", "HIGH",
          r'coinhive\.com|coin-hive\.com|minero\.cc|cryptoloot\.pro|webminepool\.com'
          r'|jsecoin\.com|monerominer\.',
          "Bekannte Krypto-Mining-Dienst-Domain"),
    _rule("CRYPTOMINING", "MEDIUM",
          r'\bCryptoNight\b|\bRandomX\b|\bEthash\b.{0,30}(?:worker|mine|pool|hash)',
          "Krypto-Mining-Algorithmusname neben Mining-Schlüsselwörtern"),

    # --- Remote-Ausführung ---
    _rule("REMOTE_EXEC", "HIGH",
          r'require\s*\(["\']child_process["\']\).{0,120}(?:exec|spawn|execSync|spawnSync)\s*\(',
          "child_process.exec/spawn — Remote-Befehlsausführung"),
    _rule("REMOTE_EXEC", "HIGH",
          r'new\s+Function\s*\(.{0,200}(?:fetch|http|Buffer\.from|atob)',
          "new Function() mit Netzwerk-/Dekodierungsinhalt — dynamische Code-Ausführung"),
    _rule("REMOTE_EXEC", "MEDIUM",
          r'vm\.runInNewContext\s*\(|vm\.runInThisContext\s*\(',
          "Node.js-vm-Modul-Ausführung — kann Sandbox-Escape ermöglichen"),
    _rule("REMOTE_EXEC", "MEDIUM",
          r'(?:https?\.get|fetch)\s*\(.{0,120}(?:eval|new\s+Function|vm\.run)',
          "Abrufen und Ausführen von Remote-Code"),

    # --- Supply-Chain / Event-Stream-Stil ---
    _rule("SUPPLY_CHAIN", "HIGH",
          r'_compile\s*\(\s*(?:decrypt|decipher|Buffer\.from)',
          "Module._compile() mit verschlüsseltem/dekodiertem Inhalt — Event-Stream-Angriff"),
    _rule("SUPPLY_CHAIN", "HIGH",
          r'require\.extensions\[|Module\._extensions\[',
          "Einschleusen in require.extensions — Supply-Chain-Hook"),
    _rule("SUPPLY_CHAIN", "MEDIUM",
          r'npm_lifecycle_event|npm_package_name.{0,80}(?:fetch|http|send)',
          "npm-Lifecycle-Umgebungsvariable neben Netzwerkaufruf — Exfiltration zur Installationszeit"),
    _rule("SUPPLY_CHAIN", "LOW",
          r'__webpack_require__\.c\b.{0,60}(?:eval|Function)',
          "Webpack-Interna kombiniert mit eval — mögliche Bundle-Vergiftung"),

    # --- Reverse Shells ---
    _rule("REMOTE_EXEC", "HIGH",
          r'(?:net\.connect|net\.createConnection|tls\.connect).{0,120}'
          r'(?:stdin|stdout|stderr|pipe|shell)',
          "TCP-Socket an stdio angebunden — Reverse-Shell-Muster"),
    _rule("REMOTE_EXEC", "HIGH",
          r'/bin/sh|/bin/bash.{0,30}(?:-i|-c).{0,30}(?:socket|connect|pipe)',
          "Shell mit -i/-c kombiniert mit Socket/Connect — Reverse Shell"),

    # --- String Splitting / dynamische Property-Zugriffe ---
    _rule("OBFUSCATION", "HIGH",
          r'\[\s*["\'][^"\']{1,20}["\']\s*\+\s*["\'][^"\']{1,20}["\']\s*\]',
          "Klammer-Notation mit String-Konkatenation — Verschleierung von Methodennamen "
          r'(z.B. [\"ex\"+\"ec\"] statt .exec)'),
    _rule("OBFUSCATION", "HIGH",
          r'require\s*\(\s*["\'][A-Za-z0-9_./$-]{1,30}["\']\s*\+\s*["\'][A-Za-z0-9_./$-]{1,30}["\']\s*\)',
          "require() mit aufgeteiltem String — verschleierter Modulname "
          r'(z.B. require(\"child_\"+\"process\"))'),
    _rule("OBFUSCATION", "MEDIUM",
          r'eval\s*\(\s*(?:["\'][^"\']*["\']\s*\+\s*){1,}["\'][^"\']*["\']\s*\)',
          "eval() eines zusammengesetzten Literals — Verschleierung von Code-Payload"),
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    category: str
    severity: str
    source: str
    detail: str
    file: str
    line: int
    context: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".jar", ".war", ".class", ".pyc", ".pyo", ".so", ".o", ".dll",
    ".exe", ".bin", ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv",
}

JS_EXTENSIONS = {
    ".js", ".cjs", ".mjs", ".ts", ".cts", ".mts", ".jsx", ".tsx",
}

SAFE_REGISTRIES = (
    "https://registry.npmjs.org",
    "https://registry.yarnpkg.com",
    "https://npm.pkg.github.com",
    "https://pkgs.dev.azure.com",
    "https://artifactory.",
    "https://nexus.",
)

BINARY_CHECK_BYTES = 8192
MAX_CACHE_MEMBER_BYTES = 512 * 1024  # 512 KB per member in tarball
# Lines longer than this in a text/JS file are suspicious — minified code is a
# common hiding spot for appended payloads that regex rules won't catch.
MINIFIED_LINE_THRESHOLD = 1000


def is_binary(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(BINARY_CHECK_BYTES)
    except OSError:
        return True


def get_tracked_files(repo_path: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", repo_path, "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    )
    return [
        os.path.join(repo_path, f)
        for f in result.stdout.splitlines()
        if f.strip()
    ]


def read_lines(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.readlines()
    except OSError:
        return []


def _find_hook_line(lines: list[str], hook: str) -> int:
    for i, line in enumerate(lines, 1):
        if hook in line:
            return i
    return 0


# ---------------------------------------------------------------------------
# Core JS line scanner (shared by file and cache scanners)
# ---------------------------------------------------------------------------

# Matches: const/let/var X = "part1" + "part2"  (variable that stores a split string)
_SPLIT_VAR_ASSIGN = re.compile(
    r'(?:var|let|const)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*'
    r'["\'][^"\']{1,30}["\']\s*\+\s*["\'][^"\']{1,30}["\']',
)
# Known dangerous module names whose parts are worth detecting when split
_DANGEROUS_MODULE_PARTS = re.compile(
    r'child|process|exec|spawn|eval|Function|require|fs|net|http|crypto|os',
    re.IGNORECASE,
)


def _scan_js_split_var(lines: list[str], rel_path: str) -> list[Finding]:
    """Detect the two-step pattern: var cp = 'child_'+'process'; require(cp)."""
    findings: list[Finding] = []
    assigned_vars: dict[str, int] = {}  # var name → line number of assignment

    for line_no, raw_line in enumerate(lines, 1):
        line_text = raw_line.rstrip("\n\r")
        m = _SPLIT_VAR_ASSIGN.search(line_text)
        if m:
            concat_expr = line_text[m.start():]
            if _DANGEROUS_MODULE_PARTS.search(concat_expr):
                assigned_vars[m.group(1)] = line_no

    if not assigned_vars:
        return findings

    # Second pass: look for require(var) or dynamic call using those variable names
    require_var = re.compile(
        r'require\s*\(\s*(' + '|'.join(re.escape(v) for v in assigned_vars) + r')\s*\)',
    )
    for line_no, raw_line in enumerate(lines, 1):
        line_text = raw_line.rstrip("\n\r")
        m = require_var.search(line_text)
        if m:
            var = m.group(1)
            findings.append(Finding(
                category="OBFUSCATION",
                severity="HIGH",
                source="OBFUSCATION",
                detail=f"require() mit Variable '{var}', die einen zusammengesetzten String hält "
                       f"(zugewiesen in Zeile {assigned_vars[var]}) — verschleierter Modulname",
                file=rel_path,
                line=line_no,
                context=line_text.strip()[:120],
            ))
    return findings


_PROC_ENV_LINE_PAT = re.compile(r'process\.env\b')
_CHILD_PROC_LINE_PAT = re.compile(r'require\s*\(\s*["\']child_process["\']')

_COMBINED_CHECKS = [
    (_PROC_ENV_LINE_PAT,   "process.env kombiniert mit Netzwerkaufruf im Install-Skript — mögliche Exfiltration"),
    (_CHILD_PROC_LINE_PAT, "child_process kombiniert mit Netzwerkaufruf im Install-Skript — mögliche Befehlsausführung"),
]


def _scan_js_cooccurrence(
    lines: list[str], rel_path: str, existing: list[Finding]
) -> list[Finding]:
    """Flag process.env / child_process at MEDIUM when the file also contains network code.

    Reports only the first occurrence of each pattern to avoid flooding output
    for React/Vite/Next.js files that use process.env on every other line.
    Lines already covered by a HIGH rule are skipped.
    """
    already_reported: set[int] = {f.line for f in existing}
    found_env = found_child = False
    findings: list[Finding] = []

    for line_no, raw_line in enumerate(lines, 1):
        if found_env and found_child:
            break
        if line_no in already_reported:
            continue
        line_text = raw_line.rstrip("\n\r")
        stripped = line_text.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*"):
            continue

        if not found_env and _PROC_ENV_LINE_PAT.search(line_text):
            found_env = True
            findings.append(Finding(
                category="EXFILTRATION",
                severity="MEDIUM",
                source="EXFILTRATION",
                detail="process.env in Datei mit Netzwerkfunktionen — prüfen ob Umgebungsvariablen exfiltriert werden",
                file=rel_path,
                line=line_no,
                context=line_text.strip()[:120],
            ))

        if not found_child and _CHILD_PROC_LINE_PAT.search(line_text):
            found_child = True
            findings.append(Finding(
                category="REMOTE_EXEC",
                severity="MEDIUM",
                source="REMOTE_EXEC",
                detail="child_process in Datei mit Netzwerkfunktionen — prüfen ob Befehle exfiltriert werden",
                file=rel_path,
                line=line_no,
                context=line_text.strip()[:120],
            ))

    return findings


def _scan_js_lines(lines: list[str], rel_path: str, has_network: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, raw_line in enumerate(lines, 1):
        line_text = raw_line.rstrip("\n\r")
        stripped = line_text.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*"):
            continue

        # Report one finding per threat category per line to avoid noise while
        # ensuring all distinct threat types on a line are captured.
        seen_categories: set[str] = set()
        for rule in CODE_THREAT_RULES:
            if rule.pattern.search(line_text) and rule.category not in seen_categories:
                seen_categories.add(rule.category)
                findings.append(Finding(
                    category=rule.category,
                    severity=rule.severity,
                    source=rule.category,
                    detail=rule.description,
                    file=rel_path,
                    line=line_no,
                    context=line_text.strip()[:120],
                ))

    findings.extend(_scan_js_split_var(lines, rel_path))

    if has_network:
        findings.extend(_scan_js_cooccurrence(lines, rel_path, findings))

    return findings


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def _scan_package_json_lines(lines: list[str], rel_path: str) -> list[Finding]:
    findings: list[Finding] = []
    raw = "".join(lines)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return findings

    scripts = data.get("scripts", {})

    # Check lifecycle hooks against INSTALL_SCRIPT_RULES
    for hook in LIFECYCLE_HOOKS:
        script_value = scripts.get(hook, "")
        if not script_value:
            continue
        for pattern_str, description in INSTALL_SCRIPT_RULES:
            if re.search(pattern_str, script_value, re.IGNORECASE):
                findings.append(Finding(
                    category="INSTALL_SCRIPT",
                    severity="HIGH",
                    source=f"scripts.{hook}",
                    detail=description,
                    file=rel_path,
                    line=_find_hook_line(lines, hook),
                    context=script_value[:120],
                ))
                break  # ein Befund pro Hook reicht

    # node -e inline eval — nur Lifecycle-Hooks, nicht alle Scripts
    for hook in LIFECYCLE_HOOKS:
        script_value = scripts.get(hook, "")
        if script_value and re.search(r'\bnode\s+-e\b|\bnode\s+--eval\b', script_value, re.IGNORECASE):
            findings.append(Finding(
                category="INSTALL_SCRIPT",
                severity="MEDIUM",
                source=f"scripts.{hook}",
                detail="node -e Inline-Auswertung im npm-Lifecycle-Skript",
                file=rel_path,
                line=_find_hook_line(lines, hook),
                context=script_value[:120],
            ))

    # process.env / child_process combined with network in install scripts.
    # Alone they are normal (env checks, build helpers); dangerous only when
    # combined with an outbound network call in the same script string.
    for hook in LIFECYCLE_HOOKS:
        script_value = scripts.get(hook, "")
        if not script_value or not _SCRIPT_NET_PAT.search(script_value):
            continue
        for pat, desc in _COMBINED_CHECKS:
            if pat.search(script_value):
                findings.append(Finding(
                    category="INSTALL_SCRIPT",
                    severity="HIGH",
                    source=f"scripts.{hook}",
                    detail=desc,
                    file=rel_path,
                    line=_find_hook_line(lines, hook),
                    context=script_value[:120],
                ))

    # Abhängigkeiten mit Git-URLs / Nicht-Registry-Quellen
    git_url_pat = re.compile(
        r'^(?:git\+(?:https?|ssh)://|git://|github:|bitbucket:|gitlab:|'
        r'(?:https?|ssh)://(?!registry\.npmjs\.org|registry\.yarnpkg\.com'
        r'|npm\.pkg\.github\.com|pkgs\.dev\.azure\.com))',
        re.IGNORECASE,
    )
    for dep_field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for pkg, version in data.get(dep_field, {}).items():
            if not isinstance(version, str):
                continue
            if git_url_pat.match(version):
                line_no = 0
                for i, line in enumerate(lines, 1):
                    if pkg in line:
                        line_no = i
                        break
                findings.append(Finding(
                    category="SUPPLY_CHAIN",
                    severity="MEDIUM",
                    source=f"{dep_field}.{pkg}",
                    detail=f"Abhängigkeit mit Nicht-Registry-URL: {version[:80]}",
                    file=rel_path,
                    line=line_no,
                    context=f'"{pkg}": "{version}"',
                ))

    return findings


def scan_package_json(path: str, rel_path: str) -> list[Finding]:
    return _scan_package_json_lines(read_lines(path), rel_path)


def _scan_npmrc_lines(lines: list[str], rel_path: str) -> list[Finding]:
    findings: list[Finding] = []

    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue

        m = re.match(r'(?:@[^:]+:)?registry\s*=\s*(.+)', line, re.IGNORECASE)
        if m:
            registry = m.group(1).strip()
            if not any(registry.startswith(s) for s in SAFE_REGISTRIES):
                findings.append(Finding(
                    category="SUPPLY_CHAIN",
                    severity="MEDIUM",
                    source=".npmrc",
                    detail=f"Nicht-Standard-npm-Registry: {registry}",
                    file=rel_path,
                    line=line_no,
                    context=line[:120],
                ))

        if re.search(r'[/_:]authToken\s*=\s*\S+', line, re.IGNORECASE):
            findings.append(Finding(
                category="EXFILTRATION",
                severity="MEDIUM",
                source=".npmrc",
                detail="Hardcodierter npm-Auth-Token in .npmrc — sollte Umgebungsvariable verwenden",
                file=rel_path,
                line=line_no,
                context=re.sub(r'(authToken\s*=\s*)\S+', r'\1***', line)[:120],
            ))

    return findings


def scan_npmrc(path: str, rel_path: str) -> list[Finding]:
    return _scan_npmrc_lines(read_lines(path), rel_path)


def _scan_yarnrc_lines(lines: list[str], rel_path: str) -> list[Finding]:
    findings: list[Finding] = []

    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = re.match(r'^registry\s+(.+)', line, re.IGNORECASE)
        if m:
            registry = m.group(1).strip()
            if not any(registry.startswith(s) for s in SAFE_REGISTRIES):
                findings.append(Finding(
                    category="SUPPLY_CHAIN",
                    severity="MEDIUM",
                    source=".yarnrc",
                    detail=f"Nicht-Standard-Yarn-Registry: {registry}",
                    file=rel_path,
                    line=line_no,
                    context=line[:120],
                ))

        if re.search(r'[/_:](?:_authToken|_password)\s*=\s*\S+', line, re.IGNORECASE):
            findings.append(Finding(
                category="EXFILTRATION",
                severity="MEDIUM",
                source=".yarnrc",
                detail="Hardcodiertes Authentifizierungstoken in .yarnrc",
                file=rel_path,
                line=line_no,
                context=re.sub(r'((?:_authToken|_password)\s*=\s*)\S+', r'\1***', line)[:120],
            ))

    return findings


def scan_yarnrc(path: str, rel_path: str) -> list[Finding]:
    """Scan Yarn v1 .yarnrc for suspicious registry and token config."""
    return _scan_yarnrc_lines(read_lines(path), rel_path)


def _scan_yarnrc_yml_lines(lines: list[str], rel_path: str) -> list[Finding]:
    findings: list[Finding] = []

    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = re.match(r'^npmRegistryServer:\s*["\']?(.+?)["\']?\s*$', line, re.IGNORECASE)
        if m:
            registry = m.group(1).strip()
            if not any(registry.startswith(s) for s in SAFE_REGISTRIES):
                findings.append(Finding(
                    category="SUPPLY_CHAIN",
                    severity="MEDIUM",
                    source=".yarnrc.yml",
                    detail=f"Nicht-Standard-Yarn-v2-Registry: {registry}",
                    file=rel_path,
                    line=line_no,
                    context=line[:120],
                ))

        if re.match(r'^npmAuthToken:\s*["\']?\S', line, re.IGNORECASE):
            findings.append(Finding(
                category="EXFILTRATION",
                severity="MEDIUM",
                source=".yarnrc.yml",
                detail="Hardcodierter npm-Auth-Token in .yarnrc.yml",
                file=rel_path,
                line=line_no,
                context=re.sub(r'(npmAuthToken:\s*)["\']?\S+["\']?', r'\1***', line)[:120],
            ))

        # Plugin loaded from external URL — high risk supply-chain vector
        if re.search(r'path:\s*https?://', line, re.IGNORECASE):
            findings.append(Finding(
                category="SUPPLY_CHAIN",
                severity="HIGH",
                source=".yarnrc.yml",
                detail="Yarn-Plugin von externer URL geladen — Supply-Chain-Risiko",
                file=rel_path,
                line=line_no,
                context=line[:120],
            ))

    return findings


def scan_yarnrc_yml(path: str, rel_path: str) -> list[Finding]:
    """Scan Yarn v2/v3 .yarnrc.yml for suspicious registry, token and plugin config."""
    return _scan_yarnrc_yml_lines(read_lines(path), rel_path)


def _scan_package_lock_lines(lines: list[str], rel_path: str) -> list[Finding]:
    findings: list[Finding] = []
    raw = "".join(lines)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return findings

    def check_resolved(pkg_name: str, resolved: str) -> None:
        if not isinstance(resolved, str) or not resolved:
            return
        if resolved.startswith("file:") or resolved.startswith("node_modules/"):
            return
        if any(resolved.startswith(s) for s in SAFE_REGISTRIES):
            return
        findings.append(Finding(
            category="SUPPLY_CHAIN",
            severity="MEDIUM",
            source="package-lock.json",
            detail=f"Aufgelöste URL zeigt auf Nicht-Standard-Registry: {resolved[:80]}",
            file=rel_path,
            line=0,
            context=f"{pkg_name}: {resolved[:80]}",
        ))

    lock_version = data.get("lockfileVersion", 1)
    if lock_version >= 2:
        # v2/v3 format: packages["node_modules/name"].resolved
        for pkg_path, pkg_info in data.get("packages", {}).items():
            if isinstance(pkg_info, dict):
                check_resolved(pkg_path, pkg_info.get("resolved", ""))
    else:
        # v1 format: dependencies[name].resolved (recursive)
        def walk_deps(deps: dict) -> None:
            for name, info in deps.items():
                if not isinstance(info, dict):
                    continue
                check_resolved(name, info.get("resolved", ""))
                if "dependencies" in info:
                    walk_deps(info["dependencies"])
        walk_deps(data.get("dependencies", {}))

    return findings


def scan_package_lock(path: str, rel_path: str) -> list[Finding]:
    """Scan package-lock.json for resolved URLs pointing to non-standard registries."""
    return _scan_package_lock_lines(read_lines(path), rel_path)


def _check_minified_lines(lines: list[str], rel_path: str) -> list[Finding]:
    """Flag JS files whose longest line exceeds MINIFIED_LINE_THRESHOLD.

    Minified/bundled code compresses logic into single huge lines; attackers
    append or embed payloads there knowing regex rules scan line-by-line and
    may miss content past a certain offset.  One LOW finding per file.
    """
    max_len = 0
    max_line_no = 0
    for line_no, raw_line in enumerate(lines, 1):
        line_len = len(raw_line.rstrip("\n\r"))
        if line_len > max_len:
            max_len = line_len
            max_line_no = line_no

    if max_len >= MINIFIED_LINE_THRESHOLD:
        return [Finding(
            category="OBFUSCATION",
            severity="LOW",
            source="MINIFIED_CODE",
            detail=(
                f"Längste Zeile hat {max_len} Zeichen — stark minimierter/verschleierter Code; "
                "statische Analyse eingeschränkt, manuell prüfen"
            ),
            file=rel_path,
            line=max_line_no,
            context=f"Zeile {max_line_no}: {max_len} Zeichen",
        )]
    return []


def scan_js_file(path: str, rel_path: str) -> list[Finding]:
    lines = read_lines(path)
    has_network = bool(_FILE_NET_PAT.search("".join(lines)))
    findings = _scan_js_lines(lines, rel_path, has_network=has_network)
    findings.extend(_check_minified_lines(lines, rel_path))
    return findings


def scan_file(path: str, config: "ScanConfig") -> list[Finding]:
    ext = Path(path).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return []

    rel_path = os.path.relpath(path, config.repo_path)

    parts = Path(rel_path).parts
    if "node_modules" in parts and not config.include_modules:
        return []

    # Native addons (.node) are compiled ELF/PE binaries — is_binary() would
    # skip them silently, but they can contain malicious native code and cannot
    # be statically analysed here.  Flag them so the operator is aware.
    if ext == ".node":
        return [Finding(
            category="SUPPLY_CHAIN",
            severity="MEDIUM",
            source="NATIVE_ADDON",
            detail=(
                "Native .node-Addon gefunden — kompilierter Nativer Code kann nicht statisch "
                "analysiert werden; Herkunft und Integrität manuell prüfen"
            ),
            file=rel_path,
            line=0,
            context=os.path.basename(path),
        )]

    if is_binary(path):
        return []

    name = os.path.basename(path).lower()

    if name == "package.json":
        return scan_package_json(path, rel_path)
    if name == "package-lock.json":
        return scan_package_lock(path, rel_path)
    if name in (".npmrc", ".npmrc.example"):
        return scan_npmrc(path, rel_path)
    if name == ".yarnrc":
        return scan_yarnrc(path, rel_path)
    if name in (".yarnrc.yml", ".yarnrc.yaml"):
        return scan_yarnrc_yml(path, rel_path)
    if ext in JS_EXTENSIONS:
        return scan_js_file(path, rel_path)

    return []


# ---------------------------------------------------------------------------
# npm cache scanning
# ---------------------------------------------------------------------------

def get_npm_cache_dir() -> str:
    try:
        result = subprocess.run(
            ["npm", "config", "get", "cache"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        path = result.stdout.strip()
        return path if path and os.path.isdir(path) else ""
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _scan_tarball(tgz_path: str, label: str) -> list[Finding]:
    """Extract and scan JS/JSON/config files inside a gzipped tarball."""
    findings: list[Finding] = []
    try:
        with gzip.open(tgz_path, "rb") as gz_fh:
            with tarfile.open(fileobj=gz_fh, mode="r:") as tf:
                for member in tf.getmembers():
                    if not member.isfile() or member.size > MAX_CACHE_MEMBER_BYTES:
                        continue

                    mname = member.name
                    ext = Path(mname).suffix.lower()
                    bname = Path(mname).name.lower()

                    is_js = ext in JS_EXTENSIONS
                    is_pkg = bname == "package.json"
                    is_lock = bname == "package-lock.json"
                    is_npmrc = bname in (".npmrc", ".npmrc.example")
                    is_yarnrc = bname == ".yarnrc"
                    is_yarnrc_yml = bname in (".yarnrc.yml", ".yarnrc.yaml")

                    if not any((is_js, is_pkg, is_lock, is_npmrc, is_yarnrc, is_yarnrc_yml)):
                        continue

                    fobj = tf.extractfile(member)
                    if fobj is None:
                        continue

                    raw = fobj.read().decode("utf-8", errors="replace")
                    rel = f"[cache:{label}]{mname}"

                    lines = raw.splitlines(keepends=True)
                    if is_js:
                        has_network = bool(_FILE_NET_PAT.search(raw))
                        findings.extend(_scan_js_lines(lines, rel, has_network=has_network))
                    elif is_pkg:
                        findings.extend(_scan_package_json_lines(lines, rel))
                    elif is_lock:
                        findings.extend(_scan_package_lock_lines(lines, rel))
                    elif is_npmrc:
                        findings.extend(_scan_npmrc_lines(lines, rel))
                    elif is_yarnrc:
                        findings.extend(_scan_yarnrc_lines(lines, rel))
                    elif is_yarnrc_yml:
                        findings.extend(_scan_yarnrc_yml_lines(lines, rel))

    except Exception:
        pass
    return findings


def scan_npm_cache(cache_dir: str, verbose: bool = False) -> list[Finding]:
    """
    Scan npm's content-addressed cache (_cacache/content-v2/) for malicious packages.
    Each blob in that directory is a gzipped tarball of a published package.
    """
    content_dir = os.path.join(cache_dir, "_cacache", "content-v2")
    if not os.path.isdir(content_dir):
        if verbose:
            print(f"  npm-Cache-Inhalt nicht gefunden: {content_dir}", file=sys.stderr)
        return []

    findings: list[Finding] = []
    count = 0
    for root, _, fnames in os.walk(content_dir):
        for fname in fnames:
            findings.extend(_scan_tarball(os.path.join(root, fname), fname[:16]))
            count += 1

    if verbose:
        print(f"  npm-Cache: {count} Blob(s) geprüft in {content_dir}")

    return findings


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

SEVERITY_LABEL = {
    "HIGH":   "[HIGH]  ",
    "MEDIUM": "[MED]   ",
    "LOW":    "[LOW]   ",
}


def print_text_report(findings: list[Finding]) -> None:
    if not findings:
        print("Keine NPM/JS-Bedrohungsindikatoren gefunden.")
        return

    findings_sorted = sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.file, f.line))

    by_category: dict[str, list[Finding]] = {}
    for f in findings_sorted:
        by_category.setdefault(f.category, []).append(f)

    print(f"\n{'='*72}")
    print(f"  NPM/JS-Bedrohungsscan — {len(findings)} Befund(e)")
    print(f"{'='*72}\n")

    category_order = ["INSTALL_SCRIPT", "EXFILTRATION",
                      "FILESYSTEM_ATTACK", "REMOTE_EXEC", "OBFUSCATION",
                      "CRYPTOMINING", "SUPPLY_CHAIN"]
    all_cats = category_order + [c for c in by_category if c not in category_order]

    for cat in all_cats:
        items = by_category.get(cat, [])
        if not items:
            continue
        print(f"  {cat} ({len(items)})")
        print(f"  {'-'*44}")
        for f in items:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            print(f"  {SEVERITY_LABEL[f.severity]} {loc}")
            print(f"    Detail : {f.detail}")
            print(f"    Context: {f.context}")
            print()

    highs   = sum(1 for f in findings if f.severity == "HIGH")
    mediums = sum(1 for f in findings if f.severity == "MEDIUM")
    lows    = sum(1 for f in findings if f.severity == "LOW")

    print(f"{'='*72}")
    print(f"  Gesamt: {len(findings)} Befund(e) in {len({f.file for f in findings})} Datei(en)"
          f"  [HIGH={highs}  MEDIUM={mediums}  LOW={lows}]")
    print(f"{'='*72}\n")


def print_json_report(findings: list[Finding]) -> None:
    data = [
        {
            "category": f.category,
            "severity": f.severity,
            "source": f.source,
            "detail": f.detail,
            "file": f.file,
            "line": f.line,
            "context": f.context,
        }
        for f in findings
    ]
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Config & main
# ---------------------------------------------------------------------------

@dataclass
class ScanConfig:
    repo_path: str
    include_modules: bool = False
    output_format: str = "text"
    no_fail: bool = False
    min_severity: str = "LOW"
    skip_patterns: list[str] = field(default_factory=list)
    scan_cache: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Durchsucht ein Node.js-Projekt nach JS/NPM-Trojaner- und Supply-Chain-Indikatoren.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Aktuelles Git-Repository scannen
  python3 scan-npm.py

  # Bestimmten Pfad scannen, JSON-Ausgabe
  python3 scan-npm.py /pfad/zum/repo --format json

  # Nur HIGH-Schweregrad, node_modules einschließen
  python3 scan-npm.py --min-severity HIGH --include-modules

  # Inkl. npm-Cache scannen (~/.npm/_cacache)
  python3 scan-npm.py --scan-cache

  # CI: Pipeline bei Befunden nicht fehlschlagen lassen
  python3 scan-npm.py --no-fail
""",
    )
    parser.add_argument("repo", nargs="?", default=".",
                        help="Pfad zum Repository-Wurzelverzeichnis (Standard: .)")
    parser.add_argument("--include-modules", action="store_true",
                        help="node_modules/ ebenfalls scannen (kann langsam sein)")
    parser.add_argument("--min-severity", choices=["HIGH", "MEDIUM", "LOW"], default="LOW",
                        help="Minimaler Schweregrad für die Ausgabe (Standard: LOW)")
    parser.add_argument("--skip", nargs="*", default=[], metavar="MUSTER",
                        help="Reguläre Ausdrücke für zu überspringende Pfade")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        dest="output_format", help="Ausgabeformat")
    parser.add_argument("--no-fail", action="store_true",
                        help="Immer mit Exit-Code 0 beenden, auch bei Befunden")
    parser.add_argument("--scan-cache", action="store_true",
                        help="npm-Cache via 'npm config get cache' ebenfalls scannen")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    is_git = os.path.isdir(os.path.join(repo_path, ".git"))

    config = ScanConfig(
        repo_path=repo_path,
        include_modules=args.include_modules,
        output_format=args.output_format,
        no_fail=args.no_fail,
        min_severity=args.min_severity,
        skip_patterns=args.skip or [],
        scan_cache=args.scan_cache,
    )

    # Collect files: prefer git-tracked list, fall back to filesystem walk
    if is_git:
        try:
            files = get_tracked_files(repo_path)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"FEHLER: git ls-files fehlgeschlagen: {exc}", file=sys.stderr)
            return 2
    else:
        files = []
        for root, dirs, fnames in os.walk(repo_path):
            if not config.include_modules:
                dirs[:] = [d for d in dirs if d != "node_modules"]
            for fname in fnames:
                files.append(os.path.join(root, fname))

    # Apply skip patterns
    def should_skip(path: str) -> bool:
        rel = os.path.relpath(path, repo_path)
        for pat in config.skip_patterns:
            try:
                if re.search(pat, rel, re.IGNORECASE):
                    return True
            except re.error:
                if pat.lower() in rel.lower():
                    return True
        return False

    min_sev_order = SEVERITY_ORDER.get(config.min_severity, 2)

    if config.output_format == "text":
        print(f"Scanne {len(files)} Datei(en) in '{repo_path}' ...")

    all_findings: list[Finding] = []
    for path in files:
        if should_skip(path):
            continue
        for f in scan_file(path, config):
            if SEVERITY_ORDER.get(f.severity, 9) <= min_sev_order:
                all_findings.append(f)

    # Optional: npm cache scan
    if config.scan_cache:
        cache_dir = get_npm_cache_dir()
        if cache_dir:
            if config.output_format == "text":
                print(f"Scanne npm-Cache in '{cache_dir}' (kann dauern) ...")
            for f in scan_npm_cache(cache_dir, verbose=(config.output_format == "text")):
                if SEVERITY_ORDER.get(f.severity, 9) <= min_sev_order:
                    all_findings.append(f)
        elif config.output_format == "text":
            print("npm nicht verfügbar oder Cache-Verzeichnis nicht gefunden — Cache-Scan übersprungen.",
                  file=sys.stderr)

    if config.output_format == "json":
        print_json_report(all_findings)
    else:
        print_text_report(all_findings)

    if all_findings and not config.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

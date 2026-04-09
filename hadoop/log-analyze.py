#!/usr/bin/env python3
"""
Hadoop / ZooKeeper Log Analyzer
Analyzes log files for NameNode, JournalNode, DataNode, and ZooKeeper.
Usage: python3 log-analyze.py <log-directory>
"""

import sys
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ── Pattern definitions ────────────────────────────────────────────────────────

SEVERITY_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]?\d*)\s+"
    r"(?P<level>FATAL|ERROR|WARN|WARNING|INFO|DEBUG)\s+",
    re.IGNORECASE,
)

ZK_SEVERITY_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+\[.*?\]\s+"
    r"(?P<level>FATAL|ERROR|WARN|WARNING|INFO|DEBUG)\s+",
    re.IGNORECASE,
)

COMPONENT_FILE_PATTERNS = {
    "namenode":    re.compile(r"namenode|nn\b", re.IGNORECASE),
    "journalnode": re.compile(r"journalnode|jn\b", re.IGNORECASE),
    "datanode":    re.compile(r"datanode|dn\b", re.IGNORECASE),
    "zookeeper":   re.compile(r"zookeeper|zk\b", re.IGNORECASE),
}

# ── Problem signatures per component ──────────────────────────────────────────

PROBLEM_PATTERNS = {
    "namenode": [
        # SafeMode
        (re.compile(r"Safemode is (ON|enabled)", re.I),                      "SafeMode aktiv"),
        (re.compile(r"name node is in safe mode", re.I),                     "SafeMode aktiv"),
        # EditLog / FSImage
        (re.compile(r"EditLog.*IOException|EditLog.*Error", re.I),            "EditLog-Fehler"),
        (re.compile(r"FSImage.*IOException|Failed to load.*image", re.I),    "FSImage-Ladefehler"),
        (re.compile(r"Checkpointing.*failed|checkpoint.*error", re.I),       "Checkpoint-Fehler"),
        (re.compile(r"roll.*edit.*log.*fail|Failed to roll", re.I),          "EditLog-Roll-Fehler"),
        # HA / Quorum
        (re.compile(r"Failed to start namenode", re.I),                      "NameNode-Start fehlgeschlagen"),
        (re.compile(r"Standby NameNode.*Exception", re.I),                   "Standby-NameNode-Problem"),
        (re.compile(r"LeaderElection.*Exception|elector.*failed", re.I),     "Leader-Election-Problem"),
        (re.compile(r"Failed to connect to.*JournalNode", re.I),             "JournalNode nicht erreichbar"),
        (re.compile(r"Could not roll.*edit.*logs.*on.*journal", re.I),       "JournalNode-Roll-Fehler"),
        (re.compile(r"Quorum of journals.*required.*unavailable", re.I),     "JournalNode-Quorum fehlt"),
        (re.compile(r"fencing.*failed|FENCE.*ERROR", re.I),                  "Fencing fehlgeschlagen (HA)"),
        (re.compile(r"ActiveStandbyElector.*Exception", re.I),               "ZooKeeper-Election-Fehler"),
        (re.compile(r"health check.*failed|HealthMonitor.*unhealthy", re.I), "NN-Healthcheck fehlgeschlagen"),
        # Blöcke / Replikation
        (re.compile(r"Block.*missing|UnderReplicatedBlocks", re.I),          "Unterreplizierte Blöcke"),
        (re.compile(r"Marking .* as corrupt", re.I),                         "Block als korrumpiert markiert"),
        (re.compile(r"DataNode.*dead|Lost contact with DataNode", re.I),     "DataNode als tot markiert"),
        (re.compile(r"OverReplicatedBlocks", re.I),                          "Überreplizierte Blöcke"),
        (re.compile(r"PendingReplicationMonitor timed out", re.I),           "Replikations-Timeout"),
        # RPC / Netz
        (re.compile(r"connect(ion)? refused|Connection reset", re.I),        "Verbindungsfehler"),
        (re.compile(r"RPC.*timed? out|RpcTimeout", re.I),                    "RPC-Timeout"),
        (re.compile(r"ipc.*Server.*exception|RetriableException", re.I),     "IPC-Server-Fehler"),
        # Ressourcen
        (re.compile(r"GC overhead limit exceeded", re.I),                    "GC-Überlast (OOM-Gefahr)"),
        (re.compile(r"OutOfMemoryError", re.I),                              "OutOfMemoryError"),
        (re.compile(r"Unable to load (native hadoop|libhadoop)", re.I),      "Native Bibliothek fehlt"),
        # Kerberos / Security
        (re.compile(r"Kerberos.*fail|kinit.*error|TGT.*renew.*fail", re.I),  "Kerberos-Authentifizierungsfehler"),
        (re.compile(r"token.*expired|DelegationToken.*expired", re.I),       "Delegation-Token abgelaufen"),
    ],
    "journalnode": [
        # IO / Segment
        (re.compile(r"IOException|SocketException", re.I),                   "IO-/Socket-Fehler"),
        (re.compile(r"Segment.*corrupt|corrupt.*segment", re.I),             "Segment korrumpiert"),
        (re.compile(r"Failed to.*journal|journal.*fail", re.I),              "Journal-Schreibfehler"),
        (re.compile(r"gap in.*log.*segment|missing.*segment", re.I),         "Lücke in Journal-Segmenten"),
        (re.compile(r"log segment.*not found|segment.*does not exist", re.I),"Journal-Segment fehlt"),
        (re.compile(r"finalize.*segment.*fail|Failed to finalize", re.I),    "Segment-Finalisierungsfehler"),
        # HA / Sync
        (re.compile(r"out of sync|log.*diverged", re.I),                     "Journal-Divergenz (out of sync)"),
        (re.compile(r"Epoch.*mismatch|wrong.*epoch", re.I),                  "Epoch-Konflikt zwischen NNs"),
        (re.compile(r"prepare.*recover.*fail|recoverUnfinalizedSegments.*fail", re.I), "Recovery-Fehler"),
        # Netz
        (re.compile(r"connect(ion)? refused|Connection reset", re.I),        "Verbindungsfehler"),
        (re.compile(r"RPC.*timed? out|RpcTimeout", re.I),                    "RPC-Timeout"),
        # Ressourcen
        (re.compile(r"GC overhead limit exceeded", re.I),                    "GC-Überlast (OOM-Gefahr)"),
        (re.compile(r"OutOfMemoryError", re.I),                              "OutOfMemoryError"),
        (re.compile(r"disk.*full|No space left", re.I),                      "Festplatte voll"),
        # Kerberos
        (re.compile(r"Kerberos.*fail|kinit.*error|TGT.*renew.*fail", re.I),  "Kerberos-Authentifizierungsfehler"),
    ],
    "datanode": [
        # Disk / Block
        (re.compile(r"Disk.*error|IOException.*block", re.I),                "Festplatten-/Block-Fehler"),
        (re.compile(r"Failed to initialize.*volume|Bad local volume", re.I), "Volume-Initialisierungsfehler"),
        (re.compile(r"All volumes.*failed|no valid volumes", re.I),          "Alle Volumes ausgefallen"),
        (re.compile(r"Block.*corrupt|corrupt.*block", re.I),                 "Korrumpierter Block"),
        (re.compile(r"Marking block .* as corrupt", re.I),                   "Block als korrumpiert markiert"),
        (re.compile(r"BlockSender.*IOException", re.I),                      "Block-Sende-Fehler"),
        (re.compile(r"No space left|disk.*full", re.I),                      "Festplatte voll"),
        (re.compile(r"reservedSpace.*exceeded|DataNode.*low.*disk", re.I),   "DataNode Disk fast voll"),
        (re.compile(r"Short circuit.*fail|ShortCircuit.*error", re.I),       "Short-Circuit-Lesefehler"),
        # Netz / NN-Verbindung
        (re.compile(r"Heartbeat.*failed|missed.*heartbeat", re.I),           "Heartbeat-Ausfall"),
        (re.compile(r"Failed to connect.*NameNode|NameNode.*unreachable", re.I), "NameNode nicht erreichbar"),
        (re.compile(r"connect(ion)? refused|Connection reset", re.I),        "Verbindungsfehler"),
        (re.compile(r"RPC.*timed? out|RpcTimeout", re.I),                    "RPC-Timeout"),
        (re.compile(r"DataXceiver.*Exception", re.I),                        "DataXceiver-Fehler (Datenübertragung)"),
        (re.compile(r"PacketResponder.*Exception", re.I),                    "PacketResponder-Fehler"),
        (re.compile(r"write pipeline.*error|pipeline.*broken", re.I),        "Write-Pipeline-Fehler"),
        # Ressourcen
        (re.compile(r"GC overhead limit exceeded", re.I),                    "GC-Überlast (OOM-Gefahr)"),
        (re.compile(r"OutOfMemoryError", re.I),                              "OutOfMemoryError"),
        (re.compile(r"Too many open files", re.I),                           "Zu viele offene Dateien (ulimit)"),
        # Kerberos
        (re.compile(r"Kerberos.*fail|kinit.*error|TGT.*renew.*fail", re.I),  "Kerberos-Authentifizierungsfehler"),
    ],
    "zookeeper": [
        # Sessions
        (re.compile(r"SessionExpired|session.*expired", re.I),               "ZooKeeper-Session abgelaufen"),
        (re.compile(r"session.*0x[0-9a-f]+.*closed", re.I),                  "ZooKeeper-Session geschlossen"),
        (re.compile(r"Too many connections", re.I),                           "Zu viele Verbindungen"),
        (re.compile(r"maxClientCnxns.*exceeded|connection.*limit.*reached", re.I), "Connection-Limit erreicht"),
        # Netz / Quorum
        (re.compile(r"Connection.*loss|ConnectionLoss", re.I),               "Verbindungsverlust"),
        (re.compile(r"leader.*election|Election.*exception", re.I),          "Leader-Election-Problem"),
        (re.compile(r"LOOKING.*timeout|Quorum.*fail", re.I),                 "Quorum nicht erreichbar"),
        (re.compile(r"Unable to load database.*snap", re.I),                 "Snapshot-Ladefehler"),
        (re.compile(r"IOException|SocketException", re.I),                   "IO-/Socket-Fehler"),
        (re.compile(r"Cannot open channel to .* at election address", re.I), "Peer-Verbindungsfehler"),
        # Daten / Transaktion
        (re.compile(r"sync.*fail|Sync.*error", re.I),                        "Sync-Fehler"),
        (re.compile(r"transaction log.*corrupt|Truncating.*log", re.I),      "Transaktions-Log korrumpiert"),
        (re.compile(r"Epoch.*mismatch|ZXID.*mismatch", re.I),               "Epoch/ZXID-Konflikt"),
        (re.compile(r"Failed to write.*txnLog|txnLog.*IOException", re.I),   "Transaktions-Log Schreibfehler"),
        # Ressourcen
        (re.compile(r"disk.*full|No space left", re.I),                      "Festplatte voll"),
        (re.compile(r"GC overhead limit exceeded", re.I),                    "GC-Überlast (OOM-Gefahr)"),
        (re.compile(r"OutOfMemoryError", re.I),                              "OutOfMemoryError"),
        (re.compile(r"Request throttled|Throttled.*request", re.I),          "Request-Throttling aktiv"),
        # Auth
        (re.compile(r"AuthFailed|authentication.*failed", re.I),             "Authentifizierungsfehler"),
        (re.compile(r"Kerberos.*fail|kinit.*error", re.I),                   "Kerberos-Fehler"),
    ],
}

GENERIC_PROBLEM_PATTERNS = [
    (re.compile(r"GC overhead limit exceeded", re.I),      "GC-Überlast (OOM-Gefahr)"),
    (re.compile(r"OutOfMemoryError", re.I),                "OutOfMemoryError"),
    (re.compile(r"connect(ion)? refused", re.I),           "Verbindung abgelehnt"),
    (re.compile(r"No space left on device", re.I),         "Festplatte voll"),
    (re.compile(r"Too many open files", re.I),             "Zu viele offene Dateien (ulimit)"),
    (re.compile(r"Kerberos.*fail|kinit.*error", re.I),     "Kerberos-Authentifizierungsfehler"),
    (re.compile(r"RPC.*timed? out|RpcTimeout", re.I),      "RPC-Timeout"),
    (re.compile(r"StackOverflowError", re.I),              "StackOverflowError"),
    (re.compile(r"java\.lang\.NullPointerException", re.I),"NullPointerException"),
    (re.compile(r"Address already in use", re.I),          "Port bereits belegt"),
]


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class LogEntry:
    timestamp: str
    level: str
    message: str
    line_no: int
    raw: str


@dataclass
class ComponentResult:
    component: str
    log_file: Path
    total_lines: int = 0
    counts: dict = field(default_factory=lambda: defaultdict(int))
    problems: list = field(default_factory=list)   # (line_no, timestamp, description, raw)
    errors: list = field(default_factory=list)     # (line_no, timestamp, raw)
    warnings: list = field(default_factory=list)   # (line_no, timestamp, raw)


# ── Helpers ────────────────────────────────────────────────────────────────────

def detect_component(filename: str) -> Optional[str]:
    for component, pattern in COMPONENT_FILE_PATTERNS.items():
        if pattern.search(filename):
            return component
    return None


def parse_level(line: str) -> Optional[tuple[str, str, str]]:
    """Return (timestamp, level, rest) or None."""
    for pat in (SEVERITY_PATTERN, ZK_SEVERITY_PATTERN):
        m = pat.match(line)
        if m:
            ts = m.group("timestamp")
            lvl = m.group("level").upper().replace("WARNING", "WARN")
            rest = line[m.end():]
            return ts, lvl, rest
    return None


def analyze_file(log_file: Path, component: str) -> ComponentResult:
    result = ComponentResult(component=component, log_file=log_file)
    patterns = PROBLEM_PATTERNS.get(component, []) + GENERIC_PROBLEM_PATTERNS

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, raw in enumerate(fh, 1):
                result.total_lines += 1
                raw = raw.rstrip("\n")
                parsed = parse_level(raw)
                if not parsed:
                    continue
                ts, level, _ = parsed
                result.counts[level] += 1

                if level in ("ERROR", "FATAL"):
                    result.errors.append((line_no, ts, raw))

                if level == "WARN":
                    result.warnings.append((line_no, ts, raw))

                # Check problem patterns regardless of level (some appear in WARN/INFO)
                for pattern, description in patterns:
                    if pattern.search(raw):
                        result.problems.append((line_no, ts, description, raw))
                        break
    except OSError as exc:
        result.problems.append((0, "?", f"Datei nicht lesbar: {exc}", ""))

    return result


# ── Report printing ────────────────────────────────────────────────────────────

ANSI = {
    "red":    "\033[91m",
    "yellow": "\033[93m",
    "green":  "\033[92m",
    "cyan":   "\033[96m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
}

def c(text, *codes):
    if not sys.stdout.isatty():
        return str(text)
    return "".join(ANSI.get(k, "") for k in codes) + str(text) + ANSI["reset"]


def print_result(result: ComponentResult, max_errors: int = 10, max_problems: int = 10):
    status = c("OK", "green", "bold") if not result.problems else c("PROBLEME GEFUNDEN", "red", "bold")
    print(f"\n{'─'*70}")
    print(f"  {c(result.component.upper(), 'cyan', 'bold')}  │  {result.log_file.name}  │  {status}")
    print(f"{'─'*70}")
    print(f"  Zeilen gesamt : {result.total_lines}")
    for lvl in ("FATAL", "ERROR", "WARN", "INFO", "DEBUG"):
        n = result.counts.get(lvl, 0)
        if n == 0:
            continue
        col = "red" if lvl in ("FATAL", "ERROR") else "yellow" if lvl == "WARN" else "reset"
        print(f"  {lvl:<8}: {c(n, col)}")

    if result.problems:
        print(f"\n  {c('Erkannte Probleme:', 'red', 'bold')}")
        seen = set()
        shown = 0
        for line_no, ts, desc, raw in result.problems:
            if desc in seen:
                continue
            seen.add(desc)
            shown += 1
            if shown > max_problems:
                print(f"    … und {len(result.problems) - max_problems} weitere")
                break
            print(f"    [{c('!', 'red')}] Zeile {line_no:>6}  {ts}  →  {c(desc, 'yellow')}")

    if result.errors:
        print(f"\n  {c('Letzte ERROR/FATAL-Einträge:', 'red')}")
        for line_no, ts, raw in result.errors[-max_errors:]:
            trimmed = raw[:120] + ("…" if len(raw) > 120 else "")
            print(f"    Zeile {line_no:>6}  {ts}  {c(trimmed, 'red')}")


def print_summary(results: list[ComponentResult]):
    print(f"\n{'═'*70}")
    print(c("  ZUSAMMENFASSUNG", "bold"))
    print(f"{'═'*70}")
    ok = [r for r in results if not r.problems]
    nok = [r for r in results if r.problems]
    for r in ok:
        errors = r.counts.get("ERROR", 0) + r.counts.get("FATAL", 0)
        warns  = r.counts.get("WARN", 0)
        print(f"  {c('✓', 'green')} {r.component:<12} {r.log_file.name:<40} "
              f"ERR={errors}  WARN={warns}")
    for r in nok:
        errors = r.counts.get("ERROR", 0) + r.counts.get("FATAL", 0)
        warns  = r.counts.get("WARN", 0)
        descs  = ", ".join({d for _, _, d, _ in r.problems})
        print(f"  {c('✗', 'red')} {r.component:<12} {r.log_file.name:<40} "
              f"ERR={errors}  WARN={warns}  → {c(descs[:60], 'yellow')}")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"Verwendung: {sys.argv[0]} <log-verzeichnis>")
        sys.exit(1)

    log_dir = Path(sys.argv[1])
    if not log_dir.is_dir():
        print(f"Fehler: '{log_dir}' ist kein Verzeichnis.")
        sys.exit(1)

    log_files = sorted(
        p for p in log_dir.rglob("*")
        if p.is_file() and p.suffix in (".log", ".out", ".txt", "") and p.stat().st_size > 0
    )

    if not log_files:
        print(f"Keine Log-Dateien in '{log_dir}' gefunden.")
        sys.exit(0)

    print(c(f"\nHadoop / ZooKeeper Log-Analyse  →  {log_dir}", "bold"))
    print(f"Gefundene Dateien: {len(log_files)}\n")

    results = []
    unrecognized = []

    for lf in log_files:
        component = detect_component(lf.name)
        if component is None:
            unrecognized.append(lf)
            continue
        print(f"  Analysiere {c(component, 'cyan')} : {lf.name} …", end="\r")
        result = analyze_file(lf, component)
        results.append(result)
        print_result(result)

    if unrecognized:
        print(f"\n{c('Nicht zugeordnete Dateien (kein bekannter Komponenten-Name):', 'yellow')}")
        for lf in unrecognized:
            print(f"  • {lf}")

    if results:
        print_summary(results)
    else:
        print(c("Keine erkennbaren Hadoop/ZooKeeper-Log-Dateien gefunden.", "yellow"))
        print("Dateinamen müssen 'namenode', 'journalnode', 'datanode' oder 'zookeeper' enthalten.")


if __name__ == "__main__":
    main()

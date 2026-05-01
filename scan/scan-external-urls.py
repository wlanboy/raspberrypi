#!/usr/bin/env python3
"""
scan_external_urls.py - Scans a git repository for external URLs, emails,
hostnames, and IP addresses that could leak data or cause unintended outbound
connections in tests or code.

Exit codes:
  0 - No findings (or --no-fail set)
  1 - Findings detected
  2 - Script error (invalid arguments, not a git repo, etc.)
"""

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r'https?://[^\s\'"<>()\[\]{}\\,;]+'
    r'(?:[^\s\'"<>()\[\]{}\\,;.!?])',
    re.IGNORECASE,
)

EMAIL_PATTERN = re.compile(
    r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b'
)

# Matches hostnames like "api.example.com", "mail.internal.corp"
# Requires at least one dot and a known-ish TLD length (2-6 chars).
# Each segment must be at least 2 chars to exclude single-letter variables (p.name, p.parent).
HOSTNAME_PATTERN = re.compile(
    r'\b(?:[a-zA-Z0-9][a-zA-Z0-9\-]{0,60}[a-zA-Z0-9]\.)'
    r'+[a-zA-Z]{2,6}\b'
)

IP_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)

# Positive TLD allowlist: only matches whose last label is in this set are
# reported as hostnames. Using a whitelist is far more stable than maintaining
# a growing blacklist of code-like suffixes (error, name, parent, boot, …).
KNOWN_TLDS = {
    # Generic gTLDs
    "com", "org", "net", "edu", "gov", "mil", "int", "info", "biz",
    # Tech/cloud gTLDs
    "io", "co", "ai", "app", "dev", "cloud", "tech", "online", "site",
    # Common ccTLDs
    "ac", "ae", "at", "au", "be", "br", "ca", "ch", "cn", "cz",
    "de", "dk", "es", "eu", "fi", "fr", "gr", "hk", "hu",
    "il", "in", "it", "jp", "kr", "mx", "nl", "no", "nz", "pl",
    "pt", "ro", "ru", "se", "sg", "tr", "tw", "uk", "us", "za",
    # Short ccTLDs used as domain hacks
    "me", "ly", "to", "im", "gg", "gl", "fm", "tv", "cc",
    # NOTE: "sh" omitted — conflicts with shell scripts (stats.sh, addserver.sh)
    # NOTE: "id" omitted — conflicts with JS/Python attribute access (this.id, obj.id)
}

# Binary file detection: read first 8 KB and look for null bytes
BINARY_CHECK_BYTES = 8192

# Extensions that are always skipped (images, compiled artifacts, …)
ALWAYS_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".webp", ".tiff", ".pdf", ".zip", ".tar", ".gz", ".bz2",
    ".xz", ".7z", ".rar", ".jar", ".war", ".ear", ".class",
    ".pyc", ".pyo", ".so", ".o", ".a", ".dll", ".exe", ".bin",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv",
    ".lock",  # package-lock.json, yarn.lock etc. are noisy
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    category: str   # "url" | "email" | "hostname" | "ip"
    value: str
    file: str
    line: int
    context: str


@dataclass
class Whitelist:
    ip_ranges: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = field(default_factory=list)
    hostnames: list[str] = field(default_factory=list)
    email_domains: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)


@dataclass
class ScanConfig:
    repo_path: str
    allowlist: list[str] = field(default_factory=list)
    skip_patterns: list[str] = field(default_factory=list)
    categories: set[str] = field(default_factory=lambda: {"url", "email", "hostname", "ip"})
    skip_tests: bool = False
    output_format: str = "text"   # "text" | "json"
    no_fail: bool = False
    ignore_ips: set[str] = field(default_factory=set)
    ignore_all_ips: bool = False
    whitelist: Whitelist = field(default_factory=Whitelist)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tracked_files(repo_path: str) -> list[str]:
    """Return all files tracked by git (respects .gitignore automatically)."""
    result = subprocess.run(
        ["git", "-C", repo_path, "ls-files", "--cached", "--others",
         "--exclude-standard"],
        capture_output=True, text=True, check=True,
    )
    return [
        os.path.join(repo_path, f)
        for f in result.stdout.splitlines()
        if f.strip()
    ]


def is_binary(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(BINARY_CHECK_BYTES)
    except OSError:
        return True


def is_test_file(path: str) -> bool:
    lower = path.lower()
    return (
        "/test/" in lower
        or "/tests/" in lower
        or "\\test\\" in lower
        or "\\tests\\" in lower
        or os.path.basename(lower).startswith("test_")
        or os.path.basename(lower).endswith("_test.py")
        or os.path.basename(lower).endswith(".test.ts")
        or os.path.basename(lower).endswith(".spec.ts")
        or os.path.basename(lower).endswith("Test.java")
    )


def matches_any(value: str, patterns: list[str]) -> bool:
    value_lower = value.lower()
    for pattern in patterns:
        try:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        except re.error:
            if pattern.lower() in value_lower:
                return True
    return False


# ---------------------------------------------------------------------------
# Per-line scanning
# ---------------------------------------------------------------------------

def scan_line(line_text: str, config: ScanConfig) -> list[tuple[str, str]]:
    """Return list of (category, value) matches in a single line."""
    hits: list[tuple[str, str]] = []

    if "url" in config.categories:
        for m in URL_PATTERN.finditer(line_text):
            hits.append(("url", m.group(0)))

    if "email" in config.categories:
        for m in EMAIL_PATTERN.finditer(line_text):
            # Avoid reporting the same value already caught as a URL
            already = any(m.group(0) in v for c, v in hits if c == "url")
            if not already:
                hits.append(("email", m.group(0)))

    if "hostname" in config.categories:
        # Only report hostnames that are NOT part of an already-found URL/email
        already_values = {v for _, v in hits}
        for m in HOSTNAME_PATTERN.finditer(line_text):
            host = m.group(0)
            # Skip function/method calls: subprocess.run(, os.path.join(
            if m.end() < len(line_text) and line_text[m.end()] == "(":
                continue
            # Skip file path components: /etc/hostapd/hostapd.conf
            if m.start() > 0 and line_text[m.start() - 1] == "/":
                continue
            # Only report if the TLD is a known real TLD
            suffix = host.rsplit(".", 1)[-1].lower()
            if suffix not in KNOWN_TLDS:
                continue
            # Skip all-uppercase non-TLD part: DOS filenames (MOUSE.COM) or constants
            non_tld = host.rsplit(".", 1)[0]
            if non_tld == non_tld.upper() and any(c.isalpha() for c in non_tld):
                continue
            # Skip Python/JS import statements: "from textual.app import", "import x.y"
            before_stripped = line_text[:m.start()].rstrip()
            if re.search(r'\b(?:from|import)$', before_stripped):
                continue
            # Skip Kubernetes API groups and annotation keys: networking.istio.io/v1
            # or nginx.ingress.kubernetes.io/rewrite-target — hostname followed by /
            if m.end() < len(line_text) and line_text[m.end()] == "/":
                continue
            # Skip bare Kubernetes apiGroup values: "apiGroup: rbac.authorization.k8s.io"
            if re.search(r'\bapiGroups?\s*:\s+' + re.escape(host) + r'\s*$', line_text):
                continue
            # Skip bare YAML list items: "  - containerd.io" (package names, not URLs)
            if re.match(r'^\s*-\s+' + re.escape(host) + r'\s*$', line_text):
                continue
            if not any(host in v for v in already_values):
                hits.append(("hostname", host))

    if "ip" in config.categories and not config.ignore_all_ips:
        for m in IP_PATTERN.finditer(line_text):
            ip = m.group(0)
            if ip not in config.ignore_ips:
                hits.append(("ip", ip))

    return hits


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def scan_file(path: str, config: ScanConfig) -> list[Finding]:
    findings: list[Finding] = []

    # Skip by extension
    ext = Path(path).suffix.lower()
    if ext in ALWAYS_SKIP_EXTENSIONS:
        return findings

    # Skip test files if requested
    if config.skip_tests and is_test_file(path):
        return findings

    # Skip explicitly excluded path patterns
    rel_path = os.path.relpath(path, config.repo_path)
    if matches_any(rel_path, config.skip_patterns):
        return findings

    if is_binary(path):
        return findings

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return findings

    for line_no, raw_line in enumerate(lines, start=1):
        line_text = raw_line.rstrip("\n\r")
        for category, value in scan_line(line_text, config):
            if matches_any(value, config.allowlist):
                continue
            if is_whitelisted(category, value, config.whitelist):
                continue
            findings.append(Finding(
                category=category,
                value=value,
                file=rel_path,
                line=line_no,
                context=line_text.strip()[:120],
            ))

    return findings


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {
    "url":      "URL",
    "email":    "Email",
    "hostname": "Hostname",
    "ip":       "IP Address",
}

CATEGORY_ICONS = {
    "url":      "[URL]     ",
    "email":    "[EMAIL]   ",
    "hostname": "[HOST]    ",
    "ip":       "[IP]      ",
}


def print_text_report(findings: list[Finding]) -> None:
    if not findings:
        print("✓ No external references found.")
        return

    by_category: dict[str, list[Finding]] = {}
    for f in findings:
        by_category.setdefault(f.category, []).append(f)

    print(f"\n{'='*70}")
    print(f"  External reference scan — {len(findings)} finding(s)")
    print(f"{'='*70}\n")

    for cat in ("url", "email", "hostname", "ip"):
        items = by_category.get(cat, [])
        if not items:
            continue
        label = CATEGORY_LABELS[cat]
        print(f"  {label}s ({len(items)})")
        print(f"  {'-'*40}")
        for f in items:
            print(f"  {f.file}:{f.line}")
            print(f"    Value  : {f.value}")
            print(f"    Context: {f.context}")
            print()

    print(f"{'='*70}")
    print(f"  Total: {len(findings)} finding(s) in {len({f.file for f in findings})} file(s)")
    print(f"{'='*70}\n")


def print_json_report(findings: list[Finding]) -> None:
    data = [
        {
            "category": f.category,
            "value": f.value,
            "file": f.file,
            "line": f.line,
            "context": f.context,
        }
        for f in findings
    ]
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan a git repository for external URLs, emails, hostnames, and IPs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current directory, fail on any finding
  python scan_external_urls.py

  # Scan specific repo, skip test files, allow internal domain
  python scan_external_urls.py /path/to/repo --skip-tests --allow "mycompany\\.com"

  # CI pipeline: JSON output, fail on URL or email only
  python scan_external_urls.py --categories url email --format json

  # Load allowlist from file (one regex per line)
  python scan_external_urls.py --allow-file .scan-allowlist

  # Ignore all IP addresses (e.g. Ansible/infrastructure repos)
  python scan_external_urls.py --ignore-all-ips

  # Ignore specific IP addresses
  python scan_external_urls.py --ignore-ips 192.168.1.1 10.0.0.1

  # Load ignored IPs from file (one IP per line)
  python scan_external_urls.py --ignore-ips-file .scan-ignore-ips
""",
    )
    parser.add_argument(
        "repo", nargs="?", default=".",
        help="Path to the git repository root (default: current directory)",
    )
    parser.add_argument(
        "--categories", nargs="+",
        choices=["url", "email", "hostname", "ip"],
        default=["url", "email", "hostname", "ip"],
        metavar="CATEGORY",
        help="Categories to scan for: url email hostname ip (default: all)",
    )
    parser.add_argument(
        "--allow", nargs="*", default=[],
        metavar="PATTERN",
        help="Regex patterns to allow (e.g. 'localhost' 'example\\.com')",
    )
    parser.add_argument(
        "--allow-file", metavar="FILE",
        help="File with one allow-pattern per line (comments with # supported)",
    )
    parser.add_argument(
        "--skip", nargs="*", default=[],
        metavar="PATTERN",
        help="Regex path patterns to skip (e.g. 'docs/' 'fixtures/')",
    )
    parser.add_argument(
        "--skip-tests", action="store_true",
        help="Skip common test file/directory patterns",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        dest="output_format",
        help="Output format: text (default) or json",
    )
    parser.add_argument(
        "--no-fail", action="store_true",
        help="Always exit 0, even when findings are present",
    )
    parser.add_argument(
        "--ignore-all-ips", action="store_true",
        help="Ignore all IP addresses (useful for Ansible or infrastructure repos)",
    )
    parser.add_argument(
        "--ignore-ips", nargs="+", default=[],
        metavar="IP",
        help="IP addresses to ignore (e.g. '192.168.1.1' '10.0.0.1')",
    )
    parser.add_argument(
        "--ignore-ips-file", metavar="FILE",
        help="File with one IP address per line to ignore (comments with # supported)",
    )
    parser.add_argument(
        "--whitelist", metavar="FILE",
        help="JSON file with ip_ranges, hostnames, and email_domains to whitelist",
    )
    return parser


def load_allowlist_file(path: str) -> list[str]:
    patterns: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def load_whitelist_file(path: str) -> Whitelist:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    wl = Whitelist()
    for entry in data.get("ip_ranges", []):
        try:
            wl.ip_ranges.append(ipaddress.ip_network(entry, strict=False))
        except ValueError as exc:
            print(f"WARNING: Invalid IP range '{entry}' in whitelist: {exc}", file=sys.stderr)

    wl.hostnames = [h.lower().lstrip("*.") for h in data.get("hostnames", [])]
    wl.email_domains = [d.lower() for d in data.get("email_domains", [])]
    wl.urls = [u.lower() for u in data.get("urls", [])]
    return wl


def is_whitelisted(category: str, value: str, wl: Whitelist) -> bool:
    if category == "ip":
        try:
            addr = ipaddress.ip_address(value)
            return any(addr in net for net in wl.ip_ranges)
        except ValueError:
            return False

    if category == "hostname":
        host = value.lower()
        return any(host == h or host.endswith("." + h) for h in wl.hostnames)

    if category == "email":
        domain = value.split("@", 1)[-1].lower()
        return domain in wl.email_domains

    if category == "url":
        value_lower = value.lower()
        if any(value_lower.startswith(u) for u in wl.urls):
            return True
        m = re.match(r'https?://([^/\s:?#]+)', value, re.IGNORECASE)
        if m:
            host = m.group(1).lower()
            return any(host == h or host.endswith("." + h) for h in wl.hostnames)

    return False


def _find_default_whitelist(repo_path: str) -> str | None:
    candidate = os.path.join(repo_path, "whitelist.json")
    return candidate if os.path.isfile(candidate) else None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"ERROR: '{repo_path}' is not a git repository root.", file=sys.stderr)
        return 2

    allowlist = list(args.allow)
    if args.allow_file:
        try:
            allowlist.extend(load_allowlist_file(args.allow_file))
        except OSError as exc:
            print(f"ERROR: Cannot read allow-file: {exc}", file=sys.stderr)
            return 2

    ignore_ips = set(args.ignore_ips)
    if args.ignore_ips_file:
        try:
            ignore_ips.update(load_allowlist_file(args.ignore_ips_file))
        except OSError as exc:
            print(f"ERROR: Cannot read ignore-ips-file: {exc}", file=sys.stderr)
            return 2

    whitelist = Whitelist()
    whitelist_path = args.whitelist or _find_default_whitelist(repo_path)
    if whitelist_path:
        try:
            whitelist = load_whitelist_file(whitelist_path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: Cannot read whitelist file: {exc}", file=sys.stderr)
            return 2

    config = ScanConfig(
        repo_path=repo_path,
        allowlist=allowlist,
        skip_patterns=args.skip or [],
        categories=set(args.categories),
        skip_tests=args.skip_tests,
        output_format=args.output_format,
        no_fail=args.no_fail,
        ignore_ips=ignore_ips,
        ignore_all_ips=args.ignore_all_ips,
        whitelist=whitelist,
    )

    try:
        files = get_tracked_files(repo_path)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: git ls-files failed: {exc}", file=sys.stderr)
        return 2

    if config.output_format == "text":
        print(f"Scanning {len(files)} tracked file(s) in '{repo_path}' …")

    all_findings: list[Finding] = []
    for path in files:
        all_findings.extend(scan_file(path, config))

    if config.output_format == "json":
        print_json_report(all_findings)
    else:
        print_text_report(all_findings)

    if all_findings and not config.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

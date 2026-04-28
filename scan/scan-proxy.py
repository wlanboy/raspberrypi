#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import re
import glob
import socket
import xml.etree.ElementTree as ET

PROXY_KEYS = [
    'http_proxy', 'HTTP_PROXY',
    'https_proxy', 'HTTPS_PROXY',
    'ftp_proxy', 'FTP_PROXY',
    'no_proxy', 'NO_PROXY',
    'ALL_PROXY', 'all_proxy',
]

PROXY_PATTERN = re.compile(
    r'^\s*(export\s+)?(http_proxy|https_proxy|ftp_proxy|no_proxy|HTTP_PROXY|HTTPS_PROXY|FTP_PROXY|NO_PROXY|ALL_PROXY|all_proxy)\s*=\s*["\']?([^"\'#\n\r]+)["\']?',
    re.IGNORECASE
)

CONFIG_FILES = [
    '/etc/environment',
    '/etc/profile',
    '/etc/bashrc',
    '/etc/bash.bashrc',
    '/etc/sysconfig/proxy',
    '/etc/yum.conf',
    '/etc/dnf/dnf.conf',
    '/etc/wgetrc',
    '/etc/curlrc',
    os.path.expanduser('~/.bashrc'),
    os.path.expanduser('~/.bash_profile'),
    os.path.expanduser('~/.profile'),
    os.path.expanduser('~/.wgetrc'),
    os.path.expanduser('~/.curlrc'),
]

GLOB_PATTERNS = [
    '/etc/profile.d/*.sh',
    '/etc/profile.d/*.csh',
    '/etc/environment.d/*.conf',
]

MAVEN_SETTINGS_FILES = [
    os.path.expanduser('~/.m2/settings.xml'),
    '/etc/maven/settings.xml',
    '/usr/share/maven/conf/settings.xml',
    '/usr/local/maven/conf/settings.xml',
]

MAVEN_HOME_CANDIDATES = [
    os.environ.get('MAVEN_HOME', ''),
    os.environ.get('M2_HOME', ''),
]

ANSIBLE_CFG_FILES = [
    '/etc/ansible/ansible.cfg',
    os.path.expanduser('~/.ansible.cfg'),
    './ansible.cfg',
]

findings = {}


def add_finding(source, key, value):
    if source not in findings:
        findings[source] = []
    findings[source].append((key, value.strip()))


def check_env():
    for key in PROXY_KEYS:
        val = os.environ.get(key)
        if val:
            add_finding('ENV', key, val)


def scan_file_generic(path):
    try:
        with open(path, 'r') as f:
            for line in f:
                m = PROXY_PATTERN.match(line)
                if m:
                    add_finding(path, m.group(2), m.group(3))
    except (IOError, OSError):
        pass


def scan_yum_dnf(path):
    try:
        with open(path, 'r') as f:
            for line in f:
                stripped = line.strip()
                if re.match(r'^proxy(_username|_password)?\s*=', stripped):
                    parts = stripped.split('=', 1)
                    if len(parts) == 2:
                        add_finding(path, parts[0].strip(), parts[1].strip())
    except (IOError, OSError):
        pass


def scan_wget(path):
    try:
        with open(path, 'r') as f:
            for line in f:
                stripped = line.strip()
                if re.match(r'^(https?_proxy|ftp_proxy|no_proxy)\s*=', stripped, re.IGNORECASE):
                    parts = stripped.split('=', 1)
                    if len(parts) == 2:
                        add_finding(path, parts[0].strip(), parts[1].strip())
    except (IOError, OSError):
        pass


def scan_curl(path):
    try:
        with open(path, 'r') as f:
            for line in f:
                stripped = line.strip()
                if re.match(r'^proxy\s*=', stripped, re.IGNORECASE):
                    parts = stripped.split('=', 1)
                    if len(parts) == 2:
                        add_finding(path, 'proxy', parts[1].strip())
    except (IOError, OSError):
        pass


def scan_maven_settings(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        # handle optional namespace
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag.split('}')[0] + '}'
        proxies = root.find('{0}proxies'.format(ns))
        if proxies is None:
            return
        for proxy in proxies.findall('{0}proxy'.format(ns)):
            def txt(tag):
                el = proxy.find('{0}{1}'.format(ns, tag))
                return el.text.strip() if el is not None and el.text else ''
            active = txt('active')
            protocol = txt('protocol')
            host = txt('host')
            port = txt('port')
            username = txt('username')
            nonProxyHosts = txt('nonProxyHosts')
            if host:
                add_finding(path, 'proxy.host', host)
            if port:
                add_finding(path, 'proxy.port', port)
            if protocol:
                add_finding(path, 'proxy.protocol', protocol)
            if active:
                add_finding(path, 'proxy.active', active)
            if username:
                add_finding(path, 'proxy.username', username)
            if nonProxyHosts:
                add_finding(path, 'proxy.nonProxyHosts', nonProxyHosts)
    except (IOError, OSError, ET.ParseError):
        pass


def scan_ansible_cfg(path):
    try:
        with open(path, 'r') as f:
            for line in f:
                stripped = line.strip()
                # proxy-related keys people set in ansible.cfg
                if re.match(r'^(http_proxy|https_proxy|ftp_proxy|no_proxy|proxy)\s*=', stripped, re.IGNORECASE):
                    parts = stripped.split('=', 1)
                    if len(parts) == 2:
                        add_finding(path, parts[0].strip(), parts[1].strip())
                # MAVEN_OPTS or env vars embedded via [defaults] environment
                m = PROXY_PATTERN.match(stripped)
                if m:
                    add_finding(path, m.group(2), m.group(3))
    except (IOError, OSError):
        pass


def route_file(path):
    lower = path.lower()
    if lower.endswith('/yum.conf') or lower.endswith('/dnf.conf'):
        scan_yum_dnf(path)
    elif lower.endswith('wgetrc'):
        scan_wget(path)
    elif lower.endswith('curlrc'):
        scan_curl(path)
    else:
        scan_file_generic(path)


def collect_maven_files():
    candidates = list(MAVEN_SETTINGS_FILES)
    for home in MAVEN_HOME_CANDIDATES:
        if home:
            candidates.append(os.path.join(home, 'conf', 'settings.xml'))
    return candidates


def main():
    hostname = socket.gethostname()

    check_env()

    # shell / system files
    all_files = list(CONFIG_FILES)
    for pattern in GLOB_PATTERNS:
        all_files.extend(glob.glob(pattern))

    seen = set()
    for path in all_files:
        if path not in seen:
            seen.add(path)
            route_file(path)

    # maven
    for path in collect_maven_files():
        if path not in seen:
            seen.add(path)
            scan_maven_settings(path)

    # ansible
    for path in ANSIBLE_CFG_FILES:
        if path not in seen:
            seen.add(path)
            scan_ansible_cfg(path)

    print("=== PROXY SCAN REPORT: {0} ===".format(hostname))

    if not findings:
        print("RESULT: NO_PROXY_FOUND")
        return

    print("RESULT: PROXY_FOUND")
    for source in sorted(findings.keys()):
        for key, val in findings[source]:
            print("SOURCE={0} KEY={1} VALUE={2}".format(source, key, val))


if __name__ == '__main__':
    main()

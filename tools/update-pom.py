#!/usr/bin/env python3
"""
update-pom.py – Aktualisiert pom.xml auf die neuesten Releases,
prüft via Maven Central API, baut mit `mvn package -DskipTests`
und gibt eine fertige Commit-Message aus.
"""

import argparse
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

POM: Path  # wird in main() gesetzt
# Namespaces
NS = "http://maven.apache.org/POM/4.0.0"
ET.register_namespace("", NS)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")


# ---------------------------------------------------------------------------
# Maven Central lookup
# ---------------------------------------------------------------------------

MAVEN_METADATA_BASE = "https://repo1.maven.org/maven2"


def latest_release(group_id: str, artifact_id: str) -> str | None:
    """Liest maven-metadata.xml von repo1.maven.org – enthält alle Versionen
    und das <release>-Tag mit der tatsächlich neuesten stabilen Version."""
    group_path = group_id.replace(".", "/")
    url = f"{MAVEN_METADATA_BASE}/{group_path}/{artifact_id}/maven-metadata.xml"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "update-pom.py/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        metadata = ET.fromstring(content)

        # <release> ist die kanonische neueste stabile Version
        release = metadata.findtext("versioning/release")
        if release and not re.search(r"(SNAPSHOT|alpha|beta|rc|m\d+)", release, re.I):
            return release

        # Fallback: alle Versionen durchsuchen und Maximum ermitteln
        versions = []
        for v_el in metadata.findall("versioning/versions/version"):
            v = v_el.text
            if v and not re.search(r"(SNAPSHOT|alpha|beta|rc|m\d+)", v, re.I):
                versions.append(v)
        if not versions:
            return None

        def version_key(v: str) -> list[int]:
            try:
                return [int(x) for x in re.split(r"[.\-]", v) if x.isdigit()]
            except Exception:
                return []

        return max(versions, key=version_key)
    except Exception as exc:
        print(f"  [WARN] Lookup {group_id}:{artifact_id} fehlgeschlagen: {exc}")
        return None


# ---------------------------------------------------------------------------
# pom.xml parsen – Namespace-bewusstes ElementTree
# ---------------------------------------------------------------------------

def tag(local: str) -> str:
    return f"{{{NS}}}{local}"


def parse_pom(path: Path) -> ET.ElementTree:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(path, parser=parser)
    return tree


# ---------------------------------------------------------------------------
# Versionen extrahieren und patchen
# ---------------------------------------------------------------------------

def collect_and_update(tree: ET.ElementTree) -> list[dict]:
    """
    Geht durch parent, dependencies und plugins, fragt die neueste Version ab
    und patcht das Tree-Objekt in-place.
    Gibt eine Liste der vorgenommenen Änderungen zurück.
    """
    root = tree.getroot()
    updates = []

    # --- Parent ---
    parent_el = root.find(tag("parent"))
    if parent_el is not None:
        g = parent_el.findtext(tag("groupId"))
        a = parent_el.findtext(tag("artifactId"))
        v_el = parent_el.find(tag("version"))
        if g and a and v_el is not None:
            updates += _check_and_patch(g, a, v_el, "parent")

    # --- Dependencies ---
    for dep in root.iter(tag("dependency")):
        g = dep.findtext(tag("groupId"))
        a = dep.findtext(tag("artifactId"))
        v_el = dep.find(tag("version"))
        # Nur Dependencies mit expliziter Version (nicht managed)
        if g and a and v_el is not None and not v_el.text.startswith("${"):
            updates += _check_and_patch(g, a, v_el, "dependency")

    # --- Build-Plugins ---
    for plugin in root.iter(tag("plugin")):
        g = plugin.findtext(tag("groupId")) or "org.apache.maven.plugins"
        a = plugin.findtext(tag("artifactId"))
        v_el = plugin.find(tag("version"))
        if a and v_el is not None and not v_el.text.startswith("${"):
            updates += _check_and_patch(g, a, v_el, "plugin")

    return updates


def _check_and_patch(group_id, artifact_id, version_el, kind) -> list[dict]:
    old_version = version_el.text.strip()
    print(f"  Prüfe {group_id}:{artifact_id}  ({old_version})")
    new_version = latest_release(group_id, artifact_id)
    if not new_version:
        print(f"    -> kein Ergebnis, übersprungen")
        return []
    if new_version == old_version:
        print(f"    -> bereits aktuell ({old_version})")
        return []
    if _is_downgrade(old_version, new_version):
        print(f"    -> {new_version} wäre ein Downgrade, übersprungen")
        return []
    print(f"    -> Update: {old_version} → {new_version}")
    version_el.text = new_version
    return [{
        "kind": kind,
        "group": group_id,
        "artifact": artifact_id,
        "old": old_version,
        "new": new_version,
    }]


def _is_downgrade(old: str, new: str) -> bool:
    """Einfacher Versions-Vergleich – weist Downgrades zurück."""
    try:
        def parts(v):
            return [int(x) for x in re.split(r"[.\-]", v) if x.isdigit()]
        return parts(new) < parts(old)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# pom.xml schreiben (originale Formatierung so weit möglich erhalten)
# ---------------------------------------------------------------------------

def write_pom(tree: ET.ElementTree, path: Path) -> None:
    # ElementTree ergänzt keine XML-Deklaration automatisch
    ET.indent(tree, space="\t")
    tree.write(path, xml_declaration=True, encoding="UTF-8")
    # Schönheits-Korrektur: standalone-Attribut entfernen, das ET hinzufügt
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace(" standalone='no'", "")
    path.write_text(raw, encoding="utf-8")


# ---------------------------------------------------------------------------
# Maven-Build
# ---------------------------------------------------------------------------

def run_maven() -> bool:
    print("\nStarte Maven-Build: mvn package -DskipTests ...")
    result = subprocess.run(
        ["mvn", "package", "-DskipTests"],
        cwd=POM.parent,
        capture_output=False,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Commit-Message generieren
# ---------------------------------------------------------------------------

def build_commit_message(updates: list[dict]) -> str:
    if not updates:
        return "chore: no dependency updates"

    lines = ["pom updater: bump dependencies to latest releases", ""]
    for u in updates:
        coord = f"{u['group']}:{u['artifact']}"
        lines.append(f"- {coord}: {u['old']} → {u['new']}")

    lines += [
        "",
        "Verified with: mvn package -DskipTests",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    global POM
    parser = argparse.ArgumentParser(description="Aktualisiert pom.xml auf die neuesten Maven-Releases.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Verzeichnis mit der pom.xml (Standard: aktuelles Verzeichnis)",
    )
    args = parser.parse_args()
    POM = Path(args.directory).resolve() / "pom.xml"

    if not POM.exists():
        sys.exit(f"pom.xml nicht gefunden: {POM}")

    backup = POM.with_suffix(".xml.bak")
    shutil.copy2(POM, backup)
    print(f"Backup erstellt: {backup}\n")

    print("Lese pom.xml und prüfe Abhängigkeiten ...\n")
    tree = parse_pom(POM)
    updates = collect_and_update(tree)

    if not updates:
        print("\nKeine Updates verfügbar – pom.xml unverändert.")
        backup.unlink(missing_ok=True)
        return

    write_pom(tree, POM)
    print(f"\n{len(updates)} Update(s) in pom.xml geschrieben.")

    success = run_maven()

    if success:
        print("\nBuild erfolgreich.\n")
        backup.unlink(missing_ok=True)
        print("=" * 60)
        print("COMMIT MESSAGE")
        print("=" * 60)
        print(build_commit_message(updates))
        print("=" * 60)
    else:
        print("\nBuild FEHLGESCHLAGEN – pom.xml wird zurückgesetzt.")
        shutil.copy2(backup, POM)
        backup.unlink(missing_ok=True)
        print("\nFehlgeschlagene Updates:")
        for u in updates:
            print(f"  {u['group']}:{u['artifact']}  {u['old']} → {u['new']}")
        sys.exit(1)


if __name__ == "__main__":
    main()

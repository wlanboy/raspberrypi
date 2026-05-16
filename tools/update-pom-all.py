#!/usr/bin/env python3
"""
update-pom-all.py – Findet alle Java-Projekte (pom.xml) in einem Verzeichnis
und ruft update-pom.py für jedes auf.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "update-pom.py"


def find_pom_dirs(base: Path) -> list[Path]:
    return sorted(p.parent for p in base.rglob("pom.xml"))


def run_update(project_dir: Path) -> str:
    print(f"\n{'=' * 60}")
    print(f"📦 {project_dir}")
    print(f"{'=' * 60}")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_dir)],
    )
    if result.returncode == 0:
        return "ok"
    return "error"


def has_unpushed_commits(project_dir: Path) -> bool:
    result = subprocess.run(
        ["git", "log", "@{u}..HEAD", "--oneline"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aktualisiert pom.xml aller Java-Projekte in einem Verzeichnis."
    )
    parser.add_argument(
        "basedir",
        nargs="?",
        default=".",
        help="Basisverzeichnis mit Java-Projekten (Standard: aktuelles Verzeichnis)",
    )
    args = parser.parse_args()
    base = Path(args.basedir).resolve()

    if not base.is_dir():
        sys.exit(f"❌ Verzeichnis nicht gefunden: {base}")

    pom_dirs = find_pom_dirs(base)
    if not pom_dirs:
        sys.exit(f"❌ Keine pom.xml gefunden in: {base}")

    print(f"🔍 {len(pom_dirs)} Java-Projekt(e) gefunden in {base}\n")

    ok_dirs = []
    error_dirs = []
    for project_dir in pom_dirs:
        status = run_update(project_dir)
        if status == "ok":
            ok_dirs.append(project_dir)
        else:
            error_dirs.append(project_dir)

    push_dirs = [d for d in ok_dirs if has_unpushed_commits(d)]

    print(f"\n{'=' * 60}")
    print(f"📊 Zusammenfassung ({len(pom_dirs)} Projekt(e))")
    print(f"{'=' * 60}")

    if ok_dirs:
        print(f"\n✔ Erfolgreich ({len(ok_dirs)}):")
        for d in ok_dirs:
            print(f"   {d}")

    if error_dirs:
        print(f"\n❌ Fehlgeschlagen ({len(error_dirs)}):")
        for d in error_dirs:
            print(f"   {d}")

    if push_dirs:
        print(f"\n🚀 git push ausstehend ({len(push_dirs)} Projekt(e)):")
        for d in push_dirs:
            print(f"   {d}")
        print()
        answer = input("❓ git push für alle ausstehenden Projekte ausführen? [j/N]: ").strip().lower()
        if answer == "j":
            for d in push_dirs:
                print(f"\n📤 Pushing {d} ...")
                result = subprocess.run(["git", "push"], cwd=d)
                if result.returncode == 0:
                    print(f"✔ {d.name}")
                else:
                    print(f"❌ Fehler beim Push: {d}")

    if error_dirs:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import sys
import subprocess
import curses
from pathlib import Path

SATA_ROOT = "/mnt/sata"
SELECTION_FILE = Path.home() / ".update-stack-selection"


def find_compose_files():
    results = []
    base = Path(SATA_ROOT)
    if not base.exists():
        return results
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name == "lost+found":
            continue
        try:
            matches = list(entry.glob("docker-compose*.yml"))
            for compose in sorted(matches):
                results.append(str(compose))
        except PermissionError:
            pass
    return results


def load_selection():
    if SELECTION_FILE.exists():
        return set(SELECTION_FILE.read_text().splitlines())
    return set()


def save_selection(selected):
    SELECTION_FILE.write_text("\n".join(sorted(selected)))


def run_selection_tui(compose_dirs):
    selected = load_selection()

    def tui(stdscr):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        current = 0
        items = list(compose_dirs)
        checked = set(d for d in selected if d in items)

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            stdscr.addstr(0, 0, "Docker Compose Stacks - Auswahl (SPACE=toggle, A=alle, N=keine, ENTER=speichern, Q=abbrechen)", curses.A_BOLD)
            stdscr.addstr(1, 0, "-" * min(w - 1, 90))

            for i, path in enumerate(items):
                row = i + 2
                if row >= h - 1:
                    break
                mark = "[x]" if path in checked else "[ ]"
                line = f"  {mark} {path}"
                if i == current:
                    stdscr.addstr(row, 0, line[:w - 1], curses.color_pair(1))
                elif path in checked:
                    stdscr.addstr(row, 0, line[:w - 1], curses.color_pair(2))
                else:
                    stdscr.addstr(row, 0, line[:w - 1])

            status = f"  {len(checked)} von {len(items)} ausgewählt"
            stdscr.addstr(h - 1, 0, status, curses.color_pair(3))
            stdscr.refresh()

            key = stdscr.getch()
            if key == curses.KEY_UP and current > 0:
                current -= 1
            elif key == curses.KEY_DOWN and current < len(items) - 1:
                current += 1
            elif key == ord(" "):
                path = items[current]
                if path in checked:
                    checked.discard(path)
                else:
                    checked.add(path)
            elif key == ord("a") or key == ord("A"):
                checked = set(items)
            elif key == ord("n") or key == ord("N"):
                checked = set()
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                return checked
            elif key in (ord("q"), ord("Q"), 27):
                return None

    result = curses.wrapper(tui)
    return result


def ask_yes_no(prompt):
    answer = input(f"{prompt} [j/N] ").strip().lower()
    return answer in ("j", "ja", "y", "yes")


def run_pull_and_up(selected_dirs):
    if not selected_dirs:
        print("Keine Stacks ausgewählt.")
        return

    print(f"\n=== docker compose pull für {len(selected_dirs)} Stack(s) ===\n")
    failed_pull = []
    for path in sorted(selected_dirs):
        p = Path(path)
        print(f"-- {path}")
        result = subprocess.run(
            ["docker", "compose", "-f", p.name, "pull"],
            cwd=p.parent,
        )
        if result.returncode != 0:
            failed_pull.append(path)
        print()

    if failed_pull:
        print(f"WARNUNG: pull fehlgeschlagen für: {', '.join(failed_pull)}\n")

    if not ask_yes_no("docker compose up -d ausführen?"):
        print("Abgebrochen.")
        return

    print(f"\n=== docker compose up -d für {len(selected_dirs)} Stack(s) ===\n")
    for path in sorted(selected_dirs):
        p = Path(path)
        print(f"-- {path}")
        subprocess.run(
            ["docker", "compose", "-f", p.name, "up", "-d"],
            cwd=p.parent,
        )
        print()


def main():
    select_mode = "-s" in sys.argv

    compose_dirs = find_compose_files()
    if not compose_dirs:
        print(f"Keine docker-compose.yml Dateien unter {SATA_ROOT} gefunden.")
        sys.exit(1)

    if select_mode:
        result = run_selection_tui(compose_dirs)
        if result is None:
            print("Abgebrochen.")
            sys.exit(0)
        save_selection(result)
        print(f"{len(result)} Stack(s) gespeichert.")
        if not result:
            sys.exit(0)
        if not ask_yes_no("Jetzt pull + up -d ausführen?"):
            sys.exit(0)
        run_pull_and_up(result)
    else:
        selected = load_selection()
        active = [d for d in compose_dirs if d in selected]
        if not active:
            print("Keine gespeicherte Auswahl gefunden. Bitte zuerst mit -s auswählen.")
            sys.exit(1)
        print(f"Gespeicherte Auswahl: {len(active)} Stack(s)")
        for d in sorted(active):
            print(f"  {d}")
        print()
        run_pull_and_up(active)


if __name__ == "__main__":
    main()

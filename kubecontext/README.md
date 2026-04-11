# kubecontext

TUI zum Zusammenführen von kubectl-Contexts aus SSH-Hosts in die lokale `~/.kube/config`.

## Was es tut

1. Liest alle Hosts aus `~/.ssh/config`
2. Verbindet sich per SSH und liest `~/.kube/config` von jedem Host
3. Zeigt alle gefundenen Contexts in einer Tabelle an
4. Markiert, welche bereits lokal vorhanden sind
5. Merged ausgewählte Contexts in die lokale `~/.kube/config`

## Installation

```bash
uv sync
uv run pyright
uv run ruff check
```

## Starten

```bash
uv run python main.py
```

## Bedienung

| Taste | Aktion |
|-------|--------|
| `Space` | Zeile auswählen / abwählen |
| `A` | Alle NEW-Contexts auswählen |
| `N` | Alle abwählen |
| `M` | Ausgewählte mergen |
| `Q` | Beenden |

## Status-Anzeige

| Symbol | Status | Bedeutung |
|--------|--------|-----------|
| `✓` grün | NEW | Noch nicht lokal vorhanden — vorausgewählt |
| `○` gedimmt | EXISTS (rename) | Name bereits vergeben, anderer Server — wird beim Merge mit `-<host>` umbenannt |
| `—` gedimmt | SAME — skip | Identisch lokal vorhanden — nicht auswählbar |
| `—` gedimmt | UNREACHABLE | Host nicht erreichbar oder kein `~/.kube/config` |

## Merge-Verhalten

- Vor jedem Schreiben wird `~/.kube/config` nach `~/.kube/config.backup` gesichert
- Contexts mit identischer Server-URL werden nie doppelt eingetragen
- Bei Namenskollisionen wird `-<hostname>` angehängt
- Nach einem Merge aktualisiert sich die Tabelle automatisch
- Mehrere Merges hintereinander sind möglich

## Voraussetzungen

- SSH-Zugang zu den Hosts ohne Passwort (Key-Auth oder `ssh-agent`)
- `~/.kube/config` auf den Remote-Hosts vorhanden
- Python >= 3.12

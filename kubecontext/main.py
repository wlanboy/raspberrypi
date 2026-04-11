"""
Kube Context Merger TUI

Reads SSH hosts from ~/.ssh/config, fetches ~/.kube/config from each
remote host via SSH, and lets you select which contexts to merge into
your local ~/.kube/config.

Status legend:
  NEW     — context not in local config (pre-selected)
  EXISTS  — same name, different server (not pre-selected, can be merged
             with -<host> suffix)
  SAME    — identical to local entry (disabled, nothing to do)
  ERROR   — host unreachable or no kube config found
"""

from __future__ import annotations

import copy
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Footer, Header, Static


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SSHHost:
    name: str
    hostname: str
    user: str = ""
    port: int = 22
    identity_file: Optional[str] = None


@dataclass
class RemoteContext:
    context_name: str
    cluster_name: str
    cluster_server: str
    user_name: str
    namespace: Optional[str]
    source_host: str
    # raw dicts for merging
    raw_cluster: dict = field(default_factory=dict)
    raw_context: dict = field(default_factory=dict)
    raw_user: dict = field(default_factory=dict)
    # determined after comparison with local config
    status: str = "NEW"   # NEW | EXISTS | SAME


# ---------------------------------------------------------------------------
# SSH config parser
# ---------------------------------------------------------------------------

def parse_ssh_config(config_path: Path) -> list[SSHHost]:
    hosts: list[SSHHost] = []
    if not config_path.exists():
        return hosts

    current: Optional[SSHHost] = None
    with open(config_path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            key, value = parts[0].lower(), parts[1].strip()

            if key == "host":
                # Skip wildcard / match-all patterns
                if any(ch in value for ch in ("*", "?", "!")):
                    current = None
                    continue
                current = SSHHost(name=value, hostname=value)
                hosts.append(current)
            elif current is not None:
                if key == "hostname":
                    current.hostname = value
                elif key == "user":
                    current.user = value
                elif key == "port":
                    try:
                        current.port = int(value)
                    except ValueError:
                        pass
                elif key == "identityfile":
                    current.identity_file = value

    return hosts


# ---------------------------------------------------------------------------
# Remote kube config fetcher
# ---------------------------------------------------------------------------

def fetch_remote_kube_config(host: SSHHost) -> Optional[str]:
    """Return raw YAML string of ~/.kube/config from host, or None."""
    cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
    ]
    if host.port != 22:
        cmd += ["-p", str(host.port)]
    if host.identity_file:
        cmd += ["-i", host.identity_file]
    target = f"{host.user}@{host.hostname}" if host.user else host.hostname
    cmd += [target, "cat ~/.kube/config"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Kube config helpers
# ---------------------------------------------------------------------------

def parse_remote_contexts(yaml_text: str, source_host: str) -> list[RemoteContext]:
    contexts: list[RemoteContext] = []
    try:
        cfg = yaml.safe_load(yaml_text)
        if not cfg:
            return contexts
        clusters = {c["name"]: c.get("cluster", {}) for c in cfg.get("clusters") or []}
        users = {u["name"]: u.get("user", {}) for u in cfg.get("users") or []}

        for ctx in cfg.get("contexts") or []:
            ctx_data = ctx.get("context") or {}
            cluster_name = ctx_data.get("cluster", "")
            user_name = ctx_data.get("user", "")
            cluster = clusters.get(cluster_name, {})

            contexts.append(RemoteContext(
                context_name=ctx["name"],
                cluster_name=cluster_name,
                cluster_server=cluster.get("server", ""),
                user_name=user_name,
                namespace=ctx_data.get("namespace"),
                source_host=source_host,
                raw_cluster={"name": cluster_name, "cluster": cluster},
                raw_context={"name": ctx["name"], "context": ctx_data},
                raw_user={"name": user_name, "user": users.get(user_name, {})},
            ))
    except Exception:
        pass
    return contexts


def load_local_kube_config() -> dict:
    path = Path.home() / ".kube" / "config"
    if path.exists():
        with open(path) as fh:
            return yaml.safe_load(fh) or _empty_config()
    return _empty_config()


def _empty_config() -> dict:
    return {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [],
        "contexts": [],
        "users": [],
        "preferences": {},
        "current-context": "",
    }


def local_cluster_servers(local_cfg: dict) -> set[str]:
    """Return set of cluster server URLs already in local config."""
    return {
        c.get("cluster", {}).get("server", "")
        for c in local_cfg.get("clusters") or []
    }


def local_context_signatures(local_cfg: dict) -> dict[str, str]:
    """Return {context_name: cluster_server} for all local contexts."""
    clusters = {c["name"]: c.get("cluster", {}) for c in local_cfg.get("clusters") or []}
    result: dict[str, str] = {}
    for ctx in local_cfg.get("contexts") or []:
        ctx_data = ctx.get("context") or {}
        cluster = clusters.get(ctx_data.get("cluster", ""), {})
        result[ctx["name"]] = cluster.get("server", "")
    return result


def classify_contexts(
    remote: list[RemoteContext], local_cfg: dict
) -> None:
    """Set .status on each RemoteContext in-place."""
    local_servers = local_cluster_servers(local_cfg)
    sigs = local_context_signatures(local_cfg)
    for ctx in remote:
        # Identical server already present regardless of context name → SAME
        if ctx.cluster_server and ctx.cluster_server in local_servers:
            ctx.status = "SAME"
        elif ctx.context_name not in sigs:
            ctx.status = "NEW"
        elif sigs[ctx.context_name] == ctx.cluster_server:
            ctx.status = "SAME"
        else:
            ctx.status = "EXISTS"


def merge_into_local(
    selected: list[RemoteContext], local_cfg: dict
) -> dict:
    """Return a new local config with selected contexts merged in."""
    cfg = copy.deepcopy(local_cfg)
    cfg.setdefault("clusters", [])
    cfg.setdefault("contexts", [])
    cfg.setdefault("users", [])

    existing_clusters = {c["name"] for c in cfg["clusters"]}
    existing_users = {u["name"] for u in cfg["users"]}
    existing_contexts = {c["name"] for c in cfg["contexts"]}
    # Track servers already present to skip true duplicates across hosts
    existing_servers = {
        c.get("cluster", {}).get("server", "") for c in cfg["clusters"]
    }

    for ctx in selected:
        # Skip if the exact same cluster server is already present
        if ctx.cluster_server and ctx.cluster_server in existing_servers:
            continue

        cluster_name = ctx.cluster_name
        user_name = ctx.user_name
        context_name = ctx.context_name

        # Rename on name collision
        if cluster_name in existing_clusters:
            cluster_name = f"{cluster_name}-{ctx.source_host}"
        if user_name in existing_users:
            user_name = f"{user_name}-{ctx.source_host}"
        if context_name in existing_contexts:
            context_name = f"{context_name}-{ctx.source_host}"

        cluster_entry = copy.deepcopy(ctx.raw_cluster)
        cluster_entry["name"] = cluster_name
        cfg["clusters"].append(cluster_entry)
        existing_clusters.add(cluster_name)
        existing_servers.add(ctx.cluster_server)

        user_entry = copy.deepcopy(ctx.raw_user)
        user_entry["name"] = user_name
        cfg["users"].append(user_entry)
        existing_users.add(user_name)

        context_entry = copy.deepcopy(ctx.raw_context)
        context_entry["name"] = context_name
        context_entry["context"]["cluster"] = cluster_name
        context_entry["context"]["user"] = user_name
        cfg["contexts"].append(context_entry)
        existing_contexts.add(context_name)

    return cfg


def save_local_kube_config(cfg: dict) -> Optional[Path]:
    """Save config, backing up the old file first. Returns backup path."""
    path = Path.home() / ".kube" / "config"
    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Optional[Path] = None
    if path.exists():
        backup = path.with_suffix(".backup")
        shutil.copy2(path, backup)
    with open(path, "w") as fh:
        yaml.dump(cfg, fh, default_flow_style=False, allow_unicode=True)
    return backup


# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------

CHECK_ON  = "[bold green]✓[/bold green]"
CHECK_OFF = "[dim]○[/dim]"
CHECK_NA  = "[dim]—[/dim]"   # SAME / ERROR rows — not selectable

STATUS_STYLE = {
    "NEW": "bold green",
    "EXISTS": "bold yellow",
    "SAME": "dim",
    "ERROR": "bold red",
}

STATUS_LABEL = {
    "NEW": "NEW",
    "EXISTS": "EXISTS (rename)",
    "SAME": "SAME — skip",
    "ERROR": "UNREACHABLE",
}


class StatusBar(Static):
    message: reactive[str] = reactive("")

    def render(self) -> str:
        return self.message


class KubeContextApp(App):
    CSS = """
    Screen {
        background: $surface;
    }

    #status-bar {
        height: 1;
        background: $boost;
        color: $text-muted;
        padding: 0 1;
    }

    #table-container {
        height: 1fr;
        border: solid $primary-darken-2;
        margin: 1 1 0 1;
    }

    DataTable {
        height: 1fr;
    }

    #bottom-bar {
        height: 3;
        align: center middle;
        margin: 0 1 1 1;
    }

    #btn-merge {
        margin: 0 1;
    }

    #btn-quit {
        margin: 0 1;
    }

    #legend {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_row", "Toggle", show=True),
        Binding("a", "select_all", "Select all NEW", show=True),
        Binding("n", "deselect_all", "Deselect all", show=True),
        Binding("m", "merge", "Merge", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_contexts: list[RemoteContext] = []
        # row_key -> selected bool
        self._selected: dict[str, bool] = {}
        self._local_cfg: dict = {}
        self._merging = False  # guard against concurrent double-click

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield StatusBar(id="status-bar")
        yield Static(
            "  SPACE toggle · A select-all NEW · N deselect-all · M merge · Q quit",
            id="legend",
        )
        with Vertical(id="table-container"):
            yield DataTable(id="ctx-table", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="bottom-bar"):
            yield Button("Merge selected", id="btn-merge", variant="success")
            yield Button("Quit", id="btn-quit", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#ctx-table", DataTable)
        for label, key in [
            ("  ", "check"), ("Host", "host"), ("Context", "context"),
            ("Cluster", "cluster"), ("Server", "server"),
            ("Namespace", "namespace"), ("Status", "status"),
        ]:
            table.add_column(label, key=key)
        self._local_cfg = load_local_kube_config()
        self._load_remote_contexts()

    # ------------------------------------------------------------------
    # Background loading
    # ------------------------------------------------------------------

    def _load_remote_contexts(self) -> None:
        self.run_worker(self._fetch_all, exclusive=True, thread=True)

    def _fetch_all(self) -> None:
        ssh_hosts = parse_ssh_config(Path.home() / ".ssh" / "config")
        total = len(ssh_hosts)

        for idx, host in enumerate(ssh_hosts, start=1):
            self.call_from_thread(
                self._set_status,
                f"Connecting [{idx}/{total}]: {host.name} ({host.hostname}) …",
            )
            yaml_text = fetch_remote_kube_config(host)
            if yaml_text is None:
                self.call_from_thread(self._append_error_row, host)
                continue

            contexts = parse_remote_contexts(yaml_text, host.name)
            classify_contexts(contexts, self._local_cfg)
            for ctx in contexts:
                self.call_from_thread(self._append_row, ctx)

        self.call_from_thread(
            self._set_status,
            f"Done. {len(self._all_contexts)} context(s) found across {total} host(s). "
            "Select contexts and press M or click Merge.",
        )

    # ------------------------------------------------------------------
    # Row helpers (must be called on the main thread)
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", StatusBar).message = msg

    def _append_row(self, ctx: RemoteContext) -> None:
        self._all_contexts.append(ctx)
        key = f"{ctx.source_host}::{ctx.context_name}"
        # Pre-select only NEW contexts
        selected = ctx.status == "NEW"
        self._selected[key] = selected

        table = self.query_one("#ctx-table", DataTable)
        check = CHECK_ON if selected else CHECK_OFF
        style = STATUS_STYLE.get(ctx.status, "")
        table.add_row(
            check,
            ctx.source_host,
            ctx.context_name,
            ctx.cluster_name,
            ctx.cluster_server,
            ctx.namespace or "",
            f"[{style}]{STATUS_LABEL.get(ctx.status, ctx.status)}[/{style}]",
            key=key,
        )

    def _append_error_row(self, host: SSHHost) -> None:
        table = self.query_one("#ctx-table", DataTable)
        key = f"{host.name}::__error__"
        self._selected[key] = False
        table.add_row(
            CHECK_NA,
            host.name,
            "—",
            "—",
            "—",
            "—",
            "[bold red]UNREACHABLE[/bold red]",
            key=key,
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_row(self) -> None:
        table = self.query_one("#ctx-table", DataTable)
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        key = str(cell_key.row_key.value)
        # Find the matching context; SAME and ERROR rows cannot be toggled
        ctx = next((c for c in self._all_contexts
                    if f"{c.source_host}::{c.context_name}" == key), None)
        if ctx is None or ctx.status == "SAME":
            return

        new_val = not self._selected.get(key, False)
        self._selected[key] = new_val
        check = CHECK_ON if new_val else CHECK_OFF
        table.update_cell(key, "check", check)

    def action_select_all(self) -> None:
        table = self.query_one("#ctx-table", DataTable)
        for ctx in self._all_contexts:
            if ctx.status == "NEW":
                key = f"{ctx.source_host}::{ctx.context_name}"
                self._selected[key] = True
                table.update_cell(key, "check", CHECK_ON)

    def action_deselect_all(self) -> None:
        table = self.query_one("#ctx-table", DataTable)
        for ctx in self._all_contexts:
            key = f"{ctx.source_host}::{ctx.context_name}"
            self._selected[key] = False
            marker = CHECK_NA if ctx.status in ("SAME", "ERROR") else CHECK_OFF
            try:
                table.update_cell(key, "check", marker)
            except Exception:
                pass

    def action_merge(self) -> None:
        self._do_merge()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-merge":
            self._do_merge()
        elif event.button.id == "btn-quit":
            self.exit()

    def _do_merge(self) -> None:
        if self._merging:
            return
        to_merge = [
            ctx for ctx in self._all_contexts
            if self._selected.get(f"{ctx.source_host}::{ctx.context_name}", False)
        ]
        if not to_merge:
            self._set_status("Nothing selected.")
            return

        self._merging = True
        new_cfg = merge_into_local(to_merge, self._local_cfg)
        backup = save_local_kube_config(new_cfg)
        self._local_cfg = new_cfg

        # Re-classify all contexts against the updated local config and
        # refresh every row in the table to reflect the new status.
        classify_contexts(self._all_contexts, self._local_cfg)
        table = self.query_one("#ctx-table", DataTable)
        for ctx in self._all_contexts:
            key = f"{ctx.source_host}::{ctx.context_name}"
            self._selected[key] = False
            style = STATUS_STYLE.get(ctx.status, "")
            table.update_cell(key, "check", CHECK_NA if ctx.status in ("SAME", "ERROR") else CHECK_OFF)
            table.update_cell(
                key, "status",
                f"[{style}]{STATUS_LABEL.get(ctx.status, ctx.status)}[/{style}]",
            )

        names = ", ".join(
            f"{c.context_name}@{c.source_host}" for c in to_merge
        )
        backup_msg = f" (backup: {backup})" if backup else ""
        self._set_status(
            f"Merged {len(to_merge)} context(s): {names}{backup_msg}"
        )
        self._merging = False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = KubeContextApp()
    app.run()


if __name__ == "__main__":
    main()

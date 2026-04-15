#!/usr/bin/env python3
"""
Prometheus Memory/Cardinality Analyzer
Findet Metriken, Labels und Label-Wert-Kombinationen mit dem höchsten
Speicherverbrauch (Cardinality = Anzahl unique Time Series).
"""

import base64
import json
import sys
import urllib.request
import urllib.parse
import ssl

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROMETHEUS_URL = "https://localhost:9090"
BASIC_AUTH_USER = "admin"
BASIC_AUTH_PASS = "secret"
TOP_N = 50  # Wie viele Top-Einträge anzeigen

# SSL-Verifikation deaktivieren (self-signed certs im LAN)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

_AUTH_HEADER = "Basic " + base64.b64encode(
    f"{BASIC_AUTH_USER.strip()}:{BASIC_AUTH_PASS.strip()}".encode("utf-8")
).decode("ascii")


def query(path: str, params: dict | None = None) -> dict:
    url = f"{PROMETHEUS_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": _AUTH_HEADER})
    with urllib.request.urlopen(req, context=ssl_ctx, timeout=60) as resp:
        return json.loads(resp.read())


def query_instant(promql: str) -> list:
    data = query("/api/v1/query", {"query": promql})
    if data.get("status") != "success":
        raise RuntimeError(f"Query fehlgeschlagen: {data}")
    return data["data"]["result"]


def get_label_names() -> list[str]:
    data = query("/api/v1/labels")
    return data.get("data", [])


def get_label_values(label: str) -> list[str]:
    data = query(f"/api/v1/label/{urllib.parse.quote(label)}/values")
    return data.get("data", [])



def get_tsdb_stats() -> dict:
    data = query("/api/v1/status/tsdb")
    return data.get("data", {})


def get_runtime_info() -> dict:
    data = query("/api/v1/status/runtimeinfo")
    return data.get("data", {})


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_table(rows: list[tuple], headers: tuple):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in col_widths))
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))


def main():
    print("Prometheus Cardinality & Memory Analyzer")
    print(f"Target: {PROMETHEUS_URL}")
    print(f"Auth:   {BASIC_AUTH_USER} / {'*' * len(BASIC_AUTH_PASS)}")
    print(f"Header: {_AUTH_HEADER}")

    # --- 1. Runtime Info ---
    separator("Runtime Info")
    try:
        rt = get_runtime_info()
        for k in ("storageRetention", "chunkCount", "timeSeriesCount", "corruptionCount"):
            if k in rt:
                print(f"  {k}: {rt[k]}")
    except Exception as e:
        print(f"  [!] Nicht verfügbar: {e}")

    # --- 2. TSDB Stats (Cardinality) ---
    separator("TSDB Cardinality Stats")
    try:
        stats = get_tsdb_stats()

        # Gesamtübersicht
        head = stats.get("headStats", {})
        if head:
            print(f"\n  Head Block:")
            for k, v in head.items():
                print(f"    {k}: {v:,}")

        # Top Metriken nach Anzahl Series
        top_metrics = stats.get("seriesCountByMetricName", [])[:TOP_N]
        if top_metrics:
            separator(f"Top {TOP_N} Metriken nach Anzahl Time Series")
            print_table(
                [(e["name"], f"{e['value']:,}") for e in top_metrics],
                ("Metric Name", "Series Count")
            )

        # Top Label Names nach Cardinality
        top_labels = stats.get("seriesCountByLabelName", [])[:TOP_N]
        if top_labels:
            separator(f"Top {TOP_N} Label Names nach Cardinality")
            print_table(
                [(e["name"], f"{e['value']:,}") for e in top_labels],
                ("Label Name", "Series Count")
            )

        # Top Label-Value Paare
        top_pairs = stats.get("seriesCountByFocusLabelValue", [])[:TOP_N]
        if top_pairs:
            separator(f"Top {TOP_N} Label-Value-Paare")
            print_table(
                [(e["name"], f"{e['value']:,}") for e in top_pairs],
                ("Label=Value", "Series Count")
            )

        # Top Metriken mit höchster Label-Cardinality
        top_label_count = stats.get("labelValueCountByLabelName", [])[:TOP_N]
        if top_label_count:
            separator(f"Top {TOP_N} Labels nach Anzahl unique Werte")
            print_table(
                [(e["name"], f"{e['value']:,}") for e in top_label_count],
                ("Label Name", "Unique Values")
            )

        # Memory-Chunks
        top_chunks = stats.get("memoryInBytesByLabelName", [])[:TOP_N]
        if top_chunks:
            separator(f"Top {TOP_N} Labels nach Speicherverbrauch (Bytes)")
            rows = []
            for e in top_chunks:
                mb = e["value"] / 1024 / 1024
                rows.append((e["name"], f"{e['value']:,}", f"{mb:.2f} MB"))
            print_table(rows, ("Label Name", "Bytes", "MB"))

    except Exception as e:
        print(f"  [!] TSDB Stats nicht verfügbar: {e}")
        print("      (Erfordert Prometheus >= 2.14)")

    # --- 3. Cardinality via PromQL ---
    separator("Cardinality via PromQL (count by __name__)")
    try:
        results = query_instant('topk(20, count by (__name__) ({__name__!=""}))')
        if results:
            rows = []
            for r in sorted(results, key=lambda x: -float(x["value"][1])):
                name = r["metric"].get("__name__", "?")
                count = int(float(r["value"][1]))
                rows.append((name, f"{count:,}"))
            print_table(rows, ("Metric Name", "Active Series"))
        else:
            print("  Keine Ergebnisse (ggf. zu viele Metriken für diese Query)")
    except Exception as e:
        print(f"  [!] PromQL-Query fehlgeschlagen: {e}")

    # --- 4. Label-Value Cardinality – alle Labels dynamisch ---
    separator("Label-Value Cardinality (alle Labels)")
    try:
        all_labels = get_label_names()
        rows = []
        for label in all_labels:
            try:
                values = get_label_values(label)
                if values:
                    rows.append((label, len(values), values[:5]))
            except Exception:
                pass
        if rows:
            print(f"\n  {'Label':<30} {'Unique Values':>15}  Beispiele")
            print(f"  {'-'*30}  {'-'*13}  {'-'*40}")
            for label, count, examples in sorted(rows, key=lambda x: -x[1])[:TOP_N]:
                ex = ", ".join(str(v) for v in examples[:5])
                print(f"  {label:<30} {count:>15,}  {ex}")
    except Exception as e:
        print(f"  [!] Label-Namen nicht abrufbar: {e}")

    # --- 5. Sample-Rate via PromQL ---
    separator("Ingestion Rate (Samples/sec)")
    try:
        results = query_instant('topk(10, rate(scrape_samples_scraped[5m]))')
        if results:
            rows = []
            for r in sorted(results, key=lambda x: -float(x["value"][1])):
                job = r["metric"].get("job", "?")
                inst = r["metric"].get("instance", "?")
                rate_val = float(r["value"][1])
                rows.append((job, inst, f"{rate_val:.1f}"))
            print_table(rows, ("Job", "Instance", "Samples/sec"))
    except Exception as e:
        print(f"  [!] Nicht verfügbar: {e}")

    # --- 6. Neue Series pro Scrape (Cardinality-Explosion erkennen) ---
    separator("Neue Series pro Scrape (scrape_series_added)")
    try:
        results = query_instant('topk(10, scrape_series_added)')
        if results:
            rows = []
            for r in sorted(results, key=lambda x: -float(x["value"][1])):
                job = r["metric"].get("job", "?")
                inst = r["metric"].get("instance", "?")
                added = int(float(r["value"][1]))
                rows.append((job, inst, f"{added:,}"))
            print_table(rows, ("Job", "Instance", "Series Added (last scrape)"))
        else:
            print("  metric scrape_series_added nicht verfügbar")
    except Exception as e:
        print(f"  [!] Nicht verfügbar: {e}")

    # --- 7. Anzahl Targets pro Job ---
    separator("Targets pro Job")
    try:
        results = query_instant('sum by (job) (up)')
        if results:
            rows = []
            for r in sorted(results, key=lambda x: -float(x["value"][1])):
                job = r["metric"].get("job", "?")
                count = int(float(r["value"][1]))
                rows.append((job, f"{count:,}"))
            print_table(rows, ("Job", "Active Targets"))
    except Exception as e:
        print(f"  [!] Nicht verfügbar: {e}")

    # --- 8. WAL + Disk + Symbol Table Speicher ---
    separator("Speicherverbrauch: WAL / Blocks / Symbol Table")
    storage_queries = [
        ("WAL Size",              "prometheus_tsdb_wal_storage_size_bytes"),
        ("Head Chunks (RAM)",     "prometheus_tsdb_head_chunks * 1"),
        ("Head Series",           "prometheus_tsdb_head_series"),
        ("Block Storage (Disk)",  "prometheus_tsdb_storage_blocks_bytes"),
        ("Symbol Table (RAM)",    "prometheus_tsdb_symbol_table_size_bytes"),
        ("Head Min Time",         "prometheus_tsdb_head_min_time / 1000"),
        ("Head Max Time",         "prometheus_tsdb_head_max_time / 1000"),
    ]
    for label, pql in storage_queries:
        try:
            results = query_instant(pql)
            if results:
                val = float(results[0]["value"][1])
                if "bytes" in label.lower() or "ram" in label.lower() or "wal" in label.lower() or "symbol" in label.lower() or "storage" in label.lower():
                    mb = val / 1024 / 1024
                    print(f"  {label:<25} {val:>15,.0f} bytes  ({mb:.1f} MB)")
                else:
                    print(f"  {label:<25} {val:>15,.0f}")
        except Exception:
            pass

    # --- 9. Chunks/Series Ratio (Speichereffizienz) ---
    separator("Chunks/Series Ratio (Speichereffizienz)")
    try:
        results = query_instant(
            'prometheus_tsdb_head_chunks / prometheus_tsdb_head_series'
        )
        if results:
            ratio = float(results[0]["value"][1])
            print(f"  Chunks pro Series: {ratio:.2f}")
            if ratio > 3:
                print("  [!] Hoch – viele kurze/unterbrochene Series oder lange Retention")
            else:
                print("  [OK] Normal")
    except Exception as e:
        print(f"  [!] Nicht verfügbar: {e}")

    # --- 10. Runtime Details ---
    separator("Runtime Details")
    try:
        rt = get_runtime_info()
        for k in ("goroutineCount", "GOMAXPROCS", "GOGC", "startTime", "lastConfigTime"):
            if k in rt:
                print(f"  {k}: {rt[k]}")
    except Exception as e:
        print(f"  [!] Nicht verfügbar: {e}")

    # --- 11. Health Status & OOM-Nähe ---
    separator("HEALTH STATUS & OOM-RISIKO")

    issues = []   # (severity, message)   severity: "KRITISCH" | "WARNUNG" | "OK"
    metrics = {}  # gesammelte Rohwerte für die Bewertung

    def fetch(promql: str) -> float | None:
        try:
            r = query_instant(promql)
            return float(r[0]["value"][1]) if r else None
        except Exception:
            return None

    # --- /healthz endpoint ---
    try:
        url = f"{PROMETHEUS_URL}/-/healthy"
        req = urllib.request.Request(url, headers={"Authorization": _AUTH_HEADER})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=5) as resp:
            healthy = resp.status == 200
    except Exception:
        healthy = False
    issues.append(("OK" if healthy else "KRITISCH", f"HTTP /-/healthy: {'OK' if healthy else 'NICHT ERREICHBAR'}"))

    # --- /ready endpoint ---
    try:
        url = f"{PROMETHEUS_URL}/-/ready"
        req = urllib.request.Request(url, headers={"Authorization": _AUTH_HEADER})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=5) as resp:
            ready = resp.status == 200
    except Exception:
        ready = False
    issues.append(("OK" if ready else "WARNUNG", f"HTTP /-/ready:  {'OK' if ready else 'NICHT BEREIT (Startup/Replay läuft?)'}"))

    # --- Go Heap (aktueller RAM-Verbrauch des Prozesses) ---
    heap_bytes = fetch("go_memstats_heap_inuse_bytes")
    alloc_bytes = fetch("go_memstats_alloc_bytes")
    sys_bytes = fetch("go_memstats_sys_bytes")
    if heap_bytes is not None:
        metrics["heap_mb"] = heap_bytes / 1024 / 1024
        metrics["alloc_mb"] = alloc_bytes / 1024 / 1024 if alloc_bytes else 0
        metrics["sys_mb"] = sys_bytes / 1024 / 1024 if sys_bytes else 0

    # --- cgroup / OS Speicherlimit erkennen ---
    # container_memory_limit_bytes falls node_exporter/cAdvisor läuft
    mem_limit = fetch('container_memory_limit_bytes{name="prometheus"}')
    if mem_limit is None:
        mem_limit = fetch('container_memory_limit_bytes{container="prometheus"}')
    # Fallback: node memory
    node_mem_total = fetch('node_memory_MemTotal_bytes')
    node_mem_avail = fetch('node_memory_MemAvailable_bytes')

    if mem_limit and mem_limit > 0 and heap_bytes:
        used_pct = heap_bytes / mem_limit * 100
        metrics["limit_mb"] = mem_limit / 1024 / 1024
        metrics["heap_pct_of_limit"] = used_pct
        if used_pct > 90:
            issues.append(("KRITISCH", f"Heap {used_pct:.1f}% des Container-Limits → OOM sehr wahrscheinlich!"))
        elif used_pct > 75:
            issues.append(("WARNUNG",  f"Heap {used_pct:.1f}% des Container-Limits → OOM-Risiko vorhanden"))
        else:
            issues.append(("OK",       f"Heap {used_pct:.1f}% des Container-Limits"))
    elif node_mem_avail and node_mem_total and heap_bytes:
        node_used_pct = (1 - node_mem_avail / node_mem_total) * 100
        metrics["node_mem_total_mb"] = node_mem_total / 1024 / 1024
        metrics["node_mem_avail_mb"] = node_mem_avail / 1024 / 1024
        metrics["node_mem_used_pct"] = node_used_pct
        if node_used_pct > 92:
            issues.append(("KRITISCH", f"Host-RAM {node_used_pct:.1f}% belegt – OOM-Killer aktiv möglich"))
        elif node_used_pct > 80:
            issues.append(("WARNUNG",  f"Host-RAM {node_used_pct:.1f}% belegt"))
        else:
            issues.append(("OK",       f"Host-RAM {node_used_pct:.1f}% belegt"))
    else:
        issues.append(("WARNUNG", "Kein Speicherlimit ermittelbar (kein cAdvisor / node_exporter?)"))

    # --- GC-Druck ---
    gc_duration = fetch("go_gc_duration_seconds{quantile='0.99'}")
    if gc_duration is not None:
        metrics["gc_p99_ms"] = gc_duration * 1000
        if gc_duration > 1.0:
            issues.append(("KRITISCH", f"GC p99 {gc_duration*1000:.0f}ms – extremer Speicherdruck"))
        elif gc_duration > 0.1:
            issues.append(("WARNUNG",  f"GC p99 {gc_duration*1000:.0f}ms – erhöhter Speicherdruck"))
        else:
            issues.append(("OK",       f"GC p99 {gc_duration*1000:.1f}ms – unauffällig"))

    # --- TSDB Korruption ---
    corrupt = fetch("prometheus_tsdb_head_series_not_found_total")
    if corrupt and corrupt > 0:
        issues.append(("WARNUNG", f"TSDB: {corrupt:.0f} Series 'not found' (mögliche Korruption)"))

    # --- WAL Replay / Head Truncation Fehler ---
    wal_errors = fetch("prometheus_tsdb_wal_corruptions_total")
    if wal_errors and wal_errors > 0:
        issues.append(("KRITISCH", f"WAL-Korruptionen: {wal_errors:.0f}"))

    # --- Scrape-Fehler ---
    scrape_fail = fetch("sum(up == 0)")
    scrape_total = fetch("count(up)")
    if scrape_fail is not None and scrape_total:
        fail_pct = scrape_fail / scrape_total * 100
        metrics["scrape_fail_pct"] = fail_pct
        if fail_pct > 20:
            issues.append(("KRITISCH", f"{scrape_fail:.0f}/{scrape_total:.0f} Targets DOWN ({fail_pct:.1f}%)"))
        elif scrape_fail > 0:
            issues.append(("WARNUNG",  f"{scrape_fail:.0f}/{scrape_total:.0f} Targets DOWN ({fail_pct:.1f}%)"))
        else:
            issues.append(("OK",       f"Alle {scrape_total:.0f} Targets UP"))

    # --- Ausgabe ---
    SEV_ORDER = {"KRITISCH": 0, "WARNUNG": 1, "OK": 2}
    issues.sort(key=lambda x: SEV_ORDER.get(x[0], 9))

    print()
    for sev, msg in issues:
        tag = {"KRITISCH": "[KRITISCH]", "WARNUNG": "[WARNUNG] ", "OK": "[OK]      "}.get(sev, sev)
        print(f"  {tag}  {msg}")

    print()
    if metrics.get("heap_mb"):
        print(f"  Heap in use:  {metrics['heap_mb']:>8.1f} MB")
    if metrics.get("alloc_mb"):
        print(f"  Alloc:        {metrics['alloc_mb']:>8.1f} MB")
    if metrics.get("sys_mb"):
        print(f"  Sys (vom OS): {metrics['sys_mb']:>8.1f} MB")
    if metrics.get("limit_mb"):
        print(f"  Limit:        {metrics['limit_mb']:>8.1f} MB  →  {metrics.get('heap_pct_of_limit', 0):.1f}% genutzt")
    if metrics.get("node_mem_total_mb"):
        print(f"  Host RAM:     {metrics['node_mem_total_mb']:>8.1f} MB total  /  {metrics['node_mem_avail_mb']:.1f} MB frei")
    if metrics.get("gc_p99_ms"):
        print(f"  GC p99:       {metrics['gc_p99_ms']:>8.1f} ms")

    worst = issues[0][0] if issues else "OK"
    summary = {"KRITISCH": "KRITISCH – sofortiger Handlungsbedarf!", "WARNUNG": "WARNUNG – beobachten", "OK": "Alles OK"}.get(worst, worst)
    print(f"\n  Gesamtstatus: {summary}")

    print("\nFertig.\n")


if __name__ == "__main__":
    main()

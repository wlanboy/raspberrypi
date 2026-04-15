#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prometheus Memory/Cardinality Analyzer
Findet Metriken, Labels und Label-Wert-Kombinationen mit dem hoechsten
Speicherverbrauch (Cardinality = Anzahl unique Time Series).
"""

from __future__ import print_function

import json
import ssl
import socket
import urllib
import urllib2
import httplib

PROMETHEUS_URL = "https://prometheus.gmk.lan:9090"
TOP_N = 50  # Wie viele Top-Eintraege anzeigen


# SSL-Verifikation deaktivieren (self-signed certs im LAN)
# Kompatibel mit Python 2.7.3 (kein ssl.create_default_context verfuegbar)
class _UnverifiedHTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(
            sock,
            key_file=self.key_file,
            cert_file=self.cert_file,
            cert_reqs=ssl.CERT_NONE
        )


class _UnverifiedHTTPSHandler(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_UnverifiedHTTPSConnection, req)


_opener = urllib2.build_opener(_UnverifiedHTTPSHandler())


def query(path, params=None):
    url = "{0}{1}".format(PROMETHEUS_URL, path)
    if params:
        url += "?" + urllib.urlencode(params)
    req = urllib2.Request(url)
    resp = _opener.open(req, timeout=60)
    return json.loads(resp.read())


def query_instant(promql):
    data = query("/api/v1/query", {"query": promql})
    if data.get("status") != "success":
        raise RuntimeError("Query fehlgeschlagen: {0}".format(data))
    return data["data"]["result"]


def get_label_names():
    data = query("/api/v1/labels")
    return data.get("data", [])


def get_label_values(label):
    data = query("/api/v1/label/{0}/values".format(urllib.quote(label)))
    return data.get("data", [])


def get_tsdb_stats():
    data = query("/api/v1/status/tsdb")
    return data.get("data", {})


def get_runtime_info():
    data = query("/api/v1/status/runtimeinfo")
    return data.get("data", {})


def separator(title):
    print("\n{0}".format('=' * 60))
    print("  {0}".format(title))
    print('=' * 60)


def print_table(rows, headers):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join("{{:<{0}}}".format(w) for w in col_widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in col_widths))
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))


def main():
    print("Prometheus Cardinality & Memory Analyzer")
    print("Target: {0}".format(PROMETHEUS_URL))

    # --- 1. Runtime Info ---
    separator("Runtime Info")
    try:
        rt = get_runtime_info()
        for k in ("storageRetention", "chunkCount", "timeSeriesCount", "corruptionCount"):
            if k in rt:
                print("  {0}: {1}".format(k, rt[k]))
    except Exception as e:
        print("  [!] Nicht verfuegbar: {0}".format(e))

    # --- 2. TSDB Stats (Cardinality) ---
    separator("TSDB Cardinality Stats")
    try:
        stats = get_tsdb_stats()

        # Gesamtuebersicht
        head = stats.get("headStats", {})
        if head:
            print("\n  Head Block:")
            for k, v in head.items():
                print("    {0}: {1:,}".format(k, v))

        # Top Metriken nach Anzahl Series
        top_metrics = stats.get("seriesCountByMetricName", [])[:TOP_N]
        if top_metrics:
            separator("Top {0} Metriken nach Anzahl Time Series".format(TOP_N))
            print_table(
                [(e["name"], "{0:,}".format(e['value'])) for e in top_metrics],
                ("Metric Name", "Series Count")
            )

        # Top Label Names nach Cardinality
        top_labels = stats.get("seriesCountByLabelName", [])[:TOP_N]
        if top_labels:
            separator("Top {0} Label Names nach Cardinality".format(TOP_N))
            print_table(
                [(e["name"], "{0:,}".format(e['value'])) for e in top_labels],
                ("Label Name", "Series Count")
            )

        # Top Label-Value Paare
        top_pairs = stats.get("seriesCountByFocusLabelValue", [])[:TOP_N]
        if top_pairs:
            separator("Top {0} Label-Value-Paare".format(TOP_N))
            print_table(
                [(e["name"], "{0:,}".format(e['value'])) for e in top_pairs],
                ("Label=Value", "Series Count")
            )

        # Top Labels nach unique Werte-Anzahl
        top_label_count = stats.get("labelValueCountByLabelName", [])[:TOP_N]
        if top_label_count:
            separator("Top {0} Labels nach Anzahl unique Werte".format(TOP_N))
            print_table(
                [(e["name"], "{0:,}".format(e['value'])) for e in top_label_count],
                ("Label Name", "Unique Values")
            )

        # Memory-Chunks
        top_chunks = stats.get("memoryInBytesByLabelName", [])[:TOP_N]
        if top_chunks:
            separator("Top {0} Labels nach Speicherverbrauch (Bytes)".format(TOP_N))
            rows = []
            for e in top_chunks:
                mb = e["value"] / 1024.0 / 1024.0
                rows.append((e["name"], "{0:,}".format(e['value']), "{0:.2f} MB".format(mb)))
            print_table(rows, ("Label Name", "Bytes", "MB"))

    except Exception as e:
        print("  [!] TSDB Stats nicht verfuegbar: {0}".format(e))
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
                rows.append((name, "{0:,}".format(count)))
            print_table(rows, ("Metric Name", "Active Series"))
        else:
            print("  Keine Ergebnisse (ggf. zu viele Metriken fuer diese Query)")
    except Exception as e:
        print("  [!] PromQL-Query fehlgeschlagen: {0}".format(e))

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
            print("\n  {0:<30} {1:>15}  Beispiele".format("Label", "Unique Values"))
            print("  {0}  {1}  {2}".format('-' * 30, '-' * 13, '-' * 40))
            for label, count, examples in sorted(rows, key=lambda x: -x[1])[:TOP_N]:
                ex = ", ".join(str(v) for v in examples[:5])
                print("  {0:<30} {1:>15,}  {2}".format(label, count, ex))
    except Exception as e:
        print("  [!] Label-Namen nicht abrufbar: {0}".format(e))

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
                rows.append((job, inst, "{0:.1f}".format(rate_val)))
            print_table(rows, ("Job", "Instance", "Samples/sec"))
    except Exception as e:
        print("  [!] Nicht verfuegbar: {0}".format(e))

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
                rows.append((job, inst, "{0:,}".format(added)))
            print_table(rows, ("Job", "Instance", "Series Added (last scrape)"))
        else:
            print("  metric scrape_series_added nicht verfuegbar")
    except Exception as e:
        print("  [!] Nicht verfuegbar: {0}".format(e))

    # --- 7. Anzahl Targets pro Job ---
    separator("Targets pro Job")
    try:
        results = query_instant('sum by (job) (up)')
        if results:
            rows = []
            for r in sorted(results, key=lambda x: -float(x["value"][1])):
                job = r["metric"].get("job", "?")
                count = int(float(r["value"][1]))
                rows.append((job, "{0:,}".format(count)))
            print_table(rows, ("Job", "Active Targets"))
    except Exception as e:
        print("  [!] Nicht verfuegbar: {0}".format(e))

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
                if ("bytes" in label.lower() or "ram" in label.lower()
                        or "wal" in label.lower() or "symbol" in label.lower()
                        or "storage" in label.lower()):
                    mb = val / 1024.0 / 1024.0
                    print("  {0:<25} {1:>15,.0f} bytes  ({2:.1f} MB)".format(label, val, mb))
                else:
                    print("  {0:<25} {1:>15,.0f}".format(label, val))
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
            print("  Chunks pro Series: {0:.2f}".format(ratio))
            if ratio > 3:
                print("  [!] Hoch - viele kurze/unterbrochene Series oder lange Retention")
            else:
                print("  [OK] Normal")
    except Exception as e:
        print("  [!] Nicht verfuegbar: {0}".format(e))

    # --- 10. Runtime Details ---
    separator("Runtime Details")
    try:
        rt = get_runtime_info()
        for k in ("goroutineCount", "GOMAXPROCS", "GOGC", "startTime", "lastConfigTime"):
            if k in rt:
                print("  {0}: {1}".format(k, rt[k]))
    except Exception as e:
        print("  [!] Nicht verfuegbar: {0}".format(e))

    # --- 11. Health Status & OOM-Naehe ---
    separator("HEALTH STATUS & OOM-RISIKO")

    issues = []   # (severity, message)   severity: "KRITISCH" | "WARNUNG" | "OK"
    metrics = {}  # gesammelte Rohwerte fuer die Bewertung

    def fetch(promql):
        try:
            r = query_instant(promql)
            return float(r[0]["value"][1]) if r else None
        except Exception:
            return None

    # --- /healthz endpoint ---
    try:
        url = "{0}/-/healthy".format(PROMETHEUS_URL)
        req = urllib2.Request(url)
        resp = _opener.open(req, timeout=5)
        healthy = resp.getcode() == 200
    except Exception:
        healthy = False
    issues.append(("OK" if healthy else "KRITISCH",
                   "HTTP /-/healthy: {0}".format("OK" if healthy else "NICHT ERREICHBAR")))

    # --- /ready endpoint ---
    try:
        url = "{0}/-/ready".format(PROMETHEUS_URL)
        req = urllib2.Request(url)
        resp = _opener.open(req, timeout=5)
        ready = resp.getcode() == 200
    except Exception:
        ready = False
    issues.append(("OK" if ready else "WARNUNG",
                   "HTTP /-/ready:  {0}".format("OK" if ready else "NICHT BEREIT (Startup/Replay laeuft?)")))

    # --- Go Heap (aktueller RAM-Verbrauch des Prozesses) ---
    heap_bytes = fetch("go_memstats_heap_inuse_bytes")
    alloc_bytes = fetch("go_memstats_alloc_bytes")
    sys_bytes = fetch("go_memstats_sys_bytes")
    if heap_bytes is not None:
        metrics["heap_mb"] = heap_bytes / 1024.0 / 1024.0
        metrics["alloc_mb"] = alloc_bytes / 1024.0 / 1024.0 if alloc_bytes else 0
        metrics["sys_mb"] = sys_bytes / 1024.0 / 1024.0 if sys_bytes else 0

    # --- cgroup / OS Speicherlimit erkennen ---
    mem_limit = fetch('container_memory_limit_bytes{name="prometheus"}')
    if mem_limit is None:
        mem_limit = fetch('container_memory_limit_bytes{container="prometheus"}')
    node_mem_total = fetch('node_memory_MemTotal_bytes')
    node_mem_avail = fetch('node_memory_MemAvailable_bytes')

    if mem_limit and mem_limit > 0 and heap_bytes:
        used_pct = heap_bytes / mem_limit * 100
        metrics["limit_mb"] = mem_limit / 1024.0 / 1024.0
        metrics["heap_pct_of_limit"] = used_pct
        if used_pct > 90:
            issues.append(("KRITISCH", "Heap {0:.1f}% des Container-Limits -> OOM sehr wahrscheinlich!".format(used_pct)))
        elif used_pct > 75:
            issues.append(("WARNUNG",  "Heap {0:.1f}% des Container-Limits -> OOM-Risiko vorhanden".format(used_pct)))
        else:
            issues.append(("OK",       "Heap {0:.1f}% des Container-Limits".format(used_pct)))
    elif node_mem_avail and node_mem_total and heap_bytes:
        node_used_pct = (1.0 - node_mem_avail / node_mem_total) * 100
        metrics["node_mem_total_mb"] = node_mem_total / 1024.0 / 1024.0
        metrics["node_mem_avail_mb"] = node_mem_avail / 1024.0 / 1024.0
        metrics["node_mem_used_pct"] = node_used_pct
        if node_used_pct > 92:
            issues.append(("KRITISCH", "Host-RAM {0:.1f}% belegt - OOM-Killer aktiv moeglich".format(node_used_pct)))
        elif node_used_pct > 80:
            issues.append(("WARNUNG",  "Host-RAM {0:.1f}% belegt".format(node_used_pct)))
        else:
            issues.append(("OK",       "Host-RAM {0:.1f}% belegt".format(node_used_pct)))
    else:
        issues.append(("WARNUNG", "Kein Speicherlimit ermittelbar (kein cAdvisor / node_exporter?)"))

    # --- GC-Druck ---
    gc_duration = fetch("go_gc_duration_seconds{quantile='0.99'}")
    if gc_duration is not None:
        metrics["gc_p99_ms"] = gc_duration * 1000
        if gc_duration > 1.0:
            issues.append(("KRITISCH", "GC p99 {0:.0f}ms - extremer Speicherdruck".format(gc_duration * 1000)))
        elif gc_duration > 0.1:
            issues.append(("WARNUNG",  "GC p99 {0:.0f}ms - erhoehter Speicherdruck".format(gc_duration * 1000)))
        else:
            issues.append(("OK",       "GC p99 {0:.1f}ms - unauffaellig".format(gc_duration * 1000)))

    # --- TSDB Korruption ---
    corrupt = fetch("prometheus_tsdb_head_series_not_found_total")
    if corrupt and corrupt > 0:
        issues.append(("WARNUNG", "TSDB: {0:.0f} Series 'not found' (moegliche Korruption)".format(corrupt)))

    # --- WAL Replay / Head Truncation Fehler ---
    wal_errors = fetch("prometheus_tsdb_wal_corruptions_total")
    if wal_errors and wal_errors > 0:
        issues.append(("KRITISCH", "WAL-Korruptionen: {0:.0f}".format(wal_errors)))

    # --- Scrape-Fehler ---
    scrape_fail = fetch("sum(up == 0)")
    scrape_total = fetch("count(up)")
    if scrape_fail is not None and scrape_total:
        fail_pct = scrape_fail / scrape_total * 100
        metrics["scrape_fail_pct"] = fail_pct
        if fail_pct > 20:
            issues.append(("KRITISCH", "{0:.0f}/{1:.0f} Targets DOWN ({2:.1f}%)".format(scrape_fail, scrape_total, fail_pct)))
        elif scrape_fail > 0:
            issues.append(("WARNUNG",  "{0:.0f}/{1:.0f} Targets DOWN ({2:.1f}%)".format(scrape_fail, scrape_total, fail_pct)))
        else:
            issues.append(("OK",       "Alle {0:.0f} Targets UP".format(scrape_total)))

    # --- Ausgabe ---
    SEV_ORDER = {"KRITISCH": 0, "WARNUNG": 1, "OK": 2}
    issues.sort(key=lambda x: SEV_ORDER.get(x[0], 9))

    print()
    for sev, msg in issues:
        tag = {"KRITISCH": "[KRITISCH]", "WARNUNG": "[WARNUNG] ", "OK": "[OK]      "}.get(sev, sev)
        print("  {0}  {1}".format(tag, msg))

    print()
    if metrics.get("heap_mb"):
        print("  Heap in use:  {0:>8.1f} MB".format(metrics['heap_mb']))
    if metrics.get("alloc_mb"):
        print("  Alloc:        {0:>8.1f} MB".format(metrics['alloc_mb']))
    if metrics.get("sys_mb"):
        print("  Sys (vom OS): {0:>8.1f} MB".format(metrics['sys_mb']))
    if metrics.get("limit_mb"):
        print("  Limit:        {0:>8.1f} MB  ->  {1:.1f}% genutzt".format(
            metrics['limit_mb'], metrics.get('heap_pct_of_limit', 0)))
    if metrics.get("node_mem_total_mb"):
        print("  Host RAM:     {0:>8.1f} MB total  /  {1:.1f} MB frei".format(
            metrics['node_mem_total_mb'], metrics['node_mem_avail_mb']))
    if metrics.get("gc_p99_ms"):
        print("  GC p99:       {0:>8.1f} ms".format(metrics['gc_p99_ms']))

    worst = issues[0][0] if issues else "OK"
    summary = {
        "KRITISCH": "KRITISCH - sofortiger Handlungsbedarf!",
        "WARNUNG":  "WARNUNG - beobachten",
        "OK":       "Alles OK"
    }.get(worst, worst)
    print("\n  Gesamtstatus: {0}".format(summary))

    print("\nFertig.\n")


if __name__ == "__main__":
    main()

# Monitoring von Java‑Prozessen unter Linux
(PID‑Liste, JAR‑Name, Heap‑Usage, CPU‑Usage, RAM‑Usage)

Diese Anleitung zeigt, wie du:
- Java‑Prozesse findest
- Heap‑Usage per jstat ausliest
- CPU‑ und RAM‑Usage per ps ermittelst
- Thread count

## Voraussetzungen
- Linux‑System
- jstat (Teil des JDK)
- Shell: Bash
- Java‑Prozesse, die .jar ausführen

## 1. Java‑Prozesse finden
```bash
ps ax | grep java | grep jar | awk '{print $1}'
```

## 2. Heap‑Usage eines Prozesses
```bash
jstat -gc <PID> | tail -n 1 | awk '{split($0,a," "); print a[3]+a[4]+a[6]+a[8]}'
```

## 3. CPU‑ und RAM‑Usage eines Prozesses
```bash
ps -p <PID> -o %cpu,%mem
```

## 3. Thread‑Count ermitteln
Der Thread‑Count eines Prozesses lässt sich über ps auslesen:
```bash
ps -p <PID> -o nlwp
```
nlwp = Number of Light Weight Processes → entspricht der Thread‑Anzahl.

## 4. Alles kombiniert: PID, JAR‑Name, Heap‑Usage, CPU, RAM
```bash
echo "PID      JAR-Datei                          Heap(KB)   CPU%     RAM%     Threads"
echo "--------------------------------------------------------------------------------------"

ps ax | grep java | grep jar | while read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    jar=$(echo "$line" | awk '{print $7}')

    # Heap usage (KB)
    heap=$(jstat -gc "$pid" | tail -n 1 | awk '{split($0,a," "); print a[3]+a[4]+a[6]+a[8]}')

    # CPU and RAM usage
    cpu=$(ps -p "$pid" -o %cpu --no-headers)
    mem=$(ps -p "$pid" -o %mem --no-headers)

    # Thread count
    threads=$(ps -p "$pid" -o nlwp --no-headers)

    printf "%-8s %-35s %-10s %-8s %-8s %-8s\n" "$pid" "$jar" "${heap}KB" "${cpu}%" "${mem}%" "$threads"
done
```
Beispielausgabe
```Code
PID      JAR-Datei                          Heap(KB)   CPU%     RAM%     Threads
--------------------------------------------------------------------------------------
5118     order-service.jar                  84256KB    12.3%    1.8%     54
6123     auth-service.jar                   65536KB     8.1%    1.2%     37
7344     payment-service.jar                91200KB    15.7%    2.4%     61
```

## 5. OOM‑Kills über dmesg finden
Der schnellste Weg:

```bash
dmesg | grep -i -E "killed process|out of memory|oom"
```

Oder nach dem Prozessnamen:
```bash
dmesg | grep -i java
```

Oder nach PID
```bash
dmesg | grep -i "5118"
```

## 6. OOM‑Kills über journalctl (systemd‑Systeme)
Wenn dein System systemd nutzt (Ubuntu, CentOS 7+, Debian 8+):

```bash
journalctl -k | grep -i -E "killed process|out of memory|oom"
```

Oder für einen bestimmten Zeitraum:
```bash
journalctl -k --since "2 hours ago" | grep -i oom
```

## 6. Check aller Prozesse für OOM_SCORE
```bash
#!/bin/bash

# Farben
RED="\e[31m"
YELLOW="\e[33m"
GREEN="\e[32m"
RESET="\e[0m"

echo -e "PID      NAME                           OOM_SCORE   OOM_SCORE_ADJ"
echo -e "---------------------------------------------------------------------"

# Temporäre Datei für sortierbare Daten
tmpfile=$(mktemp)

# Alle Prozesse durchgehen
for pid in /proc/[0-9]*; do
    pidnum=$(basename "$pid")

    # Prozessname
    [[ -f "$pid/comm" ]] || continue
    name=$(cat "$pid/comm")

    # OOM Score
    [[ -f "$pid/oom_score" ]] && score=$(cat "$pid/oom_score") || score="N/A"
    [[ -f "$pid/oom_score_adj" ]] && score_adj=$(cat "$pid/oom_score_adj") || score_adj="N/A"

    # Nur numerische Scores sortierbar
    if [[ "$score" =~ ^[0-9]+$ ]]; then
        echo "$score $pidnum $name $score_adj" >> "$tmpfile"
    fi
done

# Sortieren nach Score (absteigend)
sort -nr "$tmpfile" | while read -r score pidnum name score_adj; do

    # Farbe bestimmen
    if (( score >= 800 )); then
        color="$RED"
    elif (( score >= 200 )); then
        color="$YELLOW"
    else
        color="$GREEN"
    fi

    printf "%-8s %-30s ${color}%-12s %-12s${RESET}\n" "$pidnum" "$name" "$score" "$score_adj"
done
rm "$tmpfile"

./oom.sh
```
## Erklärung
Wenn einem Linux‑System der Arbeitsspeicher ausgeht, aktiviert der Kernel den OOM‑Killer (Out‑Of‑Memory Killer).
Damit entscheidet der Kernel, welcher Prozess beendet wird, um Speicher freizugeben.

Dafür nutzt Linux zwei wichtige Werte:
- oom_score
- oom_score_adj

### oom_score — Wie wahrscheinlich ein Prozess gekillt wird
oom_score ist ein vom Kernel berechneter, dynamischer Wert.
Er zeigt an, wie wahrscheinlich es ist, dass ein Prozess vom OOM‑Killer beendet wird.

Eigenschaften:
- Wertebereich: 0 bis 1000
- Je höher der Wert, desto wahrscheinlicher wird der Prozess gekillt
- Wird automatisch vom Kernel berechnet

Hängt ab von:
- tatsächlicher RAM‑Nutzung (RSS)
- virtuellem Speicherverbrauch
- Priorität des Prozesses
- cgroup‑Limits (z. B. in Containern)
- allgemeinem Speicherstress des Systems

### Interpretation:
oom_score	Bedeutung
- 0	Sehr geringe Wahrscheinlichkeit
- 1–199	Unkritisch
- 200–799	Mittel
- 800–1000	Sehr hoch — potenzielles OOM‑Opfer

### oom_score_adj — Manuelle Gewichtung des OOM‑Risikos
oom_score_adj ist ein statischer, manuell gesetzter Wert, mit dem Administratoren oder Programme beeinflussen können, wie der Kernel einen Prozess bewertet.

Eigenschaften:
- Wertebereich: -1000 bis +1000
- Je niedriger der Wert, desto geschützter ist der Prozess
- Je höher der Wert, desto gefährdeter
- Wird vor der Berechnung des finalen oom_score berücksichtigt

### Interpretation:
oom_score_adj	Bedeutung
- -1000	Prozess ist vollständig geschützt (niemals OOM‑Kill)
- -500	Stark geschützt
- 0	Standardverhalten
- +500	Erhöhtes Risiko
- +1000	Prozess wird bevorzugt gekillt

## 7. OOM‑Kills in Kubernetes (falls relevant)
```bash
kubectl describe pod <podname> | grep -i oom
```


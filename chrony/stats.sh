#!/bin/bash

# Erzwinge Punkt statt Komma für Berechnungen
export LC_NUMERIC=C

LOG_FILE="/var/log/chrony/statistics.log"
SAMPLES=100

if [ ! -f "$LOG_FILE" ]; then
    echo "Fehler: $LOG_FILE nicht gefunden!"
    exit 1
fi

echo "----------------------------------------------------------"
echo "Chrony GPS Statistik Analyse (Letzte $SAMPLES Proben)"
echo "----------------------------------------------------------"

# Extrahiere Daten und berechne Durchschnittswerte
# Wir nutzen direkt die absolute Abweichung für den Offset
STATS=$(grep "GPS" "$LOG_FILE" | tail -n $SAMPLES | awk '{
    abs_off = ($4 < 0 ? -$4 : $4); 
    sum_off += abs_off; 
    sum_sd += $5; 
    count++;
} 
END {
    if (count > 0) 
        printf "%.6f %.6f %d", sum_off/count, sum_sd/count, count;
}')

# Werte aus dem String extrahieren
AVG_OFFSET=$(echo $STATS | cut -d' ' -f1)
AVG_STDEV=$(echo $STATS | cut -d' ' -f2)
COUNT=$(echo $STATS | cut -d' ' -f3)

if [ -z "$COUNT" ] || [ "$COUNT" -eq 0 ]; then
    echo "Keine GPS Daten im Log gefunden."
    exit 1
fi

# Umrechnung in Millisekunden
OFFSET_MS=$(echo "$AVG_OFFSET * 1000" | bc -l)
STDEV_MS=$(echo "$AVG_STDEV * 1000" | bc -l)

echo "Anzahl Proben: $COUNT"
printf "Durchschn. Abweichung (Offset): %.3f ms\n" "$OFFSET_MS"
printf "Durchschn. Jitter (Std Dev):    %.3f ms\n" "$STDEV_MS"
echo "----------------------------------------------------------"

# Bewertung & Empfehlung
echo -n "Bewertung: "
if (( $(echo "$OFFSET_MS < 0.5" | bc -l) )); then
    echo "EXZELLENT (Perfekt kalibriert)"
    echo "----------------------------------------------------------"
    echo "EMPFEHLUNG: Keine Änderungen nötig. Das System läuft optimal."
elif (( $(echo "$OFFSET_MS < 1.5" | bc -l) )); then
    echo "GUT (Stabil im Betrieb)"
    echo "----------------------------------------------------------"
    echo "EMPFEHLUNG: Dein GPS hinkt minimal. Erhöhe den 'offset' in"
    echo "der chrony.conf um ca. 0.0005 bis 0.001 für Latenzoptimierung."
else
    echo "OPTIMIERUNGSBEDARF (Offset-Korrektur empfohlen)"
    echo "----------------------------------------------------------"
    echo "EMPFEHLUNG: Der Offset ist zu hoch (> 1.5 ms)."
    echo "Passe den 'offset' Wert in der chrony.conf deutlich an."
fi

if (( $(echo "$STDEV_MS > 5.0" | bc -l) )); then
    echo "HINWEIS: Hoher Jitter gemessen. 'filter' könnte helfen."
fi
echo "----------------------------------------------------------"
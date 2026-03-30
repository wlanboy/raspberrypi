# Lokales LLM auf dem Chromebook (Intel N150, 16 GB RAM)

Diese Anleitung richtet einen lokalen LLM-Chat im Terminal auf einem Chromebook mit
Intel N150 ein. Die Inferenz läuft rein per CPU — keine GPU nötig.
Mit 16 GB RAM sind Modelle bis ca. 7B Parameter (Q4-Quantisierung) sinnvoll nutzbar.

---

## Inhaltsverzeichnis

1. [Linux (Crostini) aktivieren](#1-linux-crostini-aktivieren)
2. [Ollama installieren](#2-ollama-installieren)
3. [Modell laden und starten](#3-modell-laden-und-starten)
4. [Empfohlene Modelle für den N150](#4-empfohlene-modelle-für-den-n150)
5. [Tipps & Fehlerbehebung](#5-tipps--fehlerbehebung)

---

## 1. Linux (Crostini) aktivieren

ChromeOS enthält eine integrierte Linux-VM (Debian-basiert).

**Einstellungen → Erweitert → Entwickler → Linux-Entwicklungsumgebung → Aktivieren**

Empfohlene Einstellungen:
- **Speicher:** mindestens 6 GB (für 7B-Modelle)
- **Speicherplatz:** mindestens 20 GB (Modelle sind 2–5 GB groß)

System aktualisieren:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 2. Ollama installieren

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Ollama startet automatisch als Hintergrunddienst. Status prüfen:

```bash
ollama --version
systemctl --user status ollama
```

### Autostart deaktivieren

```bash
systemctl --user disable ollama
systemctl --user stop ollama
```

Ollama dann bei Bedarf manuell starten:

```bash
ollama serve &
```

Oder als Hintergrundprozess mit Log:

```bash
ollama serve > /tmp/ollama.log 2>&1 &
```

---

## 3. Modell laden und starten

### Chat starten

```bash
ollama run phi4-mini
```

Beim ersten Start wird das Modell heruntergeladen. Danach öffnet sich direkt eine
Kommandozeilen-Chat-Sitzung. Beenden mit `/bye` oder `Strg+D`.

### Nur herunterladen

```bash
ollama pull phi4-mini
```

### Nützliche Befehle

```bash
ollama list              # Lokale Modelle anzeigen
ollama rm phi4-mini      # Modell löschen (Speicher freigeben)
ollama show phi4-mini    # Modell-Infos anzeigen
```

### Mehrere Modelle vergleichen

```bash
ollama run qwen2.5:3b
ollama run gemma3:4b
```

### Im Chat nützliche Befehle

```
/? oder /help    Hilfe anzeigen
/set verbose     Tokens/s und weitere Stats einblenden
/bye             Chat beenden
```

---

## 4. Empfohlene Modelle für den N150

Der N150 hat 4 E-Cores (kein AVX-512) und keine dedizierte GPU.
Ollama lädt automatisch die für die CPU optimierte GGUF-Variante (llama.cpp).

| Modell | Größe | ~tok/s | Stärken |
|---|---|---|---|
| `phi4-mini` | 2,5 GB | 8–12 | Beste Qualität/Größe-Ratio; Reasoning, Deutsch |
| `qwen2.5:3b` | 2 GB | 10–14 | Stark mehrsprachig (DE/EN/ZH), Coding |
| `qwen2.5:7b` | 4,7 GB | 3–5 | Hohe Qualität, langsamer |
| `gemma3:4b` | 3,3 GB | 6–10 | Gutes Deutsch, Google-Qualität |
| `llama3.2:3b` | 2 GB | 10–15 | Schnell, starkes Englisch |
| `llama3.2:1b` | 1,3 GB | 20–30 | Maximum Geschwindigkeit, einfache Aufgaben |
| `deepseek-r1:1.5b` | 1,1 GB | 20–28 | Reasoning-Modell, zeigt Denkschritte |
| `deepseek-r1:7b` | 4,7 GB | 3–5 | Starkes Reasoning, langsamer |
| `mistral:7b` | 4,1 GB | 4–6 | Solide Allround-Qualität |
| `smollm2:1.7b` | 1 GB | 25–35 | Kleinstes brauchbares Modell |

> Geschwindigkeiten sind Richtwerte auf dem N150 – abhängig von RAM-Auslastung
> und Hintergrundprozessen der Linux-VM.

**Einstiegsempfehlung:** `phi4-mini` oder `qwen2.5:3b` — gutes Gleichgewicht
zwischen Qualität und Geschwindigkeit auf der verfügbaren Hardware.

---

## 5. Tipps & Fehlerbehebung

### RAM und CPU während der Inferenz beobachten

```bash
# In einem zweiten Terminal-Tab
watch -n 1 free -h
top
```

Alle 4 Kerne bei ~100 % während der Textgenerierung ist normal.
Wenn `available` unter 500 MB fällt → kleineres Modell wählen.

### Speicherplatz prüfen

```bash
df -h ~
```

### Ollama-Logs anzeigen

```bash
journalctl --user -u ollama -f
```

### Häufige Probleme

| Problem | Lösung |
|---|---|
| `ollama: command not found` | Terminal neu starten oder `source ~/.bashrc` |
| Download bricht ab | `ollama pull <modell>` erneut ausführen — setzt fort |
| Modell antwortet sehr langsam | Kleineres Modell wählen; RAM prüfen mit `free -h` |
| `ollama: error loading model` | Zu wenig RAM — VM-Speicher erhöhen oder kleineres Modell |
| Ollama startet nicht | `systemctl --user restart ollama` |

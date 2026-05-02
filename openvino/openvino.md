# OpenVINO Model Server – Inbetriebnahme mit Docker



## Voraussetzungen

- Docker installiert und lauffähig
- Ausreichend Speicherplatz für Modelle und Docker-Image
- (Optional) GPU-Treiber für Hardware-Beschleunigung

---

## 1. Docker-Image herunterladen

Das offizielle Image von Docker Hub:

```bash
docker pull openvino/model_server:latest
```

Alternativ aus dem RedHat Ecosystem Catalog:

```bash
docker pull registry.connect.redhat.com/intel/openvino-model-server:latest
```

---

## 2. Modell vorbereiten

Der Model Server erwartet Modelle im OpenVINO IR-Format (`.xml` + `.bin`) oder als ONNX-Datei.

Die Verzeichnisstruktur muss folgendes Schema einhalten:

```
models/
└── <modellname>/
    └── <versionsnummer>/
        ├── model.xml
        └── model.bin
```

---

## 3. Server starten

### Einzelnes Modell bereitstellen

```bash
docker run -u $(id -u) \
  -v $(pwd)/models:/models \
  -p 9000:9000 \
  -p 8080:8080 \
  openvino/model_server:latest \
  --model_name resnet \
  --model_path /models/resnet50 \
  --port 9000 \
  --rest_port 8080
```

| Parameter | Bedeutung |
|---|---|
| `-u $(id -u)` | Container läuft mit der UID des Host-Nutzers (Dateiberechtigungen) |
| `-v $(pwd)/models:/models` | Lokales Modellverzeichnis in den Container einbinden |
| `-p 9000:9000` | gRPC-Port freigeben |
| `-p 8080:8080` | REST-API-Port freigeben |
| `--model_name` | Name des Modells (wird in Anfragen verwendet) |
| `--model_path` | Pfad zum Modell **innerhalb** des Containers |
| `--port` | gRPC-Listening-Port |
| `--rest_port` | HTTP/REST-Listening-Port |

### Layout-Transformation (optional)

Falls das Modell ein anderes Eingabelayout erwartet (z. B. NHWC statt NCHW):

```bash
docker run -u $(id -u) \
  -v $(pwd)/models:/models \
  -p 9000:9000 \
  openvino/model_server:latest \
  --model_name resnet \
  --model_path /models/resnet50 \
  --layout NHWC:NCHW \
  --port 9000
```

---

## 4. Mehrere Modelle mit Konfigurationsdatei

Für mehrere Modelle wird eine JSON-Konfigurationsdatei empfohlen:

```json
{
  "model_config_list": [
    {
      "config": {
        "name": "resnet",
        "base_path": "/models/resnet50"
      }
    },
    {
      "config": {
        "name": "yolo",
        "base_path": "/models/yolov8"
      }
    }
  ]
}
```

Datei speichern als `config.json`, dann starten:

```bash
docker run -u $(id -u) \
  -v $(pwd)/models:/models \
  -v $(pwd)/config.json:/config.json \
  -p 9000:9000 \
  -p 8080:8080 \
  openvino/model_server:latest \
  --config_path /config.json \
  --port 9000 \
  --rest_port 8080
```

---

## 5. Server testen

### REST-API (HTTP)

Status aller Modelle abfragen:

```bash
curl http://localhost:8080/v1/config
```

Modell-Metadaten abfragen:

```bash
curl http://localhost:8080/v1/models/resnet
```

---

## 6. GPU-Unterstützung

Für Intel GPU (iGPU / Arc / Flex / Max) muss der Container Zugriff auf die GPU-Geräte erhalten:

```bash
docker run -u $(id -u) \
  --device /dev/dri \
  -v $(pwd)/models:/models \
  -p 9000:9000 \
  openvino/model_server:latest \
  --model_name resnet \
  --model_path /models/resnet50 \
  --port 9000 \
  --target_device GPU
```

Zusätzlich muss der Nutzer in der Gruppe `render` sein:

```bash
sudo usermod -aG render $USER
```

---

## 7. Container im Hintergrund betreiben

```bash
docker run -d \
  --name ovms \
  -u $(id -u) \
  -v $(pwd)/models:/models \
  -p 9000:9000 \
  -p 8080:8080 \
  --restart unless-stopped \
  openvino/model_server:latest \
  --model_name resnet \
  --model_path /models/resnet50 \
  --port 9000 \
  --rest_port 8080
```

Logs ansehen:

```bash
docker logs ovms
docker logs -f ovms   # Live-Ausgabe
```

Server stoppen:

```bash
docker stop ovms
docker rm ovms
```

---

## 8. Aus Quellcode bauen (optional)

Für nicht veröffentlichte Features oder eigene Anpassungen:

```bash
git clone https://github.com/openvinotoolkit/model_server.git
cd model_server
make release_image GPU=1
```

Der Build-Prozess dauert je nach Hardware **40 Minuten oder länger**.

---

## 9. Docker Compose (mehrere Modelle)

Alle Modelle können einzeln per Docker Compose gestartet werden. Jeder Dienst bekommt seinen eigenen Port:

| Dienst | REST-Port | gRPC-Port | API-Endpunkt |
|---|---|---|---|
| qwen3-8b | 8081 | 9001 | `/v3/chat/completions` |
| gemma-4-e4b | 8082 | 9002 | `/v3/chat/completions` |
| whisper-small | 8083 | 9003 | `/v3/audio/transcriptions` |
| whisper-medium-en | 8084 | 9004 | `/v3/audio/transcriptions` |

Starten (alle Dienste):

```bash
UID=$(id -u) GID=$(id -g) docker compose up -d
```

Einzelnen Dienst starten:

```bash
UID=$(id -u) GID=$(id -g) docker compose up -d ovms-qwen3
```

Status prüfen:

```bash
docker compose ps
docker compose logs -f ovms-qwen3
```

Alle stoppen:

```bash
docker compose down
```

---

## Unterstützte APIs

| API | Protokoll | Standard |
|---|---|---|
| TensorFlow Serving | gRPC + REST | Port 9000 / 8080 |
| KServe v2 | gRPC + REST | Port 9000 / 8080 |
| OpenAI-kompatibel | REST | Port 8080 |

---


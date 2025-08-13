# Verwende ein offizielles Python-Laufzeit-Image als Basis
FROM python:3.12-slim

# Installiere den Docker-Client. Dies ist notwendig, damit die Anwendung
# 'docker run' Befehle ausführen kann.
RUN apt-get update && apt-get install -y ca-certificates curl gnupg && \
    mkdir -m 0755 -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
    "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y docker-ce-cli
    
# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die Abhängigkeiten in das Arbeitsverzeichnis
# In diesem Fall benötigen wir nur Flask, da subprocess und sqlite3 in der Standardbibliothek enthalten sind
COPY requirements.txt requirements.txt

# Installiere alle Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den gesamten Anwendungscode in das Arbeitsverzeichnis
COPY main.py /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Geben Sie den Port an, den die Anwendung verwendet
EXPOSE 3300

# Führe den Flask-Server aus, wenn der Container startet
CMD ["waitress-serve", "--listen=0.0.0.0:3300", "main:app"]

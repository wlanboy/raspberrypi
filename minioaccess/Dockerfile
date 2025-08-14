# Verwende ein offizielles Python-Laufzeit-Image als Basis
FROM python:3.12-slim

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app
# MC client
RUN apt-get update && apt-get install curl -y
RUN curl -o /app/mc https://dl.min.io/client/mc/release/linux-amd64/mc
RUN chmod +x mc

# Kopiere die Abhängigkeiten in das Arbeitsverzeichnis
# In diesem Fall benötigen wir nur Flask, da subprocess und sqlite3 in der Standardbibliothek enthalten sind
COPY requirements.txt requirements.txt

# Installiere alle Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den gesamten Anwendungscode in das Arbeitsverzeichnis
COPY .env /app/
COPY main.py /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Geben Sie den Port an, den die Anwendung verwendet
EXPOSE 9002

# Führe den Flask-Server aus, wenn der Container startet
CMD ["waitress-serve", "--listen=0.0.0.0:9002", "main:app"]

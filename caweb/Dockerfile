# Verwenden Sie ein Python-Basis-Image
FROM python:3.12-slim

# Setzen Sie das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopieren Sie die Anwendungsdateien in das Arbeitsverzeichnis
COPY main.py /app/
COPY create.sh /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Installieren Sie die benötigten Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Machen Sie das Shell-Skript ausführbar
RUN chmod +x create.sh

# Geben Sie den Port an, den die Anwendung verwendet
EXPOSE 2000

# Startbefehl für die Anwendung
#CMD ["python", "main.py"]
CMD ["waitress-serve", "--listen=0.0.0.0:5000", "main:app"]
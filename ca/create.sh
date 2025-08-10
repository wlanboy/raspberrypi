#!/bin/bash

# === Lokale CA-Dateien ===
CA_CERT="ca.pem"
CA_KEY="ca.key"

# === Hostname prüfen ===
if [ -z "$1" ]; then
  echo "❌ Fehler: Bitte gib einen Hostnamen an."
  echo "➡️  Beispiel: ./create.sh homeassistant.lan"
  exit 1
fi

HOSTNAME="$1"
DIR="$HOSTNAME"

# === Ordner erstellen ===
mkdir -p "$DIR"
cd "$DIR" || exit 1

# === Schlüssel generieren ===
openssl genrsa -out "$HOSTNAME.key" 4096

# === CSR erstellen ===
openssl req -new -key "$HOSTNAME.key" -out "$HOSTNAME.csr" \
  -subj "/C=DE/ST=Germany/L=LAN/O=Homelab/CN=$HOSTNAME"

# === Zertifikat signieren ===
openssl x509 -req -in "$HOSTNAME.csr" -CA "../$CA_CERT" -CAkey "../$CA_KEY" \
  -CAcreateserial -out "$HOSTNAME.crt" -days 825 -sha256

echo "✅ Zertifikat für $HOSTNAME wurde erstellt:"
echo "🔐 Schlüssel: $DIR/$HOSTNAME.key"
echo "📄 Zertifikat: $DIR/$HOSTNAME.crt"

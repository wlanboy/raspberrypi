#!/bin/bash

# === Lokale CA-Dateien ===
CA_CERT="ca.pem"
CA_KEY="ca.key"

# === Hostname prüfen ===
if [ -z "$1" ]; then
  echo "❌ Fehler: Bitte gib einen Hostnamen an."
  echo "➡️  Beispiel: ./create-cert.sh homeassistant.lan"
  exit 1
fi

HOSTNAME="$1"
DIR="$HOSTNAME"

# === Ordner erstellen ===
mkdir -p "$DIR"
cd "$DIR" || exit 1

# === Schlüssel generieren ===
openssl genrsa -out "$HOSTNAME.key" 4096

# === Temporäre OpenSSL-Konfiguration mit SAN ===
cat > san.cnf <<EOF
[ req ]
default_bits       = 4096
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt             = no

[ req_distinguished_name ]
C  = DE
ST = Germany
L  = LAN
O  = Homelab
CN = $HOSTNAME

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = $HOSTNAME
EOF

# === CSR erstellen mit SAN ===
openssl req -new -key "$HOSTNAME.key" -out "$HOSTNAME.csr" -config san.cnf

# === Zertifikat signieren mit SAN ===
openssl x509 -req -in "$HOSTNAME.csr" -CA "../$CA_CERT" -CAkey "../$CA_KEY" \
  -CAcreateserial -out "$HOSTNAME.crt" -days 825 -sha256 -extfile san.cnf -extensions req_ext

# === Aufräumen ===
rm san.cnf

echo "✅ Zertifikat für $HOSTNAME mit SAN wurde erstellt:"
echo "🔐 Schlüssel: $DIR/$HOSTNAME.key"
echo "📄 Zertifikat: $DIR/$HOSTNAME.crt"

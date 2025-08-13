#!/bin/bash

# === Lokale CA-Dateien ===
CA_CERT="/local-ca/ca.pem"
CA_KEY="/local-ca/ca.key"

# === Hostname prüfen ===
if [ -z "$1" ]; then
  echo "❌ Fehler: Bitte gib einen Hostnamen an."
  echo "➡️ Beispiel: ./create.sh homeassistant.lan alt.lan"
  exit 1
fi

HOSTNAME="$1"
DIR="/local-ca/$HOSTNAME" # Neuer Pfad für den Host-Ordner

# Ersten Parameter als Haupt-Hostname übernehmen
main_dns="DNS.1 = $HOSTNAME"
# Iterieren über die restlichen Parameter für alternative DNS-Namen
alt_dns=""
count=2
for san in "${@:2}"; do
  alt_dns+="DNS.$count = $san"$'\n'
  count=$((count+1))
done

# === Ordner erstellen ===
mkdir -p "$DIR"
cd "$DIR" || exit 1

# === Schlüssel generieren ===
openssl genrsa -out "$HOSTNAME.key" 4096

# === Temporäre OpenSSL-Konfiguration mit SAN ===
cat > /tmp/san.cnf <<EOF
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
$main_dns
$alt_dns
EOF

# === CSR erstellen mit SAN ===
openssl req -new -key "$DIR/$HOSTNAME.key" -out "$DIR/$HOSTNAME.csr" -config /tmp/san.cnf

# === Zertifikat signieren mit SAN ===
# Der Pfad zur CA-Datei wird jetzt relativ zu `local-ca/$HOSTNAME` gesetzt
openssl x509 -req -in "$DIR/$HOSTNAME.csr" -CA "$CA_CERT" -CAkey "$CA_KEY" \
  -CAcreateserial -out "$DIR/$HOSTNAME.crt" -days 825 -sha256 -extfile /tmp/san.cnf -extensions req_ext

# === Aufräumen ===
rm /tmp/san.cnf "$DIR/$HOSTNAME.csr"

echo "✅ Zertifikat für $HOSTNAME mit SAN wurde erstellt:"
echo "🔐 Schlüssel: $DIR/$HOSTNAME.key"
echo "📄 Zertifikat: $DIR/$HOSTNAME.crt"
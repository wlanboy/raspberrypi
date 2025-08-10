#!/bin/bash

# Check if an IP address was passed as an argument
if [ -z "$1" ]; then
    echo "Error: Please provide the IP address of your server."
    echo "Example: ./install_pihole.sh 192.168.1.100"
    exit 1
fi

SERVER_IP="$1"
PIHOLE_DIR="/pihole"

echo "Creating Pi-hole directories..."
mkdir -p "$PIHOLE_DIR/etc"
mkdir -p "$PIHOLE_DIR/dns"

echo "Starting Pi-hole container..."
docker run -d \
    --name pihole \
    -p 8080:80 \
    -p 8443:443 \
    -p "$SERVER_IP:53:53/tcp" \
    -p "$SERVER_IP:53:53/udp" \
    -p "$SERVER_IP:67:67/udp" \
    -v "$PIHOLE_DIR/etc:/etc/pihole/" \
    -v "$PIHOLE_DIR/dns:/etc/dnsmasq.d/" \
    -e TZ=Europe/Berlin \
    -e ServerIP="$SERVER_IP" \
    -e WEBPASSWORD=pihole \
    -e DNS1=192.168.178.1 \
    -e DNS2=8.8.8.8 \
    --restart unless-stopped \
    pihole/pihole:latest

echo "Pi-hole is starting. The web interface will be available at http://$SERVER_IP:8080."
echo "The default web password is 'pihole'. Please change it after your first login."

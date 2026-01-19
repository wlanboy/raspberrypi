# Pi-hole Installation via Script
This document describes how to create a flexible shell script that sets up a Pi-hole Docker container. You only need to pass the IP address of your server as an argument.

## 1\. Prerequisites
Before you begin, make sure **Docker** is installed on your system. If it's not, follow the instructions at this link:
  - **[Docker Installation on Raspberry Pi](https://github.com/wlanboy/raspberrypi/blob/main/docker.md)**

# 2\. Create the Script
Create a new file named `install_pihole.sh` and add the following code. This script will create the necessary directories and set up the Docker container.

```bash
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

```

## 3\. Make the Script Executable and Run It
Save the file and make it executable so you can run it:

```bash
chmod +x install_pihole.sh
```

Now, you can run the script and pass your server's IP address as an argument. In this example, we'll use the IP `192.168.1.100`:
```bash
./install_pihole.sh 192.168.1.100
```

The script will create the necessary directories and start the Pi-hole container with the IP address you provided.

## 4\. Using Pi-hole
Once the container is running, you can access the web interface to configure Pi-hole and manage your blocklists. You'll find the web interface at:
**http://YOUR\_SERVER\_IP:8080**

The default password for the web interface is `pihole`. It is highly recommended that you change this password immediately.

#!/bin/bash

# 1. Alte/fehlerhafte Repositories entfernen
sudo rm -f /etc/apt/sources.list.d/intel-graphics.list
sudo rm -f /etc/apt/sources.list.d/intel-gpu-noble.list

# 2. GPG-Schlüssel korrekt importieren
sudo mkdir -p /usr/share/keyrings
wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | \
sudo gpg --dearmor --yes --output /usr/share/keyrings/intel-graphics.gpg
sudo chmod 644 /usr/share/keyrings/intel-graphics.gpg

# 3. Das korrekte Intel GPU Repository für Ubuntu 24.04 (Noble) hinzufügen
# Wir nutzen den 'unified' Stack, der für Battlemage/Xe2 optimiert ist
echo "deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu noble/lts/2350 unified" | sudo tee /etc/apt/sources.list.d/intel-gpu-noble.list

# 4. OneAPI Repository hinzufügen
wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB | \
gpg --dearmor | sudo tee /usr/share/keyrings/oneapi-archive-keyring.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" | sudo tee /etc/apt/sources.list.d/oneAPI.list

# 5. System-Update
sudo apt update

# 6. Installation der Treiber-Komponenten (Moderne Paketnamen für Xe-Stack)
sudo apt install -y \
    intel-opencl-icd \
    libze-intel-gpu1 \
    libze1 \
    intel-media-va-driver-non-free \
    libigdgmm12 \
    clinfo \
    intel-gpu-tools \
    mesa-utils

# 7. Installation der OneAPI Entwicklungstools (optional, aber von dir gewünscht)
sudo apt install -y intel-oneapi-compiler-dpcpp-cpp intel-oneapi-mkl

# 8. Benutzer zur Gruppe 'render' hinzufügen (Wichtig für Zugriff ohne sudo)
sudo usermod -aG render $USER
sudo usermod -aG video $USER

echo "-----------------------------------------------------------"
echo "Installation abgeschlossen!"
echo "WICHTIG: Starte deinen PC neu, damit alle Änderungen greifen."
echo "Nach dem Neustart kannst du mit 'clinfo -l' testen."
echo "-----------------------------------------------------------"
#source /opt/intel/oneapi/setvars.sh
#sycl-ls
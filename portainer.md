# 🚀 Portainer Installation via Script
Portainer is an intuitive, open-source interface for managing Docker environments. With the following simple script, you can install Portainer as a Docker container.

## 1\. Prerequisites
Before you begin, make sure **Docker** is installed on your system. If it's not, follow the instructions at this link:
  - **[Docker Installation on Raspberry Pi](https://github.com/wlanboy/raspberrypi/blob/main/docker.md)**
    
## 2. Create the Script
Create a new file named install_portainer.sh. Copy the following code into the file. This script will stop and remove any existing Portainer container to ensure a clean reinstallation, and then start the container with persistent data storage.

```
#!/bin/bash

echo "Creating the Portainer volume..."
docker volume create portainer_data

echo "Stopping and removing any existing Portainer container..."
docker stop portainer >/dev/null 2>&1
docker rm portainer >/dev/null 2>&1

echo "Starting the Portainer container..."
docker run -d \
  -p 8000:8000 \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:lts

echo "Portainer installation complete."
echo "The web interface is available at https://YOUR_SERVER_IP:9443."
```

## 3. Make the Script Executable and Run It
Save the file and make it executable.
```
chmod +x install_portainer.sh
```

Then, run the script to start the installation:
```
./install_portainer.sh
```

## 3. Using Portainer
After the script has been executed, the Portainer web interface will be available. You can access it in your browser at the following address:
* https://YOUR_SERVER_IP:9443

On your first access, you will be prompted to create an admin user and password. You can then manage your Docker environment through the web interface.

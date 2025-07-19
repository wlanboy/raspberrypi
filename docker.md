# Docker Installation on Raspberry Pi
Details: [official Docker documentation](https://docs.docker.com/engine/install/debian/).

---

## 1. Update Your System

```
sudo apt update
sudo apt upgrade -y
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
```

## 2a. Setup docker armhf

```
# Add Docker's official GPG key:
sudo curl -fsSL https://download.docker.com/linux/raspbian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/raspbian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

## 2b. Setup docker arm64

```
# Add Docker's official GPG key:
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

## 3. Install packages
```
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 4. Add user to docker group

```
sudo usermod -aG docker $(whoami)
```


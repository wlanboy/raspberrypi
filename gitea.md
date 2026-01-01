# Git server with web frontend
Install and run your own github like instance with gitea. 

## use docker-compose
* https://github.com/wlanboy/raspberrypi/blob/main/gitea/docker-compose.yml

## create service user
bash
```bash
adduser --system --shell /bin/bash --gecos 'Git Version Control' --group --disabled-password --home /home/git git

sudo mkdir /gitea
sudo chown git:samuel -R /gitea
sudo chmod 775 -R /gitea
```

## install service

```bash
cd /gitea
wget -O gitea https://dl.gitea.io/gitea/1.25.3/gitea-1.25.3-linux-arm-6
#or
wget -O gitea https://dl.gitea.io/gitea/1.25.3/gitea-1.25.3-linux-arm64
chmod +x gitea 
```

## create service

```bash
cat > /etc/systemd/system/gitea.service<< EOF
[Unit]
Description=Gitea (Git with a cup of tea)
After=syslog.target
After=network.target
 
[Service]
RestartSec=2s
Type=simple
User=git
Group=samuel
WorkingDirectory=/gitea
ExecStart=/gitea/gitea web
Restart=always
Environment=USER=git HOME=/home/git GITEA_WORK_DIR=/gitea
 
[Install]
WantedBy=multi-user.target
EOF
```

## enable and start gitea service

```bash
systemctl enable gitea
systemctl restart gitea
```

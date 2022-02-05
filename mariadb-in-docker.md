# create mariadb instance with docker

## install docker on raspbian 64 bit
```
sudo apt-get install ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io

sudo adduser pi docker
```

## config folders and pi user
```
sudo mkdir -p /mariadb/data
sudo chown pi:docker -R /mariadb
sudo chmod 775 -R /mariadb
wget -P /mariadb https://github.com/wlanboy/Dockerfiles/raw/main/MariaDB/lowmemory.cnf 
```

## create and run mariadb container
```
docker run --name mariadb --net=workspace -p 3306:3306 -v /mariadb/data:/var/lib/mysql -v /mariadb/lowmemory.cnf:/etc/mysql/my.cnf -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=spring -e MYSQL_USER=spring -e MYSQL_PASSWORD=spring -d --restart unless-stopped mariadb:10.5
```


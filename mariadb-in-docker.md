# create mariadb instance with docker
Simple commands to create mariadb instance with docker.


## install docker 
- See: https://github.com/wlanboy/raspberrypi/blob/main/docker.md

## config folders and pi user

```bash
sudo mkdir -p /mariadb/data
sudo chown $USER:docker -R /mariadb
sudo chmod 775 -R /mariadb
wget -P /mariadb https://github.com/wlanboy/Dockerfiles/raw/main/MariaDB/lowmemory.cnf 
```

## create and run mariadb container

```bash
docker run --name mariadb --net=workspace -p 3306:3306 -v /mariadb/data:/var/lib/mysql -v /mariadb/lowmemory.cnf:/etc/mysql/my.cnf -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=spring -e MYSQL_USER=spring -e MYSQL_PASSWORD=spring -d --restart unless-stopped mariadb:11.8
```


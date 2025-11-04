# Create tor service

## dependencies

```bash
sudo apt install tor
```

## configure tor service

```bash
sudo echo "RunAsDaemon 1" >> /etc/tor/torrc
sudo echo "DataDirectory /var/lib/tor" >> /etc/tor/torrc
sudo echo "HiddenServiceDir /var/lib/tor/hidden_service/" >> /etc/tor/torrc
sudo echo "HiddenServiceDir HiddenServicePort 80 127.0.0.1:80" >> /etc/tor/torrc
```

## start tor service

```bash
sudo service tor restart
```

## get your tor onion address for hidden service

```bash
sudo cat /var/lib/tor/hidden_service/hostname
```

## configure nginx

```bash
Uncomment "server_tokens off;" and "server_name_in_redirect off;"
add one line under "server_tokens off;" > "port_in_redirect off;"
```

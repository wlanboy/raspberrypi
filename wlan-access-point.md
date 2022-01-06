# Wlan Access Point with Adblocker

## install dependencies
```
sudo apt-get install hostapd isc-dhcp-server iptables-persistent dnsutils git iproute2 whiptail ca-certificates
```

## dhcpd config
```
sudo nano /etc/dhcp/dhcpd.conf
```
changes:
```
#option domain-name "example.org";
#option domain-name-servers ns1.example.org, ns2.example.org;
authoritative;
subnet 192.168.42.0 netmask 255.255.255.0 {
	range 192.168.42.10 192.168.42.50;
	option broadcast-address 192.168.42.255;
	option routers 192.168.42.1;
	default-lease-time 600;
	max-lease-time 7200;
	option domain-name "local";
	option domain-name-servers 192.168.42.1;
}
```

```
sudo nano /etc/default/isc-dhcp-server
```
changes:
```
INTERFACES="wlan0"
```

```
sudo nano /etc/default/isc-dhcp-server
```
changes:
```
INTERFACES="wlan0"
```

## configure wlan0 interface
```
nano /etc/network/interfaces.d/wlan0
```
content:
```
allow-hotplug wlan0
iface wlan0 inet static
  address 192.168.42.1
  netmask 255.255.255.0
```

## setup wlan0 interface
```
ifconfig wlan0 192.168.42.1
```

## hostapd config
```
sudo nano /etc/hostapd/hostapd.conf
```
content:
```
interface=wlan0 #<== CHANGE THIS
ssid=Raspberry
country_code=DE
hw_mode=g
channel=6 #<== CHANGE THIS
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=Raspberry #<== CHANGE THIS
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
wpa_group_rekey=86400
ieee80211n=1
wme_enabled=1
```

```
sudo nano /etc/default/hostapd
```
changes:
```
DAEMON_CONF="/etc/hostapd/hostapd.conf"
```


## hostapd config
```
sudo nano /etc/sysctl.conf
```
changes:
```
net.ipv4.ip_forward=1
```

## ip forwards
```
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
sh -c "iptables-save > /etc/iptables/rules.v4"
```

## test hostapd 
```
/usr/sbin/hostapd /etc/hostapd/hostapd.conf
strg+c
```

## enable services
```
systemctl unmask hostapd
systemctl enable hostapd
systemctl start hostapd

systemctl enable isc-dhcp-server
systemctl start isc-dhcp-server
```

## install pi-hole
```
curl -sSL https://install.pi-hole.net | bash
```
* select eth0 device
* do not activate static ip settings
* wait

## pi-hole web ui steps
* http://pi-hole/admin/settings.php?tab=dns
  * Permit all origins
  * Never forward non-FQDN A and AAAA queries
  * Use Conditional Forwarding -> your router ip subnet
* http://pi-hole/admin/groups-adlists.php
  * add from https://github.com/wlanboy/Dockerfiles/blob/main/PiHole/hostlists.txt
* http://pi-hole/admin/gravity.php
  * update gravity lists

# headless configuration of wlan client
Mount sd card on your pc and change following settings to enable ssh daemon and wlan login for your Raspberry Pi.

## enable ssh accress

```bash
touch /boot/ssh
```

## provide wlan client configuration

```bash
cat > /boot/wpa_supplicant.conf<< EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=DE
network={
    ssid="YOUR_NETWORK_NAME"
    psk="YOUR_NETWORK_PASSWORD"
    key_mgmt=WPA-PSK
}
EOF
```

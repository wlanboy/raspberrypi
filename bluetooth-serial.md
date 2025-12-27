# Create bluetooth serial console
Commands to create a bluetooth serial console to connect your phone via bluetooth to your linux pc.


## install tools

```bash
sudo apt install bluetooth rfkill bluez bluez-tools 
```

## change bluetooth settings

```bash
sudo nano /lib/systemd/system/bluetooth.service
```

changes:

```bash
ExecStart=/usr/lib/bluetooth/bluetoothd -C
ExecStartPost=/usr/bin/sdptool add SP
```

## create rfcomm service

```bash
sudo cat > /etc/systemd/system/rfcomm.service<< EOF
[Unit]
Description=Bluetooth service
Documentation=man:bluetoothd(8)
ConditionPathIsDirectory=/sys/class/bluetooth

[Service]
[Unit]
Description=RFCOMM service
After=bluetooth.service
Requires=bluetooth.service

[Service]
ExecStart=/usr/bin/rfcomm watch hci0 1 getty rfcomm0 115200 vt100 -a pi

[Install]
WantedBy=multi-user.target
EOF
```

## apply changes

```bash
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
sudo systemctl enable rfcomm
sudo systemctl restart rfcomm
```

## create connection with desktop

```bash
bluetoothctl 
------------ commands to type in:
power on
discoverable on
pairable on
scan on
devices
trust [MAC]
pair [MAC]
connect [MAC]
```

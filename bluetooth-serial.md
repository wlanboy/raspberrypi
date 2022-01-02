# Create bluetooth serial console

## install tools
```
sudo apt install bluetooth rfkill bluez bluez-tools 
```

## change bluetooth settings
```
sudo nano /lib/systemd/system/bluetooth.service
```
changes:
```
ExecStart=/usr/lib/bluetooth/bluetoothd -C
ExecStartPost=/usr/bin/sdptool add SP
```

## create rfcomm service
```
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
```
sudo systemctl restart bluetooth
sudo systemctl enable rfcomm
sudo systemctl restart rfcomm
```

## create connection with desktop
```
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

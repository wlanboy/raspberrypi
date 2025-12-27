# TP-LINK TL-WN725N USB 2 WLAN Stick
How to get this USB Wlan Stick work on Raspberry Pi.

```bash
uname -a
Linux odroidc2 5.10.81-meson64 #21.08.6 SMP PREEMPT Mon Nov 22 11:21:51 UTC 2021 aarch64 aarch64 aarch64 GNU/Linux
```

# usb info

```bash
sudo lsusb
Bus 001 Device 003: ID xxxx:yyyy Realtek Semiconductor Corp. RTL8188EUS 802.11n Wireless Network Adapter
```

# network device info

```bash
sudo lshw -C network
  *-network:1
       description: Wireless interface
       physical id: 3
       bus info: usb@1:1.1
       logical name: wlxf4f26d17486e
       serial: xx:yy:xx:yy:xx:yy
       capabilities: ethernet physical wireless
       configuration: broadcast=yes driver=8188eu driverversion=5.10.81-meson64 multicast=yes wireless=unassociated
```

# network device status

```bash
nmcli device status
DEVICE                   TYPE      STATE         CONNECTION
wlxf4f26d17486e          wifi      disconnected  --
p2p-dev-wlxf4f26d17486e  wifi-p2p  disconnected  --
lo                       loopback  unmanaged     --
```

# module information

```bash
sudo modinfo 8188eu
filename:       /lib/modules/5.10.81-meson64/kernel/drivers/net/wireless/rtl8188eu/8188eu.ko
version:        v5.7.6.1_35670.20191106
author:         Realtek Semiconductor Corp.
description:    Realtek Wireless Lan Driver
license:        GPL
[...]
depends:        cfg80211
intree:         Y
name:           8188eu
vermagic:       5.10.81-meson64 SMP preempt mod_unload aarch64
```

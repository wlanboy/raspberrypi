# TP Link TL-WN823N
Information collection on hardware module.

```bash
uname -a
Linux raspberrypione 5.10.17+ #1421 Thu May 27 13:58:02 BST 2021 armv6l GNU/Linux
```

# usb info

```bash
sudo lsusb
Bus 001 Device 004: ID xxxx:yyyy Realtek Semiconductor Corp. RTL8192CU 802.11n WLAN Adapter
```

# network device info

```bash
sudo lshw -C network
  *-network
       description: Wireless interface
       physical id: 2
       bus info: usb@1:1.2
       logical name: wlan0
       serial: xx:yy:xx:yy:xx:yy
       capabilities: ethernet physical wireless
       configuration: broadcast=yes driver=rtl8192cu driverversion=5.10.17+ firmware=N/A link=no multicast=yes wireless=IEEE 802.11
```

# module information

```bash
sudo modinfo rtl8192cu
filename:       /lib/modules/5.10.17+/kernel/drivers/net/wireless/realtek/rtlwifi/rtl8192cu/rtl8192cu.ko
firmware:       rtlwifi/rtl8192cufw_TMSC.bin
firmware:       rtlwifi/rtl8192cufw_B.bin
firmware:       rtlwifi/rtl8192cufw_A.bin
firmware:       rtlwifi/rtl8192cufw.bin
description:    Realtek 8192C/8188C 802.11n USB wireless
license:        GPL
[...]
depends:        mac80211,rtlwifi,rtl8192c-common,rtl_usb
intree:         Y
name:           rtl8192cu
vermagic:       5.10.17+ mod_unload modversions ARMv6 p2v8
parm:           swenc:Set to 1 for software crypto (default 0)
```

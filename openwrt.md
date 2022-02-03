# Flash openwrt image to sd and boot your Raspberry Pi

## check Raspberry Pi version
* https://openwrt.org/toh/raspberry_pi_foundation/raspberry_pi#hardware_highlights

## download image
* https://openwrt.org/toh/raspberry_pi_foundation/raspberry_pi#installation

## flash image
* use e.g. https://www.balena.io/etcher/#download

## install drivers
* Plugin lan cable to first port
* browse to http://192.168.1.1/cgi-bin/luci/
* check web interfaces http://192.168.1.1/cgi-bin/luci/admin/network/network
* check for modules in https://downloads.openwrt.org/releases/21.02.1/targets/bcm27xx/bcm2709/packages/ (raspberry pi zero w 2)
* check for modules in https://downloads.openwrt.org/releases/21.02.1/targets/bcm27xx/bcm2708/packages/ (raspberrz pi 1)

## usb troubleshooting
```
opkg update && opkg install usbutils && lsusb -t
```
and
```
cat /sys/kernel/debug/usb/devices
```

## packages needed for common usb lan adapters
* kmod-mii
* kmod-usb-net
* kmod-usb-net-rtl8152

## packages needed for  usb wlan sticks
* kmod-rtl8192cu 
* rtl8188eu-firmware

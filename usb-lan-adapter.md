# Use USB LAN adapter in libvirt vm
This guide explains how to isolate a USB LAN adapter from your host OS and pass it through directly to a VM using libvirt and virt-install. This ensures the host doesn't interfere with the network traffic of your OPNsense/Firewall VM.

## Identify the USB Device
First, plug in your adapter and find its Vendor ID and Product ID.

```Bash
lsusb
Look for a line like: Bus 004 Device 003: ID 0bda:8153 Realtek Semiconductor Corp. RTL8153 Gigabit Ethernet Adapter
```
- Vendor ID: 0bda
- Product ID: 8153

## Disable USB Autosuspend
To prevent Linux from powering down the adapter during inactivity, create a persistent udev rule.

Create a new rule file:
```Bash
sudo nano /etc/udev/rules.d/50-usb-autosuspend.rules
```

Add the following line (replace 0bda and 8153 with your IDs):
```Plaintext
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="8153", ATTR{power/autosuspend}="-1"
```

Reload the rules:
```Bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

##  Prevent the Host from using the NIC (Blacklisting)
If you don't want the host OS to even "see" the adapter as a network interface, you should unbind it or prevent the driver from attaching. However, for USB devices, USB Passthrough is usually sufficient as libvirt will detach it from the host driver automatically when the VM starts.

If you want to be 100% sure the host doesn't touch it, you can disable the specific interface on the host:
```Bash
ip addr | grep -B 1 "link/ether" | grep enx
9: enx00e08f0096b4: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc fq_codel state DOWN group default qlen 1000

sudo ip link set enx00e08f0096b4 down
```

## The virt-install Command
Use the --hostdev flag to pass the physical USB device to the VM. This method is superior to virtual network flags because it gives the VM direct hardware access.

```Bash
virt-install \
  --name opnsense-vm \
  --ram 4096 \
  --vcpus 2 \
  --os-variant freebsd13.0 \
  --disk path=/isos/opnsense.qcow2,size=20,bus=virtio \
  --cdrom /isos/OPNsense-25.7-dvd-amd64.iso \
  --network bridge=br0,model=virtio \
  --hostdev 0bda:8153,type=usb \
  --graphics vnc,listen=0.0.0.0 \
  --boot hd,cdrom,menu=on \
  --check all=off
  ```

Key Parameters:
--network bridge=br0: This acts as your WAN port (connected to your existing bridge).
--hostdev 0bda:8153,type=usb: This passes the Anker adapter as the LAN port. Inside OPNsense, it will likely appear as ue0.
--check all=off: Prevents warnings about the USB device being currently in use by the host.

## Post-Installation (Inside OPNsense)
Once OPNsense boots:
It will detect two interfaces: vtnet0 (VirtIO Bridge) and ue0 (USB Adapter).
- Assign vtnet0 to WAN.
- Assign ue0 to LAN.
- Disable "Hardware Checksum Offloading" in OPNsense (Interfaces > Settings), as USB drivers often struggle with this in virtualized environments.


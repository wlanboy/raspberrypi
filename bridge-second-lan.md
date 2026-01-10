# Dedicated Network Bridge
This setup isolates your second physical NIC (enp3s0) and turns it into a virtual switch (br0). Your host will not have an IP address on this interface, making it act as a "transparent pipe" for your VM.

## Fix Netplan Permissions
First, ensure your Netplan files have the correct secure permissions to avoid warnings:

```Bash
sudo touch /etc/netplan/60-lab-bridge.yaml
sudo chmod 600 /etc/netplan/*.yaml
```

## Configure the Bridge
Create a new configuration file for the second network card. Using a separate file (e.g., 60-lab-bridge.yaml) ensures your main connection (50-cloud-init.yaml) remains untouched.

Create the file:
```Bash
sudo nano /etc/netplan/60-lab-bridge.yaml
```

dd the following configuration:

```YAML
network:
  version: 2
  ethernets:
    enp3s0:
      dhcp4: no
      dhcp6: no
  bridges:
    br0:
      interfaces: [enp3s0]
      dhcp4: no
      dhcp6: no
      parameters:
        stp: false
        forward-delay: 0
```

Apply the changes:
```Bash
sudo netplan try
sudo netplan apply
```

## Verify the Bridge
Check if the bridge br0 was created correctly and has linked with your physical card:
```Bash
ip -brief link show br0
# It should show UP or UNKNOWN
```

To confirm enp3s0 is a slave of br0:
```Bash
bridge link show enp3s0
```

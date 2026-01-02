# Enable TRIM support on your USB SATA SSD
The JMicron JMS567 is notorious for having "broken" TRIM reporting in Linux, even though the hardware usually supports it. 
You can almost always fix this by forcing the unmap provisioning mode.

## check USB devices
```bash
lsusb
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 002: ID 2109:3431 VIA Labs, Inc. Hub
Bus 001 Device 003: ID 04d9:0007 Holtek Semiconductor, Inc. Raspberry Pi Internal Keyboard
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 002 Device 002: ID 152d:3562 JMicron Technology Corp. / JMicron USA Technology Corp. JMS567 SATA 6Gb/s bridge
```

## check TRIM support on block devices
```bash
lsblk -D
NAME   DISC-ALN DISC-GRAN DISC-MAX DISC-ZERO
loop0         0        4K       4G         0
sda           0        0B       0B         0
├─sda1        0        0B       0B         0
└─sda2        0        0B       0B         0
zram0         0        4K       2T         0
```

## Step 1: Create the udev rule
Since you've already identified your IDs (152d:3562), we can create a specific rule for this device.
```Bash
sudo nano /etc/udev/rules.d/10-jmicron-trim.rules
```

## Step 2: Add the following line Copy and paste this exact line:
```
ACTION=="add|change", ATTRS{idVendor}=="152d", ATTRS{idProduct}=="3562", SUBSYSTEM=="scsi_disk", ATTR{provisioning_mode}="unmap"
```

## Step 3: Apply rules without restart
```Bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Step 4: Verify the Result
Run the discard check again:
```Bash
lsblk -D
NAME   DISC-ALN DISC-GRAN DISC-MAX DISC-ZERO
loop0         0        4K       4G         0
sda           0        4K       4G         0
├─sda1        0        4K       4G         0
└─sda2        0        4K       4G         0
zram0         0        4K       2T         0
```

## Step 5: Perform a manual TRIM and ensure the kernel can actually talk to the drive's controller:
```Bash
sudo fstrim -v /
/: 690.2 MiB (723771392 bytes) trimmed
```

## Step 6: Enable Automatic Weekly TRIM
If the manual fstrim -v / worked, you should enable the system timer so you never have to think about it again:
```Bash
sudo systemctl enable --now fstrim.timer
```


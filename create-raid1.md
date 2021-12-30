# create raid with two usb disks

# install tools
```
sudo apt-get install mdadm
```

# list block devices
```
sudo blkid 
```

# create raid
```
sudo mdadm --create --verbose /dev/md/vol1 --level=1 --raid-devices=2 /dev/sda1 /dev/sdb1
```

# inspect raid config and persistent it
```
sudo mdadm --detail /dev/md/vol1
sudo mdadm --detail --scan >> /etc/mdadm/mdadm.conf
```

# crate file system and mount it
```
sudo mkfs.ext4 -v -m .1 -b 4096 -E stride=32,stripe-width=64 /dev/md/vol1
sudo mkdir /media/raid1
sudo mount /dev/md/vol1 /media/raid1
```

# create fstab link
```
sudo blkid

sudo cp /etc/fstab /etc/fstab.bak 
sudo echo "UUID=UUID-OF-RAID1-DEVICE /media/raid1 ext4 defaults 0 0" >> /etc/fstab
```

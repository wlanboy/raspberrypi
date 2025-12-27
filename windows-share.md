# Create smb share for windows clients
Commands to create a smb share for windows clients on any linux pc.

## install dependencies

```bash
sudo apt-get install samba samba-common-bin
```

## add samba password for windows user

```bash
sudo smbpasswd -a your-user-name
```

## create share

```bash
cat >> /etc/samba/smb.conf<< EOF
# NAS Share
[ship]
path = /media/raid1
comment = Raspberry Share
valid users = your-user-name
writable = yes
browsable = yes
create mask = 0770
directory mask = 0770
public = no
EOF
```

## test config and restart samba service

```bash
sudo testparm
sudo systemctl enable smbd
sudo systemctl restart smbd
```

# Create share for windows clients

## install dependencies
```
sudo apt-get install samba samba-common-bin
```

## add samba password for windows user
```
sudo smbpasswd -a your-user-name
```

## create share
```
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
```
sudo testparm
sudo systemctl enable smbd
sudo systemctl restart smbd
```

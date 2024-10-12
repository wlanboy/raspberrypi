# Step by stop ceph install

## packages
```
sudo apt update && sudo apt upgrade -y
sudo apt install -y ceph cephadm ceph-mgr ceph-mon ceph-osd ceph-mds radosgw
```

## file based mount
```
sudo losetup -d /dev/loop0
sudo fallocate -l 10G /var/lib/ceph/osd/ceph-0.img
#sudo wipefs -a /var/lib/ceph/osd/ceph-0.img
sudo losetup /dev/loop0 /var/lib/ceph/osd/ceph-0.img
sudo losetup -a
```

## monitor and init config with containers
```
sudo cephadm bootstrap --mon-ip 172.30.93.97
```

## access web ui
```
https://localhost:8443/
```

## create osd (Object Storage Daemon)
```
ceph orch host ls
sudo ceph orch daemon add osd red:/dev/loop0
```

## ceph services (Manager, Metadata Server, RADOS Gateway)
```
sudo ceph orch daemon add mgr red
sudo ceph orch daemon add mds red
sudo ceph orch daemon add rgw red
```

## ceph status
```
sudo cephadm shell -- ceph fsid
sudo cephadm shell -- ceph -s
sudo cephadm shell -- ceph osd status
```

## delete ceph cluster
```
sudo cephadm rm-cluster --fsid <deine-FSID> --force
```

# use local pihole dns server in k3s
How to change DNS servers in Ubuntu and k3s cluster running on Ubuntu.

## prepare resolve config of all nodes
```
sudo nano /etc/systemd/resolved.conf
DNS=192.168.178.91
sudo systemctl daemon-reload
sudo systemctl restart systemd-resolved
```

## restart k3s
```
sudo systemctl stop k3s
sleep 10
sudo systemctl start k3s
systemctl status k3s

# delete coredns pod
kubectl get pod -n kube-system -l k8s-app=kube-dns --no-headers | awk '{print $1}' | xargs -I{} kubectl delete pod -n kube-system {}
```

## test dns lookup
```
kubectl run -ti --rm busybox --image=busybox:1.37.0-glibc --restart=Never --timeout=5s -- nslookup tester.nuc.lan
```

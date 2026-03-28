# Use Local Pi-hole DNS Server in k3s

Configures Ubuntu nodes and a k3s cluster to use a self-hosted Pi-hole instance as the DNS resolver.
This ensures that custom local domain names (e.g. `*.nuc.lan`) are resolved correctly within the cluster.

## Prepare Resolve Config of All Nodes

Edit `/etc/systemd/resolved.conf` and set the Pi-hole IP as DNS server:

```bash
sudo nano /etc/systemd/resolved.conf
DNS=192.168.178.91
sudo systemctl daemon-reload
sudo systemctl restart systemd-resolved
```

## Restart k3s

```bash
sudo systemctl stop k3s
sleep 10
sudo systemctl start k3s
systemctl status k3s
```

Delete the CoreDNS pod so it picks up the new resolver:

```bash
kubectl get pod -n kube-system -l k8s-app=kube-dns --no-headers | awk '{print $1}' | xargs -I{} kubectl delete pod -n kube-system {}
```

## Test DNS Lookup

```bash
kubectl run -ti --rm busybox --image=busybox:1.37.0-glibc --restart=Never --timeout=5s -- nslookup tester.nuc.lan
```

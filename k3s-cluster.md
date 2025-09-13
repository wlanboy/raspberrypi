# Create arm64 based k3s cluster on ubuntu

## install docker 
- See: https://github.com/wlanboy/raspberrypi/blob/main/docker.md

## change boot cmd line
```
sudo nano /boot/firmware/cmdline.txt
#add cgroup_memory=1 cgroup_enable=memory
```

## swap files and ip tables
```
sudo apt install -y iptables
sudo dphys-swapfile swapoff
sudo dphys-swapfile uninstall
sudo systemctl disable dphys-swapfile
```

## install k3s without traefik and servicelb and define the exteral ip
```
PUBLIC_IP="192.168.178.22"

curl -sfL https://get.k3s.io | K3S_KUBECONFIG_MODE="644" INSTALL_K3S_CHANNEL=stable INSTALL_K3S_EXEC="--disable=traefik --disable=servicelb --node-external-ip=${PUBLIC_IP}" sh -
sudo cp /var/lib/rancher/k3s/server/node-token ~/token
sudo chown $USER:$USER ~/token
```

## add agend to cluster
```
TOKEN_FILE=~/token
K3S_TOKEN=$(cat "$TOKEN_FILE")

curl -sfL https://get.k3s.io | K3S_KUBECONFIG_MODE="644" INSTALL_K3S_CHANNEL=stable INSTALL_K3S_EXEC="--node-external-ip=192.168.178.68" K3S_URL=https://gmk:6443 K3S_TOKEN=$K3S_TOKEN sh -

```

## copy kube config
```
mkdir ~/.kube
sudo cp -i /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config
```

## install kubectl
```
cd ~
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
chmod +x ./kubectl
sudo cp ./kubectl /usr/bin
```

## install metallb 
```
cd ~
cat > metallb-pool.yaml <<EOF
---
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: first-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.170.10-192.168.170.250
EOF

cat > metallb-adv.yaml <<EOF
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: advertisement
  namespace: metallb-system
spec:
  ipAddressPools:
  - first-pool
EOF

kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.9/config/manifests/metallb-native.yaml
kubectl apply -f metallb-pool.yaml
kubectl apply -f metallb-adv.yaml
```

## check cluster
```
kubectl get all -A


## uninstall k3s
```
sudo /usr/local/bin/k3s-uninstall.sh
```


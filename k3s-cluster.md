# Create arm64 based k3s cluster on ubuntu

## install docker tools
```
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin  cgroupfs-mount

sudo usermod -aG docker $USER
```

## install k3s without traefik and servicelb and define the exteral ip
```
curl -sfL https://get.k3s.io | K3S_KUBECONFIG_MODE="644" INSTALL_K3S_CHANNEL=stable INSTALL_K3S_EXEC="--disable=traefik --disable=servicelb --node-external-ip=192.168.178.22" sh -
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

## install ingress-nginx
```
wget kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.7.0/deploy/static/provider/baremetal/deploy.yaml -O nginx-deploy.yaml
kubectl create ns ingress-nginx
kubectl apply -f nginx-deploy.yaml
```

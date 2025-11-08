#!/bin/bash
set -e
cd ~

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo cp ./kubectl /usr/local/bin

#https://github.com/helm/helm/releases
HELM_VERSION="3.19.0"
#https://github.com/kubernetes-sigs/kind/releases
KIND_VERSION="0.30.0"
#https://github.com/istio/istio/releases/
ISTIO_VERSION="1.27.3"
#https://github.com/derailed/k9s/releases
K9S_VERSION="0.50.16"

wget "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz"
tar -zxvf "helm-v${HELM_VERSION}-linux-amd64.tar.gz"
sudo cp linux-amd64/helm /usr/local/bin/helm

curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v${KIND_VERSION}/kind-linux-amd64"
chmod +x ./kind
sudo mv ./kind /usr/local/bin

wget "https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/istio-${ISTIO_VERSION}-linux-amd64.tar.gz"
tar -zxvf "istio-${ISTIO_VERSION}-linux-amd64.tar.gz"
sudo cp "istio-${ISTIO_VERSION}/bin/istioctl" /usr/local/bin

wget "https://github.com/derailed/k9s/releases/download/v${K9S_VERSION}/k9s_Linux_amd64.tar.gz"
tar -zxvf k9s_Linux_amd64.tar.gz
sudo cp ./k9s /usr/local/bin

curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-arm64
chmod +x argocd
sudo mv argocd /usr/local/bin/s

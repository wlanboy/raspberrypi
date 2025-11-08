# Install Argo CD on the k3s cluster and expose the Web UI via MetalLB

Prerequisites
- k3s cluster up and kubeconfig copied (see k3s-cluster.md).
- MetalLB installed and a pool configured (example pool in k3s-cluster.md: 192.168.170.10-192.168.170.250).

## install Argo CD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

## install nginx controller
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.14.0/deploy/static/provider/baremetal/deploy.yaml
```

## howto install cert-manager
see: https://github.com/wlanboy/raspberrypi/tree/main/ca/cert-manager

## Create the TLS Certificate with cert-manager
```bash
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: argocd-cert
  namespace: argocd
spec:
  secretName: argocd-tls
  issuerRef:
    name: local-ca-issuer
    kind: ClusterIssuer
  commonName: argocd.gmk.local
  dnsNames:
    - argocd.gmk.local
  ipAddresses:
    - 192.168.170.100
EOF
```

## create ingress with ssl cert
```bash 
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-ingress
  namespace: argocd
  annotations:
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: local-ca-issuer
spec:
  tls:
  - hosts:
    - argocd.gmk.local
    - 192.168.170.100
    secretName: argocd-cert
  rules:
  - host: argocd.gmk.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 443
EOF
```

## access the UI and CLI login

Get the initial admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

Open the web UI:
- Browse to: https://192.168.170.100/ (replace with your ARGOCD_IP)
- The server uses a self-signed certificate by default — browser will warn.

Install the argocd CLI (arm64):
```bash
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-arm64
chmod +x argocd
sudo mv argocd /usr/local/bin/
```

Login with the CLI:
```bash
ARGOCD_PW=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)
argocd login 192.168.170.100 --username admin --password "$ARGOCD_PW" --insecure
```

Change the admin password after first login:
```bash
argocd account update-password
```

## verify Argo CD components
```bash
kubectl get pods -n argocd
kubectl get svc -n argocd
kubectl get all -n argocd
```

## troubleshoot / tips
- If the EXTERNAL-IP stays `<pending>`, check MetalLB pods and CRDs:
  ```bash
  kubectl get pods -n metallb-system
  kubectl get ipaddresspools -n metallb-system -o yaml
  ```

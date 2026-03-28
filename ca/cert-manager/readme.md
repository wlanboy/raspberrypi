# Install cert-manager in k3s with local CA

Installs and configures [cert-manager](https://cert-manager.io/) on a Kubernetes cluster using a self-hosted CA.
cert-manager automates the issuance and renewal of TLS certificates via a `ClusterIssuer` backed by your own CA key and certificate.

## Create namespace

```sh
kubectl create namespace cert-manager
```

## Add Helm repository

```sh
helm repo add jetstack https://charts.jetstack.io
helm repo update
```

## Install cert-manager

```sh
helm install \
  cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --set crds.enabled=true
```

## Create CA secret and ClusterIssuer

```sh
kubectl create secret tls my-local-ca-secret \
  --namespace cert-manager \
  --cert=/local-ca/ca.pem \
  --key=/local-ca/ca.key

cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: local-ca-issuer
spec:
  ca:
    secretName: my-local-ca-secret
EOF
```

## Test: issue a certificate

```sh
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-test-certificate
  namespace: istio-system
spec:
  secretName: my-test-certificate-secret
  duration: 2160h # 90d
  renewBefore: 360h # 15d
  commonName: api.gmk.lan
  isCA: false
  usages:
    - server auth
    - client auth
  dnsNames:
    - api.gmk.lan
    - test.api.gmk.lan
  issuerRef:
    name: local-ca-issuer
    kind: ClusterIssuer
EOF
```

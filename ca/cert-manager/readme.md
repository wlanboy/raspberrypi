# Install cert-manager in k3s with local ca

## cert-manager key and cert
```
kubectl create namespace cert-manager
```

## helm repro
```
helm repo add jetstack https://charts.jetstack.io
helm repo update
```

## helm install
```
kubectl create namespace cert-manager

helm install \
cert-manager jetstack/cert-manager \
--namespace cert-manager \
--set crds.enabled=true
```

## Set secret
```
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: local-ca-issuer
  namespace: cert-manager
spec:
  ca:
    secretName: my-local-ca-secret
EOF
```

## test
```
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-test-certificate
  namespace: default
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
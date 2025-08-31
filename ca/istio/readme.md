# use cert-manager with istio ingress gateway

# istio basic install
```
kubectl get ns istio-system &>/dev/null || kubectl create namespace istio-system
helm install istio-base istio/base -n istio-system --wait
helm install istiod istio/istiod -n istio-system --wait
```

# istio gateway install
```
kubectl get ns istio-ingress &>/dev/null || kubectl create namespace istio-ingress
helm install istio-ingressgateway istio/gateway -n istio-ingress --wait
```

# basic service
```
kubectl create namespace tester
kubectl label namespace tester istio-injection=enabled
kubectl create deployment tester --image=wlanboy/http-tester:latest -n tester
kubectl expose deployment tester --type=ClusterIP --port=5000 -n tester
```

# istio virtual service for service
Define Host and gateway in namespace istio-ingress. Export to tester and istio-ingress namespace
```
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: tester
  namespace: tester
spec:
  exportTo:
  - "tester"
  - "istio-ingress"
  hosts:
  - "tester.nuc.lan"
  - "tester2.nuc.lan"
  gateways:
  - istio-ingress/tester-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        port:
          number: 5000
        host: tester.tester.svc.cluster.local
EOF
```

# istio ingress gateway with tls
Create secret and define gateway in namespace istio-ingress for hostnames.
```
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: tester-gateway-cert
  namespace: istio-ingress
spec:
  secretName: tester-gateway-secret
  issuerRef:
    name: local-ca-issuer
    kind: ClusterIssuer
  dnsNames:
    - "tester.nuc.lan"
    - "tester2.nuc.lan"
EOF

kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: tester-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "tester.nuc.lan"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: tester-gateway-secret
    hosts:
      - "tester.nuc.lan"
      - "tester2.nuc.lan"
EOF
```

## have local /etc/host or pihole dns point to the public ip of the istio ingress gateway
```
kubectl get service -n istio-ingress 
NAME                   TYPE           CLUSTER-IP      EXTERNAL-IP       PORT(S)                                      AGE
istio-ingressgateway   LoadBalancer   10.43.233.201   192.168.100.100   15021:31200/TCP,80:31039/TCP,443:31032/TCP   48m

echo "192.168.100.100 tester.nuc.lan" | sudo tee -a /etc/hosts > /dev/null
echo "192.168.100.100 tester2.nuc.lan" | sudo tee -a /etc/hosts > /dev/null
```

## open browser with https://tester.nuc.lan
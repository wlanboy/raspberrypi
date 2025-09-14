# use tekton pipelines on k3s

## create namespace
```bash
kubectl create namespace tekton-pipelines
kubectl label namespace tekton-pipelines istio-injection=enabled --overwrite
kubectl label namespace tekton-pipelines \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/enforce-version=latest ## this is a workaround until tekton fixes their deployments
```

## enable audit for these violations
```bash
kubectl label namespace <your-namespace> \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

## install tekton and dashboard
```bash
kubectl apply -f https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml
kubectl wait --for=condition=ready pod -l app.kubernetes.io/part-of=tekton-pipelines -n tekton-pipelines --timeout=300s
kubectl apply -f https://storage.googleapis.com/tekton-releases/dashboard/latest/release-full.yaml
```

## restart deployments if policies do not allow pod creation
```bash
kubectl rollout restart deployment -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-pipelines
```

## if no pods are starting look at the deployments
```
    message: 'pods "tekton-*" is forbidden: violates PodSecurity
      "restricted:latest": unrestricted capabilities (container "istio-init" must
      not include "NET_ADMIN", "NET_RAW" in securityContext.capabilities.add), runAsNonRoot
      != true (container "istio-init" must not set securityContext.runAsNonRoot=false),
      runAsUser=0 (container "istio-init" must not set runAsUser=0), seccompProfile
      (pod or containers "istio-init", "istio-proxy" must set securityContext.seccompProfile.type
      to "RuntimeDefault" or "Localhost")'
```
- see: 

## install tekton triggers
```bash
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/release.yaml
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/interceptors.yaml
```

## virtual service and gateway for tekton dashboard
```bash
kubectl apply -n tekton-pipelines -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: tekton-dashboard-virtualservice
spec:
  hosts:
  - "tekton.gmk.lan"
  gateways:
  - istio-system/tekton-dashboard-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: tekton-dashboard.tekton-pipelines.svc.cluster.local
        port:
          number: 9097
EOF

kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: tekton-gateway-cert
  namespace: istio-ingress
spec:
  secretName: tekton-gateway-secret
  issuerRef:
    name: local-ca-issuer
    kind: ClusterIssuer
  dnsNames:
    - "tekton.nuc.lan"
    - "tekton.gmk.lan"
EOF

kubectl apply -n istio-system -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: tekton-dashboard-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "tekton.nuc.lan"
    - "tekton.gmk.lan"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: tekton-gateway-secret
    hosts:
    - "tekton.nuc.lan"
    - "tekton.gmk.lan"
EOF
```

## open dashboard
- https://tekton.gmk.lan

# trust for external ca
Example to inject an external ca to Istio sidecars.

See: https://preliminary.istio.io/latest/docs/reference/config/annotations/#SidecarUserVolume

## create namespace
```
kubectl create namespace test
kubectl label namespace test istio-injection=enabled
```

## create secret for ca
```
kubectl create secret generic external-ca --from-file=ca.crt=./ca.crt -n test
```

## get istio sidecar configmap
```
kubectl get configmap istio-sidecar-injector -n istio-system -o yaml > injector-patch.yaml
```

## add ca to istio sidecar template
add following lines after template.spec.volumes and after template.spec.containers[0].volumeMounts
```
volumes:
- name: external-ca
  secret:
    secretName: external-ca

volumeMounts:
- name: external-ca
  mountPath: /etc/external-ca
  readOnly: true
```

## or use the istio annotions within your deployment
```
apiVersion: apps/v1
kind: Deployment
...
spec:
  template:
    metadata:
      labels:
        app: tester
      annotations:
        sidecar.istio.io/userVolume: |
          [{"name":"external-ca","secret":{"secretName":"external-ca"}}]
        sidecar.istio.io/userVolumeMount: |
          [{"name":"external-ca","mountPath":"/etc/external-ca","readOnly":true}]
...
```

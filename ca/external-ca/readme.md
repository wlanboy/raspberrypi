# Trust for external CA in Istio

Injects a custom CA certificate into Istio sidecars so that services can trust TLS certificates signed by an external CA.
This is useful when internal services use certificates issued by a self-hosted CA that is not trusted by default.

See: <https://preliminary.istio.io/latest/docs/reference/config/annotations/#SidecarUserVolume>

## Create namespace

```sh
kubectl create namespace test
kubectl label namespace test istio-injection=enabled
```

## Create secret for CA

```sh
kubectl create secret generic external-ca --from-file=ca.crt=./ca.crt -n test
```

## Option A: Patch the Istio sidecar injector ConfigMap

Download the current sidecar injector config:

```sh
kubectl get configmap istio-sidecar-injector -n istio-system -o yaml > injector-patch.yaml
```

Add the following lines after `template.spec.volumes` and `template.spec.containers[0].volumeMounts`:

```yaml
volumes:
  - name: external-ca
    secret:
      secretName: external-ca

volumeMounts:
  - name: external-ca
    mountPath: /etc/external-ca
    readOnly: true
```

## Option B: Use Istio annotations in your Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
# ...
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
# ...
```

# k3s-tools

A collection of helper scripts for managing a k3s Kubernetes cluster.

## Requirements

- Python >= 3.12
- [uv](https://github.com/astral-sh/uv)

## Tools

### add-san.py

Manages `tls-san` entries in the k3s configuration file `/etc/rancher/k3s/config.yaml`.

When a new SAN (Subject Alternative Name) is added, the script automatically restarts k3s and
removes the existing API server certificates so that k3s generates new ones that include the
updated SAN list.

**Requires root privileges (`sudo`).**

#### Usage

```bash
# Show current tls-san entries
sudo uv run add-san.py

# Add an IP address
sudo uv run add-san.py 192.168.178.100

# Add a hostname
sudo uv run add-san.py myk3shost.lan
```

#### What it does when adding a SAN

1. Reads `/etc/rancher/k3s/config.yaml`
2. Adds the new entry under `tls-san:` (skips if already present)
3. Stops k3s: `systemctl stop k3s`
4. Removes the old API server certificate and key:
   - `/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt`
   - `/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.key`
5. Starts k3s again: `systemctl start k3s` — k3s regenerates the certificate with the new SAN

#### Example config result

```yaml
tls-san:
  - 100.64.1.1
  - 192.168.178.28
  - gmkchost.lan
```

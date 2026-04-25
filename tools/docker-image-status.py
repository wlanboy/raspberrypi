#!/usr/bin/env python3
"""
Check running Docker containers for newer image versions on Docker Hub / GHCR / custom registries.
Usage: python3 docker-image-status.py [--json]

Writes results to docker-image.status (JSON) in the same directory as this script.
"""

import subprocess
import json
import sys
import re
import urllib.request
import urllib.error
import datetime
import os

STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker-image.status")


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_running_containers():
    raw = run(["docker", "ps", "--format", "{{json .}}"])
    containers = []
    for line in raw.splitlines():
        if line.strip():
            containers.append(json.loads(line))
    return containers


def parse_image_ref(image_ref):
    """
    Returns (registry, repository, tag).
    Examples:
      nginx:latest          -> (docker.io, library/nginx, latest)
      myapp:1.2             -> (docker.io, library/myapp, 1.2)
      ghcr.io/foo/bar:v1    -> (ghcr.io, foo/bar, v1)
      192.168.1.1:5000/x:1 -> (192.168.1.1:5000, x, 1)
    """
    tag = "latest"
    if ":" in image_ref.split("/")[-1]:
        image_ref, tag = image_ref.rsplit(":", 1)

    # Detect registry: contains dot or colon before the first slash
    parts = image_ref.split("/")
    if len(parts) >= 2 and ("." in parts[0] or ":" in parts[0]):
        registry = parts[0]
        repository = "/".join(parts[1:])
    else:
        registry = "docker.io"
        # Docker Hub official images
        repository = image_ref if "/" in image_ref else f"library/{image_ref}"

    return registry, repository, tag


def get_remote_digest_dockerhub(repository, tag):
    """Fetch digest from Docker Hub without pulling the image."""
    # Get token
    auth_url = (
        f"https://auth.docker.io/token?service=registry.docker.io"
        f"&scope=repository:{repository}:pull"
    )
    with urllib.request.urlopen(auth_url, timeout=10) as resp:
        token = json.loads(resp.read())["token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json,"
                  "application/vnd.oci.image.manifest.v1+json,"
                  "application/vnd.docker.distribution.manifest.list.v2+json,"
                  "application/vnd.oci.image.index.v1+json",
    }
    manifest_url = f"https://registry-1.docker.io/v2/{repository}/manifests/{tag}"
    req = urllib.request.Request(manifest_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.headers.get("Docker-Content-Digest", "")


def get_remote_digest_generic(registry, repository, tag):
    """Fetch digest from a generic OCI-compliant registry (GHCR, self-hosted)."""
    manifest_url = f"https://{registry}/v2/{repository}/manifests/{tag}"
    headers = {
        "Accept": "application/vnd.docker.distribution.manifest.v2+json,"
                  "application/vnd.oci.image.manifest.v1+json,"
                  "application/vnd.docker.distribution.manifest.list.v2+json,"
                  "application/vnd.oci.image.index.v1+json",
    }
    req = urllib.request.Request(manifest_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.headers.get("Docker-Content-Digest", "")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Try anonymous token auth (GHCR-style)
            www_auth = e.headers.get("Www-Authenticate", "")
            token = _get_token_from_challenge(www_auth, repository)
            if token:
                req = urllib.request.Request(manifest_url, headers={
                    **headers,
                    "Authorization": f"Bearer {token}",
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.headers.get("Docker-Content-Digest", "")
        raise


def _get_token_from_challenge(www_auth, repository):
    """Parse Bearer challenge and fetch anonymous token."""
    realm = re.search(r'realm="([^"]+)"', www_auth)
    service = re.search(r'service="([^"]+)"', www_auth)
    scope = re.search(r'scope="([^"]+)"', www_auth)
    if not realm:
        return None
    url = realm.group(1)
    params = []
    if service:
        params.append(f"service={urllib.parse.quote(service.group(1))}")
    if scope:
        params.append(f"scope={urllib.parse.quote(scope.group(1))}")
    else:
        params.append(f"scope=repository:{repository}:pull")
    if params:
        url += "?" + "&".join(params)
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
        return data.get("token") or data.get("access_token")


import urllib.parse  # noqa: E402 (needed by _get_token_from_challenge)


def get_local_digest(container_id):
    """Return the digest of the image currently used by the container."""
    inspect = json.loads(run(["docker", "inspect", "--format", "{{json .}}", container_id]))
    repo_digests = inspect.get("Image", "")
    # Try to get RepoDigests from the image itself
    image_id = inspect["Image"]
    img_info = json.loads(run(["docker", "image", "inspect", "--format", "{{json .}}", image_id]))
    repo_digests = img_info.get("RepoDigests", [])
    # Return the sha256 image id as fallback
    return repo_digests, image_id


def check_container(container):
    name = container.get("Names", container.get("ID", "?"))
    image_ref = container.get("Image", "")
    cid = container.get("ID", "")

    registry, repository, tag = parse_image_ref(image_ref)

    result = {
        "name": name,
        "container_id": cid,
        "image": image_ref,
        "registry": registry,
        "repository": repository,
        "tag": tag,
        "local_digest": None,
        "remote_digest": None,
        "up_to_date": None,
        "error": None,
    }

    try:
        repo_digests, image_id = get_local_digest(cid)
        result["local_image_id"] = image_id[:19]

        # Find the matching repo digest for this tag
        local_digest = None
        for rd in repo_digests:
            if "@" in rd:
                local_digest = rd.split("@", 1)[1]
                break
        result["local_digest"] = local_digest

        # Fetch remote digest
        if registry == "docker.io":
            remote_digest = get_remote_digest_dockerhub(repository, tag)
        else:
            remote_digest = get_remote_digest_generic(registry, repository, tag)
        result["remote_digest"] = remote_digest

        if local_digest and remote_digest:
            result["up_to_date"] = local_digest == remote_digest
        else:
            result["up_to_date"] = None
            result["error"] = "Could not compare digests (local digest unavailable — image may have been pulled without a registry push)"

    except Exception as exc:
        result["error"] = str(exc)

    return result


def print_table(results):
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    col_name = max(len(r["name"]) for r in results) + 2
    col_img = max(len(r["image"]) for r in results) + 2

    header = f"{'CONTAINER':<{col_name}} {'IMAGE':<{col_img}} STATUS"
    print(header)
    print("-" * len(header))

    for r in results:
        if r["error"] and r["up_to_date"] is None:
            status = f"{YELLOW}UNKNOWN{RESET}  {r['error']}"
        elif r["up_to_date"] is True:
            status = f"{GREEN}UP TO DATE{RESET}"
        elif r["up_to_date"] is False:
            status = f"{RED}UPDATE AVAILABLE{RESET}"
        else:
            status = f"{YELLOW}UNKNOWN{RESET}"

        print(f"{r['name']:<{col_name}} {r['image']:<{col_img}} {status}")


def main():
    use_json = "--json" in sys.argv

    try:
        containers = get_running_containers()
    except subprocess.CalledProcessError as e:
        print(f"Error: cannot list containers: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    if not containers:
        print("No running containers found.")
        return

    results = []
    for c in containers:
        results.append(check_container(c))

    status = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "containers": results,
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

    if use_json:
        print(json.dumps(status, indent=2))
    else:
        print_table(results)
        print(f"\nStatus written to: {STATUS_FILE}")


if __name__ == "__main__":
    main()

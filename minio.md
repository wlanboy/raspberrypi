# Start MinIO on Raspberry Pi with Docker
MinIO is a high-performance, S3-compatible object storage solution, perfect for storing large amounts of unstructured data.

---
## Prerequisites
Before you begin, ensure that the following prerequisites are met:

* **Docker:** Docker must be installed on your Raspberry Pi. If not, please refer to the `docker.md` file in this repository for installation instructions.

---

## 1. Create Directory for MinIO Data

```bash
sudo mkdir -p /minio/data
sudo chown -R $USER:docker /minio/data
```

## 2. Start minio

```bash
docker run -p 9000:9000 -p 9001:9001 \
  --name minio \
  -v ~/minio/data:/data \
  -e "MINIO_ROOT_USER=YOUR_MINIO_ROOT_USER" \
  -e "MINIO_ROOT_PASSWORD=YOUR_MINIO_ROOT_PASSWORD" \
  quay.io/minio/minio \
  server /data --console-address ":9001"
```

## 3. Access minio webfrontend
- http://<YOUR-PI-IP-ADDRESS>:9000

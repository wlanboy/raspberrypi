# Docker/Podman Volume Backup/Restore Tool

A Python CLI tool to backup, list, delete, and restore Docker or Podman volumes using a temporary Alpine container.

## Requirements

- Python 3.10+
- Docker or Podman

## Usage

```bash
python3 docker-volumes-backup.py [--runtime docker|podman] <command> [options]
```

### Global Options

| Option              | Description                                         |
| ------------------- | --------------------------------------------------- |
| `--runtime RT`      | Force runtime: `docker` or `podman` (default: auto) |

The runtime is auto-detected: `docker` is tried first, then `podman`. If neither is running, the tool exits with an error.

## Commands

### `backup` — Backup one or all volumes

```bash
# Backup all volumes
python3 docker-volumes-backup.py backup

# Backup a specific volume
python3 docker-volumes-backup.py backup --volume mydata

# Custom output directory
python3 docker-volumes-backup.py backup --volume mydata --output /mnt/backups
```

| Option           | Default            | Description                        |
| ---------------- | ------------------ | ---------------------------------- |
| `--volume NAME`  | *(all)*            | Name of the volume to back up      |
| `--output DIR`   | `./docker-backups` | Directory where backups are stored |

Backups are saved as `<volume-name>_<YYYYMMDD_HHMMSS>.tar.gz`.

---

### `list` — List available backups

```bash
python3 docker-volumes-backup.py list

python3 docker-volumes-backup.py list --output /mnt/backups
```

| Option          | Default            | Description                    |
| --------------- | ------------------ | ------------------------------ |
| `--output DIR`  | `./docker-backups` | Directory to scan for backups  |

---

### `volumes` — List all Docker volumes

```bash
python3 docker-volumes-backup.py volumes
```

Shows all existing volumes with their driver and the containers currently using them. Volumes in use are highlighted in green.

Example output:

```text
Volume                                   Driver       Containers
---------------------------------------------------------------------------
mydata                                   local        my-app, my-worker
postgres_data                            local        -
```

---

### `delete` — Delete a Docker volume

```bash
# With confirmation prompt
python3 docker-volumes-backup.py delete --volume mydata

# Skip confirmation
python3 docker-volumes-backup.py delete --volume mydata --force
```

| Option          | Default      | Description                    |
| --------------- | ------------ | ------------------------------ |
| `--volume NAME` | *(required)* | Name of the volume to delete   |
| `--force`       | `false`      | Skip the confirmation prompt   |

> **Note:** If the volume is currently mounted by a running container, the tool will refuse to delete it and print the container name.

---

### `restore` — Restore a volume from a backup file

```bash
python3 docker-volumes-backup.py restore \
  --volume mydata \
  --file /mnt/backups/mydata_20260409_120000.tar.gz
```

| Option               | Default      | Description                            |
| -------------------- | ------------ | -------------------------------------- |
| `--volume NAME`      | *(required)* | Target volume name (created if missing)|
| `--file BACKUP_FILE` | *(required)* | Path to the `.tar.gz` backup file      |

If the target volume already exists, a confirmation prompt is shown before overwriting.

---

## Typical Workflow

```bash
# 1. Check existing volumes (auto-detects docker or podman)
python3 docker-volumes-backup.py volumes

# Force podman
python3 docker-volumes-backup.py --runtime podman volumes

# 2. Backup before migration
python3 docker-volumes-backup.py backup --volume mydata --output /mnt/backups

# 3. Verify backup exists
python3 docker-volumes-backup.py list --output /mnt/backups

# 4. Delete the volume
python3 docker-volumes-backup.py delete --volume mydata

# 5. Restore from backup
python3 docker-volumes-backup.py restore \
  --volume mydata \
  --file /mnt/backups/mydata_20260409_120000.tar.gz
```

## How It Works

Backup and restore operations run a short-lived Alpine container that mounts
the volume and the local backup directory:

- **Backup:** `tar czf` archives the volume contents into the backup directory.
- **Restore:** `tar xzf` extracts the archive into a freshly created volume.

### Safety checks

| Situation                              | Behavior                                      |
| -------------------------------------- | --------------------------------------------- |
| Runtime not running                    | Error before any operation                    |
| Volume in use during `backup`          | Warning printed, backup continues             |
| Volume in use during `delete`          | Error, operation refused                      |
| Target volume exists during `restore`  | Confirmation prompt before overwrite          |

No data leaves the local machine. No additional dependencies are required
beyond Docker or Podman.

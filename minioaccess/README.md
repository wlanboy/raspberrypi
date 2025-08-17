# simple minio web manager for user and buckets of minio community edition
* uses mc client for access to the admin api

## get uv - makes python life easier
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## run
```
uv sync
uv run main.py
```

### from scratch
- uv init chat
- cd chat
- uv sync
- uv pip compile pyproject.toml -o requirements.txt
- uv pip install -r requirements.txt
- uv run main.pys

### get local mc client
```
sh getclient.sh
```

## Docker build
```
docker build -t minioweb .
```

## set env vars
```
export MINIO_ACCESS_KEY=xxxxxx
export MINIO_SECRET_KEY=xxxxxx
```

## Docker run 
```
docker run --rm -p 9002:9002 -e MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY -e MINIO_SECRET_KEY=$MINIO_SECRET_KEY minioweb
```

## Docker run daemon 
```
docker run --name jobs -d -p 9002:9002 -e MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY -e MINIO_SECRET_KEY=$MINIO_SECRET_KEY --restart unless-stopped wlanboy/minioweb
```
# simple local chat

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

## Docker build
```
docker build -t chat .
```

## Docker run
```
docker run -p 2000:2000 chat
```

## Docker run daemon
```
docker run --name chat -d -p 2000:2000 --restart unless-stopped chat
```
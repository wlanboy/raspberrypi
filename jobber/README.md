# simple job docker run manager
* uses sqlite for persistence
* uses docker to run jobs

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
docker build -t jobs .
```

## Docker run
```
docker run -p 2100:2100 jobs
```

## Docker run daemon
```
docker run --name jobs -d -p 2100:2100 --restart unless-stopped jobs
```
# Simple Local Chat

A lightweight, self-hosted chat application using Python WebSockets. Designed for local network use — no external services or accounts required.

## Install uv

[uv](https://github.com/astral-sh/uv) is a fast Python package manager that simplifies dependency management:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Run

```bash
uv sync
uv run main.py
```

### From Scratch

```bash
uv lock --upgrade
uv run pyright
uv run ruff check
uv sync
uv pip compile pyproject.toml -o requirements.txt
uv run main.py
```

## Docker Build

```bash
docker build -t chat .
```

## Docker Run

```bash
docker run --rm -p 2000:2000 chat
```

## Docker Run as Daemon

```bash
docker run --name chat -d -p 2000:2000 --restart unless-stopped chat
```

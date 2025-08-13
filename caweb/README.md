# simple local ssl cert web ui
* expects ca files in /local-ca
* generates subfolder for each requested hostname

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
- uv init osweb
- cd osweb
- uv add flask
- uv add waitress
- uv sync
- uv run main.pys

## Docker build
```
docker build -t caweb .
```

## Docker run
```
docker run -p 2000:2000 -v /local-ca:/local-ca caweb
```

## Docker run daemon
```
docker run --name caweb -d -p 2000:2000 -v /local-ca:/local-ca --restart unless-stopped caweb
```
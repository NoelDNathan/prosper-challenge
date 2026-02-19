
Build normal:
```
docker build -t my-pipecat-bot .

```
Build normal en windows:
docker build --platform=linux/arm64 -t my-pipecat-bot .

Ejecutar el contenedor:
docker run --rm my-pipecat-bot python bot.py
docker run --platform=linux/arm64 --rm my-pipecat-bot python bot.py


variables de entorno:

docker run --rm my-pipecat-bot python bot.py



uv run pytest -m live tests/test_healthie_live.py

uv run python -m pytest -s -vv -m live tests/test_healthie_live.py -o log_cli=true -o log_cli_level=INFO
A file to save some commands I used
****
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

uv sync --python /usr/bin/python3.12
uv run python3 bot.py

uv run pytest -m live tests/test_healthie_live.py

uv run python -m pytest -s -vv -m live tests/test_healthie_live.py -o log_cli=true -o log_cli_level=INFO

uv run python -m pytest -s -vv -m live tests/test_healthie_live.py::test_find_patient_live_returns_expected -o log_cli=true -o log_cli_level=INFO

uv run python -m pytest -s -vv -m live tests/test_healthie_live.py::test_create_appointment_success -o log_cli=true -o log_cli_level=INFO


uv run python -m pytest -s -vv -m live tests/test_healthie_live.py::test_create_appointment_another_event_scheduled_at_this_time -o log_cli=true -o log_cli_level=INFO

playwright codegen https://secure.gethealthie.com

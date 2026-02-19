problemas instalando la libreria: no me funcionaba, no había version en windows. Intente usar docker pero tampoco. Acabe usando wsl

Me funciona el leer un usuario pero al dia siguiente añadieron el doble factor de autenticidad

Entonces leyendo el gmail daba problemas porque había un color que era #999999, el css daba problema.


### Live Healthie Tests

You can exercise the real Healthie UI by running the live integration suite that covers `healthie.find_patient()`:

```bash
pytest -m live tests/test_healthie_live.py
```

The pytest marker ensures these tests only run when explicitly requested. They require real Healthie credentials, so make sure `HEALTHIE_EMAIL` and `HEALTHIE_PASSWORD` are populated via your local `.env` (do **not** commit that file with secrets). The tests skip automatically if the environment variables are missing and will fail fast if the account cannot authenticate.
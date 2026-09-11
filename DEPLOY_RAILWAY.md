# Desplegar en Railway

1. Creá un servicio desde este repositorio.
2. Montá un Volume con mount path `/data`.
3. Definí las variables de `.env.example` en la sección **Variables**.
4. Usá `Dockerfile` como builder y `python latambot.py` como comando de inicio.
5. Verificá los logs y `/api/health` si exponés el puerto del dashboard.

No cargues `.env` como archivo del repositorio. Los secretos deben vivir en las variables de
Railway. El volumen conserva `datos.json` y `latambot.sqlite3` entre despliegues.

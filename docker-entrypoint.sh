#!/bin/sh
# ==============================================================================
# Entrypoint de LatamBOT
# Siembra la base de datos en el volumen persistente (DATA_DIR) la primera vez,
# copiando los archivos que vienen en la imagen si el volumen está vacío.
# Así tus configuraciones del backup sobreviven a los redeploys de Railway.
# ==============================================================================
set -e

if [ -n "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    for f in latambot.sqlite3 datos.json; do
        if [ -f "/app/$f" ] && [ ! -f "$DATA_DIR/$f" ]; then
            cp "/app/$f" "$DATA_DIR/$f"
            echo "[entrypoint] Sembrado $f -> $DATA_DIR/$f"
        fi
    done
fi

exec "$@"

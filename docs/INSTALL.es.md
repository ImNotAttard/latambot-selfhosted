# Instalación y operación de LatamBOT

Esta guía instala una instancia independiente. No conecta con la infraestructura oficial ni
importa datos de otra instalación.

## Arquitectura y directorios

El contenedor ejecuta el bot y el dashboard en el mismo proceso. `DATA_DIR` contiene los datos
persistentes; en Compose se monta el volumen `latambot_data` en `/data`. El código de la
aplicación debe tratarse como inmutable durante la operación y los secretos deben vivir fuera del
repositorio.

Antes de instalar, decidí quién administrará el host, dónde se guardarán los backups y qué
integraciones externas están permitidas. Una instalación mínima puede funcionar solo con Discord;
cada proveedor adicional agrega sus propios límites, costos, términos y riesgos.

## 1. Crear el bot en Discord

1. Entrá al Discord Developer Portal y creá una **New Application**.
2. En **Bot**, creá el usuario bot, copiá el token una sola vez y guardalo en un gestor de
   secretos. Si se filtra, regeneralo inmediatamente.
3. Activá **Server Members Intent** y **Message Content Intent**.
4. En **OAuth2 > URL Generator**, elegí `bot` y `applications.commands`. Concedé solo los
   permisos que uses: ver canales, enviar mensajes, insertar enlaces y adjuntar archivos; para
   moderación agregá administrar mensajes; para música agregá conectar y hablar.
5. Invitá el bot a un servidor de prueba antes de usarlo en producción.

## 2. Configurar variables

Copiá `.env.example` y completá como mínimo:

```bash
cp .env.example .env
chmod 600 .env
```

`DISCORD_TOKEN` es obligatorio. `DATA_DIR` debe apuntar a almacenamiento persistente. Para el
panel OAuth definí también `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`,
`DASHBOARD_BASE_URL` y un `DASHBOARD_SESSION_SECRET` aleatorio de al menos 32 caracteres.
Registrá `DASHBOARD_BASE_URL/auth/callback` como redirect URI en Discord. Las APIs de IA,
imágenes, búsqueda, R2 y webhooks son opcionales.

Generá secretos propios para cada ambiente. No reutilices el token de otra instancia ni pegues
credenciales en issues, logs, capturas o archivos de configuración versionados.

## Docker Compose

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8080/api/health
```

El panel queda local en `127.0.0.1:8080`. Para exponerlo, usá un proxy HTTPS y cambiá
`DASHBOARD_BASE_URL`; no expongas directamente el puerto de desarrollo a Internet.

Para una primera prueba, abrí otro terminal y comprobá:

```bash
docker compose logs --tail=100 latambot
curl --fail http://127.0.0.1:8080/api/health
```

El proceso debe mantener una conexión activa con Discord y el endpoint de health debe responder
sin publicar tokens ni secretos.

Logs y diagnóstico:

```bash
docker compose logs -f latambot
docker compose exec latambot sh
```

Actualización:

```bash
docker compose run --rm latambot python tools/check_public_tree.py
docker compose pull
docker compose up -d --build
```

Antes de actualizar, respaldá el volumen `latambot_data`. No uses `docker compose down -v`
si querés conservar la configuración.

## Linux sin Docker

Instalá Python 3.12, `ffmpeg` y las fuentes usadas para generar imágenes. Creá un entorno virtual,
instalá `requirements.txt`, copiá `.env.example` a `.env`, definí `DATA_DIR` y ejecutá:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python latambot.py
```

Para producción, ejecutá el proceso con un supervisor como systemd, almacená el `.env` fuera del
repositorio con permisos restringidos y configurá reinicio automático. Asegurate de que el usuario
del servicio pueda escribir en `DATA_DIR`, pero no en el código de la aplicación.

Antes de usar systemd, verificá manualmente el arranque con el mismo usuario del servicio. Usá
rutas absolutas, un `WorkingDirectory` fijo y un archivo de entorno con permisos `600`.

## Raspberry Pi

Usá una Raspberry Pi de 64 bits, almacenamiento persistente, refrigeración y una fuente estable.
Docker Compose es el método recomendado. En ARM, algunas funciones de medios dependen de
binarios disponibles para la arquitectura; verificá `docker compose build` antes de activar
descargas o música. No uses una microSD deteriorada como único almacenamiento de datos.

## Railway

Creá un servicio desde el repositorio, definí las variables de `.env.example` y montá un volumen
en `/data`. Configurá la URL pública generada por Railway como `DASHBOARD_BASE_URL` y registrá su
callback OAuth en Discord. Railway puede dormir o reiniciar servicios según el plan; revisá sus
límites y la persistencia antes de usarlo como hosting principal.

## Backups y restauración

En Docker:

```bash
mkdir -p backups
docker run --rm -v latambot_data:/data -v "$PWD/backups:/backups" \
  alpine tar -czf /backups/latambot-data.tar.gz -C /data .
```

Guardá el backup fuera del host. Para restaurar, detené el bot, extraé el archivo sobre el volumen
y reiniciá. Verificá que la restauración funciona antes de depender de ella.

Conservá varias generaciones de backups y cifralas si contienen datos de usuarios. Un backup
válido debe incluir la configuración persistente, pero nunca debe convertirse en una forma de
distribuir tokens o claves privadas.

## Troubleshooting

- **Token inválido:** regeneralo en Discord y actualizá solo el secreto de la instalación.
- **Bot offline:** comprobá token, intents, reloj del sistema, red saliente y logs.
- **Comandos ausentes:** esperá la sincronización global o invitá el bot con
  `applications.commands`.
- **Panel sin login:** verificá callback OAuth, URL pública, cookies seguras y secret de sesión.
- **Música/descargas fallan:** instalá `ffmpeg`, revisá arquitectura y las APIs opcionales.
- **Datos perdidos:** no uses `down -v`; restaurá el volumen desde un backup.
- **Reinicios repetidos:** revisá `docker compose ps`, el código de salida y la memoria/disco del
  host; no ocultes el problema con un bucle de reinicios.

## Seguridad y mantenimiento

- Usá tokens separados para desarrollo y producción.
- No compartas `.env`, logs con credenciales, cookies, SQLite ni backups sin cifrar.
- Limitá permisos del bot y del usuario Linux.
- Actualizá dependencias y revisá cambios antes de desplegar.
- Cumplí los términos de Discord, las licencias de servicios externos y la legislación aplicable.
- Probá la restauración y el procedimiento de rotación antes de necesitarlos.

# LatamBOT self-hosted

Edición portable de LatamBOT para ejecutar tu propio bot de Discord y su panel web. Esta copia no
incluye tokens, datos de producción, cookies, claves SSH ni configuración de la infraestructura
oficial.

> **Estado:** proyecto comunitario self-hosted. Cada instalación usa su propio bot, sus propios
> datos y sus propios servicios externos. El mantenimiento, los costos y el cumplimiento de las
> reglas de Discord quedan a cargo de quien lo instala.

## Inicio rápido con Docker Compose

```bash
cp .env.example .env
# Editá .env y definí DISCORD_TOKEN; no lo compartas ni lo subas a Git.
docker compose up -d --build
docker compose logs -f latambot
```

El panel queda disponible en `http://127.0.0.1:8080`. La configuración se guarda en el volumen
`latambot_data`, montado en `/data`.

## Qué incluye

- Bot de Discord y comandos de moderación, configuración, música, descargas y utilidades
  disponibles en el código.
- Panel web con OAuth2 opcional, persistencia local y healthcheck.
- Persistencia configurable en Docker, Linux, Railway y Raspberry Pi de 64 bits.
- Integraciones externas opcionales: IA, búsquedas, imágenes, almacenamiento R2, webhooks y nodo
  de descargas.

## Requisitos previos

Necesitás una aplicación creada en el [Discord Developer Portal](https://discord.com/developers/applications),
Python 3.12 si no usás Docker, `ffmpeg` para funciones multimedia y almacenamiento persistente.
Para producción, usá un dominio HTTPS delante del panel y un proxy inverso como Caddy o nginx.

En Discord, activá **Server Members Intent** y **Message Content Intent** en la sección
**Bot > Privileged Gateway Intents**. Invitá el bot con los permisos mínimos que requieran los
comandos: leer y enviar mensajes, insertar enlaces, adjuntar archivos, administrar mensajes y
conectar/hablar en voz solo si vas a usar música. No otorgues Administrator salvo que sea necesario.

El dashboard requiere además una aplicación OAuth2 y `DISCORD_CLIENT_ID`,
`DISCORD_CLIENT_SECRET`, `DASHBOARD_BASE_URL` y `DASHBOARD_SESSION_SECRET`. Registrá en Discord
la URL exacta `DASHBOARD_BASE_URL/auth/callback`.

## Integraciones opcionales

Groq, OpenRouter, SerpAPI, TMDB, TheCatAPI, R2, webhooks y el nodo de descargas son opcionales.
Sin sus variables, las funciones dependientes muestran un error explicativo y el resto del bot
continúa funcionando. Revisá `.env.example` para conocer todas las variables disponibles y nunca
uses credenciales de producción en desarrollo.

## Otras instalaciones

- `docs/INSTALL.es.md`: guía completa en español, incluyendo Discord, Docker, Linux, Railway,
  Raspberry Pi, backups y troubleshooting.
- `docs/INSTALL.en.md`: complete English installation guide.
- `DEPLOY_RAILWAY.md`: referencia específica para Railway.

## Primer arranque y comprobación

```bash
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
docker compose logs --tail=100 latambot
```

Si el bot no aparece online, revisá primero `DISCORD_TOKEN`, los intents privilegiados y los
permisos de salida de la máquina. Si el panel falla, comprobá `DASHBOARD_BASE_URL`, el callback
OAuth y que `DASHBOARD_SESSION_SECRET` tenga al menos 32 caracteres.

## Persistencia y backups

No borres el volumen `latambot_data` durante una actualización. Para hacer un backup:

```bash
docker run --rm -v latambot_data:/data -v "$PWD/backups:/backups" \
  alpine tar -czf /backups/latambot-data.tar.gz -C /data .
```

Para restaurarlo, detené el servicio, extraé el archivo sobre un volumen vacío y volvé a iniciar
el Compose. Probá periódicamente la restauración; un backup que nunca se prueba no es confiable.

## Actualización segura

1. Hacé un backup del volumen.
2. Revisá los cambios y actualizá la imagen o el checkout.
3. Ejecutá `docker compose up -d --build`.
4. Comprobá `/api/health`, los logs y el estado del bot en Discord.
5. Conservá la versión anterior hasta confirmar que la instalación funciona.

## Estado del proyecto

No subas `.env`, bases de datos, cookies, claves privadas ni logs con tokens. Antes de publicar
una modificación, ejecutá `python tools/check_public_tree.py` y los tests del proyecto.

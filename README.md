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

## Cómo funciona

La instalación se ejecuta como un único proceso: el bot mantiene la conexión con Discord y el
servidor web expone el dashboard y `/api/health`. Los datos de configuración y estado se guardan
en `DATA_DIR`; en Docker, el volumen `latambot_data` se monta en `/data`. Las credenciales se
leen desde variables de entorno y no se escriben intencionalmente dentro del repositorio.

El flujo recomendado es:

1. Crear una aplicación y un bot propios en Discord.
2. Configurar el token, el directorio persistente y, si hace falta, OAuth2.
3. Probar el bot en un servidor privado.
4. Activar únicamente las integraciones externas que realmente uses.
5. Hacer backups antes de actualizar o cambiar de host.

La instancia self-hosted es independiente: sus límites, costos de APIs, moderación, disponibilidad
y cumplimiento de las políticas de Discord dependen de su operador.

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

## Configuración mínima y configuración de producción

Para una prueba local solo se necesita `DISCORD_TOKEN`. Para producción se recomienda definir
también `DATA_DIR`, `DASHBOARD_BASE_URL`, `DASHBOARD_SESSION_SECRET` y las variables OAuth si se
va a usar el panel. Las claves de IA, búsqueda, almacenamiento, webhooks y el nodo de descargas
son independientes; dejar una vacía desactiva solamente la función que depende de ella.

No copies el `.env` de otra instalación. Generá secretos nuevos, restringí el acceso al archivo y
rotalos si aparecen en un log, captura de pantalla, backup o commit.

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

## Lista de comprobación antes de exponerlo a Internet

- `DASHBOARD_BASE_URL` usa HTTPS y coincide exactamente con el callback registrado en Discord.
- El puerto de desarrollo no está publicado directamente sin proxy.
- `DASHBOARD_SESSION_SECRET` es aleatorio y tiene al menos 32 caracteres.
- El bot no tiene `Administrator` si no lo necesita.
- El volumen y los backups están protegidos por permisos del sistema.
- Hay una política de rotación de tokens y una prueba de restauración.
- Las funciones que dependen de APIs externas tienen límites y costos revisados.

## Limitaciones conocidas

La compatibilidad de funciones multimedia depende de `ffmpeg`, `yt-dlp`, la arquitectura y los
proveedores externos. Raspberry Pi funciona mejor en 64 bits, pero no todas las herramientas
externas ofrecen el mismo soporte en ARM. Railway y otros hosts administrados pueden reiniciar,
dormir o limitar servicios según el plan. Probá las funciones que necesitás en tu hardware antes
de migrar una instalación completa.

## Estado del proyecto

No subas `.env`, bases de datos, cookies, claves privadas ni logs con tokens. Antes de publicar
una modificación, ejecutá `python tools/check_public_tree.py` y los tests del proyecto.

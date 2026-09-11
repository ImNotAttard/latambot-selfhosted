# LatamBOT installation and operations

This guide deploys an independent instance. It does not connect to official infrastructure or
import data from another installation.

## Architecture and directories

The container runs the bot and dashboard in one process. `DATA_DIR` contains persistent data; in
Compose, the `latambot_data` volume is mounted at `/data`. Treat application source as immutable
while the service is running and keep secrets outside the repository.

Before installing, decide who operates the host, where backups will be stored, and which external
integrations are allowed. A minimal installation can run with Discord alone; every additional
provider adds its own limits, costs, terms, and risk.

## 1. Create the Discord bot

1. Open the Discord Developer Portal and create a **New Application**.
2. Under **Bot**, create the bot user, copy its token once, and store it in a secret manager. If
   it leaks, regenerate it immediately.
3. Enable **Server Members Intent** and **Message Content Intent**.
4. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands`. Grant only the
   permissions you use: view channels, send messages, embed links, and attach files; add manage
   messages for moderation and connect/speak for music.
5. Invite the bot to a test server before production use.

## 2. Configure environment variables

Copy `.env.example` to `.env`, keep it mode `600`, and set at least `DISCORD_TOKEN` and a
persistent `DATA_DIR`. Dashboard OAuth also requires `DISCORD_CLIENT_ID`,
`DISCORD_CLIENT_SECRET`, `DASHBOARD_BASE_URL`, and a random `DASHBOARD_SESSION_SECRET` of at least
32 characters. Register `DASHBOARD_BASE_URL/auth/callback` in Discord. AI, image, search, R2,
webhook, and download-node integrations are optional.

Generate separate secrets for each environment. Never reuse another installation's token or paste
credentials into issues, logs, screenshots, or versioned configuration.

## Docker Compose

```bash
cp .env.example .env
chmod 600 .env
docker compose up -d --build
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
```

The dashboard binds locally to `127.0.0.1:8080`. Put an HTTPS reverse proxy in front of it before
public exposure and update `DASHBOARD_BASE_URL`; do not expose the development port directly.

For a first-run check:

```bash
docker compose logs --tail=100 latambot
curl --fail http://127.0.0.1:8080/api/health
```

The process should maintain an active Discord connection, and the health endpoint must not expose
tokens or other secrets.

For upgrades, back up the `latambot_data` volume first, then run `docker compose up -d --build`.
Never run `docker compose down -v` unless you intend to delete the data.

## Linux without Docker

Install Python 3.12, `ffmpeg`, and the fonts required by image features. Create a virtual
environment, install `requirements.txt`, configure `.env`, set `DATA_DIR`, and run
`python latambot.py`. Use systemd or another supervisor for production deployments. Keep the
environment file outside the repository and make sure the service user can write to `DATA_DIR`
but not the application source tree.

Before creating a systemd unit, run the process manually as the service user. Use absolute paths,
a fixed `WorkingDirectory`, and an environment file with mode `600`.

## Raspberry Pi

Use a 64-bit Raspberry Pi with stable power, cooling, and persistent storage. Docker Compose is
recommended. Some media features depend on architecture-specific binaries, so verify the image
build before enabling downloads or music. Do not use a failing microSD card as the only copy of
your data.

## Railway

Deploy from the repository, mount a volume at `/data`, and configure the variables from
`.env.example` in Railway. Set `DASHBOARD_BASE_URL` to the public Railway URL and register its
OAuth callback in Discord. Check plan limits, sleep behavior, and persistence before using it as
your primary host.

## Backups and restore

Back up the Docker volume regularly and store the archive outside the host:

```bash
mkdir -p backups
docker run --rm -v latambot_data:/data -v "$PWD/backups:/backups" \
  alpine tar -czf /backups/latambot-data.tar.gz -C /data .
```

Test restoration before relying on a backup. Never delete the volume during routine upgrades.
Keep multiple backup generations and encrypt archives if they contain user data. A valid backup
should include persistent application data, never tokens or private keys.

## Troubleshooting

- **Invalid token:** regenerate it in Discord and update only the installation secret.
- **Bot offline:** check token, intents, system clock, outbound network, and logs.
- **Missing commands:** wait for global synchronization or invite with `applications.commands`.
- **Dashboard login failure:** check the OAuth callback, public URL, cookies, and session secret.
- **Media failures:** install `ffmpeg`, verify architecture, and configure optional APIs.
- **Lost data:** do not use `down -v`; restore the volume from a backup.
- **Repeated restarts:** inspect `docker compose ps`, exit codes, memory, and disk space instead of
  hiding the problem with an unlimited restart loop.

## Security and maintenance

- Use separate Discord tokens for development and production.
- Never commit `.env`, databases, cookies, private keys, or logs containing secrets.
- Generate a random `DASHBOARD_SESSION_SECRET` of at least 32 bytes.
- Register the exact OAuth redirect URI before enabling dashboard OAuth.
- Review bot permissions and keep dependencies updated.
- Rotate leaked tokens immediately and follow Discord terms and third-party service licenses.
- Test restoration and secret rotation before you need either procedure.

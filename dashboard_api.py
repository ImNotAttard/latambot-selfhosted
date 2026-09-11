"""API + servidor web del dashboard de LatamBOT.

Corre dentro del proceso del bot (mismo event loop). Expone:
  - OAuth2 con Discord (login/callback/logout)
  - /api/me, /api/guild/{gid} (GET/PATCH), /api/guild/{gid}/action
  - sirve la SPA estática desde dashboard_web/

Sin dependencias nuevas: solo aiohttp (ya presente) + stdlib.
"""
import os
import sys
import json
import time
import datetime
import hmac
import hashlib
import base64
import secrets
import importlib

import aiohttp
import discord
from aiohttp import web

import dashboard_schema as schema

# ── Config (env) ──────────────────────────────────────────────────────────────
CLIENT_ID      = os.getenv("DISCORD_CLIENT_ID", "").strip()
CLIENT_SECRET  = os.getenv("DISCORD_CLIENT_SECRET", "")
BASE_URL       = os.getenv("DASHBOARD_BASE_URL", "http://localhost:8080").rstrip("/")
# Nunca firmar sesiones con secret vacío/corto (forja trivial).
_sess_raw = (os.getenv("DASHBOARD_SESSION_SECRET") or "").strip()
if len(_sess_raw) < 32:
    _sess_raw = secrets.token_hex(32)
    print("[DASHBOARD] SESSION_SECRET ausente o corto: usando uno efimero (sesiones mueren al reiniciar).")
SESSION_SECRET = _sess_raw.encode()
OWNER_ONLY     = os.getenv("DASHBOARD_OWNER_ONLY", "true").lower() in ("1", "true", "yes")
OWNER_ID       = int(os.getenv("OWNER_ID", "0") or "0")
PORT           = int(os.getenv("DASHBOARD_PORT", "8080"))
WEB_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_web")
SESSION_TTL    = 7 * 24 * 3600
CODE_SESSION_TTL = 24 * 3600  # login por codigo: 24h (antes 30 dias)
DISCORD_API    = "https://discord.com/api"
# Server al que se auto-unen los que entran con Discord (LatamSupport). Requiere
# scope guilds.join + que el bot esté en ese server con permiso Crear Invitación.
AUTOJOIN_GUILD_ID = int(os.getenv("AUTOJOIN_GUILD_ID", "0") or "0")
ASSET_VER      = str(int(time.time()))  # cambia en cada arranque/deploy -> cache-busting

PERM_ADMIN  = 0x8
PERM_MANAGE = 0x20


def _botmod():
    """Devuelve el módulo del bot YA cargado.

    latambot.py corre como __main__, así que importarlo por nombre crearía una
    segunda copia y re-ejecutaría bot.run(). Por eso usamos el __main__ vivo si
    tiene las funciones esperadas; solo caemos a import_module en tests.
    """
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "get_config") and hasattr(main, "update_server_config"):
        return main
    if "latambot" in sys.modules:
        return sys.modules["latambot"]
    return importlib.import_module("latambot")


# ── Sesiones firmadas (HMAC) ──────────────────────────────────────────────────
def _b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign_session(payload: dict, ttl: int = SESSION_TTL) -> str:
    payload = dict(payload)
    payload["exp"] = int(time.time()) + ttl
    raw = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64e(hmac.new(SESSION_SECRET, raw.encode(), hashlib.sha256).digest())
    return f"{raw}.{sig}"


def _read_session(cookie: str):
    try:
        raw, sig = cookie.split(".", 1)
        expected = _b64e(hmac.new(SESSION_SECRET, raw.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_b64d(raw))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


def _get_session(request):
    c = request.cookies.get("lb_session")
    return _read_session(c) if c else None


def _discord_avatar_url(uid, avatar):
    """Devuelve URL completa del avatar de Discord.
    `avatar` puede ser hash OAuth, URL completa (login por codigo) o None."""
    if avatar and str(avatar).startswith("http"):
        return str(avatar)
    try:
        uid_i = int(uid)
    except (TypeError, ValueError):
        return None
    if not avatar:
        # Default avatar (sistema de usernames nuevos)
        return f"https://cdn.discordapp.com/embed/avatars/{(uid_i >> 22) % 6}.png"
    ext = "gif" if str(avatar).startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{uid_i}/{avatar}.{ext}?size=64"


# ── Login por código (generado en Discord con l!panel) ────────────────────────
_codes = {}            # code -> {"gid","uid","u","av","exp"}
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O/1/I


def register_code(gid, uid, username=None, avatar=None, ttl=900):
    """Crea un código de un solo uso para entrar al panel de ese servidor."""
    # limpiar expirados
    now = time.time()
    for k in [k for k, v in _codes.items() if v["exp"] < now]:
        _codes.pop(k, None)
    code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
    _codes[code] = {"gid": int(gid), "uid": int(uid), "u": username, "av": avatar, "exp": now + ttl}
    return code


def redeem_code(code):
    code = (code or "").strip().upper().replace(" ", "")
    data = _codes.get(code)
    if not data:
        return None
    if data["exp"] < time.time():
        _codes.pop(code, None)
        return None
    _codes.pop(code, None)  # un solo uso
    return data


def _set_session_cookie(resp, payload, ttl: int = SESSION_TTL):
    resp.set_cookie("lb_session", _sign_session(payload, ttl), max_age=ttl,
                    httponly=True, secure=True, samesite="Lax", path="/")


# ── Rate limiting simple (en memoria, por IP) ─────────────────────────────────
_rate_buckets = {}


def _client_ip(request):
    # detrás de Cloudflare: la IP real viene en CF-Connecting-IP
    return (request.headers.get("CF-Connecting-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.remote or "?"))


def _rate_ok(request, scope="w", limit=40, window=60):
    key = f"{scope}:{_client_ip(request)}"
    now = time.time()
    arr = [t for t in _rate_buckets.get(key, []) if now - t < window]
    if len(arr) >= limit:
        _rate_buckets[key] = arr
        return False
    arr.append(now)
    _rate_buckets[key] = arr
    # limpieza ocasional
    if len(_rate_buckets) > 5000:
        for k in [k for k, v in list(_rate_buckets.items()) if not v or now - v[-1] > window]:
            _rate_buckets.pop(k, None)
    return True


def _clear_session_cookie(resp):
    resp.del_cookie("lb_session", path="/")


# ── Autorización ──────────────────────────────────────────────────────────────
def _configurable_guilds(bot, sess):
    """Guilds donde está el bot Y (el user es admin/manage O es owner)."""
    uid = sess["uid"]
    is_owner = uid == OWNER_ID
    via_code = bool(sess.get("via_code"))
    scope = sess.get("scope")
    admin_ids = set(sess.get("ag", []))
    out = []
    for g in bot.guilds:
        if via_code:
            if g.id != scope:
                continue
        elif not (is_owner or g.id in admin_ids):
            continue
        m = g.get_member(uid)
        if not via_code and not is_owner and m is not None and not (
            m.guild_permissions.administrator or m.guild_permissions.manage_guild
        ):
            continue
        out.append({
            "id": str(g.id),
            "name": g.name,
            "icon": (f"https://cdn.discordapp.com/icons/{g.id}/{g.icon.key}.png" if g.icon else None),
            "members": g.member_count,
            "rank": _guild_rank(g, uid, m),
        })
    out.sort(key=lambda x: x["name"].lower())
    return out


def _guild_rank(guild, uid, member):
    """Etiqueta de rango del usuario en ese servidor (para mostrar en la tarjeta)."""
    if uid == guild.owner_id:
        return "Dueño"
    if member is not None:
        if member.guild_permissions.administrator:
            return "Admin"
        if member.guild_permissions.manage_guild:
            return "Manager"
    if uid == OWNER_ID:
        return "Owner Bot"
    return "Staff"


def _authz_guild(request):
    """Devuelve (sess, guild, error_response). Si error_response no es None, devolverlo.
    Fail-closed: exige miembro en cache + permisos live (no alcanza con `ag` stale)."""
    sess = _get_session(request)
    if not sess:
        return None, None, web.json_response({"error": "no_auth"}, status=401)
    bot = request.app["bot"]
    try:
        gid = int(request.match_info["gid"])
    except (KeyError, ValueError):
        return None, None, web.json_response({"error": "bad_guild"}, status=400)
    guild = bot.get_guild(gid)
    if not guild:
        return None, None, web.json_response({"error": "guild_not_found"}, status=404)
    uid = sess["uid"]
    if uid == OWNER_ID:
        return sess, guild, None
    if sess.get("via_code") and gid != sess.get("scope"):
        return None, None, web.json_response({"error": "forbidden"}, status=403)
    m = guild.get_member(uid)
    if m is None:
        # Sin miembro en cache no podemos revalidar permisos: denegar.
        return None, None, web.json_response({"error": "forbidden"}, status=403)
    if m.guild_permissions.administrator or m.guild_permissions.manage_guild:
        return sess, guild, None
    # Login por codigo tambien habilita roles_staff, pero hay que revalidar live.
    if sess.get("via_code"):
        try:
            cfg = _botmod().get_config(gid) or {}
            staff_ids = set(cfg.get("roles_staff") or [])
            if any(r.id in staff_ids for r in getattr(m, "roles", [])):
                return sess, guild, None
        except Exception:
            pass
    return None, None, web.json_response({"error": "forbidden"}, status=403)


# ── OAuth2 ────────────────────────────────────────────────────────────────────
async def _login(request):
    if not _rate_ok(request, scope="login", limit=20, window=60):
        return web.HTTPFound("/?error=rate")
    state = secrets.token_urlsafe(16)
    url = (f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}"
           f"&redirect_uri={BASE_URL}/api/callback&response_type=code"
           f"&scope=identify%20guilds%20guilds.join&state={state}&prompt=none")
    resp = web.HTTPFound(url)
    resp.set_cookie("lb_state", state, max_age=600, httponly=True, secure=True, samesite="Lax", path="/")
    # Checkbox del login: unirse a la comunidad (activado por default)
    join = "0" if request.query.get("join") == "0" else "1"
    resp.set_cookie("lb_join", join, max_age=600, httponly=True, secure=True, samesite="Lax", path="/")
    return resp


async def _callback(request):
    code = request.query.get("code")
    state = request.query.get("state")
    if not code or not hmac.compare_digest(str(state or ""), str(request.cookies.get("lb_state") or "")):
        return web.HTTPFound("/?error=state")
    try:
        async with aiohttp.ClientSession() as s:
            data = {
                "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code", "code": code,
                "redirect_uri": f"{BASE_URL}/api/callback",
            }
            async with s.post(f"{DISCORD_API}/oauth2/token", data=data,
                              headers={"Content-Type": "application/x-www-form-urlencoded"}) as r:
                if r.status != 200:
                    return web.HTTPFound("/?error=token")
                tok = await r.json()
            access = tok["access_token"]
            auth_h = {"Authorization": f"Bearer {access}"}
            async with s.get(f"{DISCORD_API}/users/@me", headers=auth_h) as r:
                user = await r.json()
            async with s.get(f"{DISCORD_API}/users/@me/guilds", headers=auth_h) as r:
                guilds = await r.json()
            # Auto-join al server de comunidad/soporte (scope guilds.join).
            # Se respeta el checkbox del login (cookie lb_join; default "1").
            quiere_unirse = request.cookies.get("lb_join", "1") != "0"
            try:
                bot = request.app["bot"]
                bot_token = getattr(getattr(bot, "http", None), "token", None)
                if quiere_unirse and bot_token and AUTOJOIN_GUILD_ID > 0:
                    async with s.put(
                        f"{DISCORD_API}/guilds/{AUTOJOIN_GUILD_ID}/members/{user['id']}",
                        headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
                        json={"access_token": access},
                    ) as jr:
                        pass  # 201 = agregado, 204 = ya estaba; ignoramos errores
            except Exception:
                pass
    except Exception:
        return web.HTTPFound("/?error=discord")

    uid = int(user["id"])
    if OWNER_ONLY and uid != OWNER_ID:
        return web.HTTPFound("/?error=forbidden")

    admin_guild_ids = []
    if isinstance(guilds, list):
        for g in guilds:
            try:
                perms = int(g.get("permissions", 0))
            except (TypeError, ValueError):
                perms = 0
            if g.get("owner") or (perms & PERM_ADMIN) or (perms & PERM_MANAGE):
                admin_guild_ids.append(int(g["id"]))

    payload = {"uid": uid, "u": user.get("username"), "av": user.get("avatar"),
               "ag": admin_guild_ids[:200]}
    resp = web.HTTPFound("/")
    _set_session_cookie(resp, payload)
    resp.del_cookie("lb_state", path="/")
    resp.del_cookie("lb_join", path="/")
    return resp


async def _code_login(request):
    """Canjea un código (de l!panel) por una sesión con acceso a ESE servidor."""
    if not _rate_ok(request, scope="code", limit=10, window=60):
        return web.json_response({"error": "rate_limited", "msg": "Demasiados intentos, esperá un minuto."}, status=429)
    try:
        body = await request.json()
    except Exception:
        body = {}
    data = redeem_code(body.get("code"))
    if not data:
        return web.json_response({"error": "invalid_code"}, status=400)
    if OWNER_ONLY and int(data["uid"]) != OWNER_ID:
        return web.json_response({"error": "forbidden", "msg": "Panel en modo solo owner."}, status=403)
    payload = {"uid": data["uid"], "u": data.get("u"), "av": data.get("av"),
               "via_code": True, "scope": data["gid"], "ag": [data["gid"]]}
    resp = web.json_response({"ok": True, "guild": str(data["gid"])})
    _set_session_cookie(resp, payload, ttl=CODE_SESSION_TTL)
    return resp


async def _logout(request):
    resp = web.json_response({"ok": True})
    _clear_session_cookie(resp)
    return resp


async def _me(request):
    sess = _get_session(request)
    if not sess:
        return web.json_response({"authenticated": False}, status=401)
    bot = request.app["bot"]
    bot_info = {"name": "LatamBOT", "avatar": None}
    try:
        if bot.user:
            bot_info = {"name": bot.user.name, "avatar": str(bot.user.display_avatar.url)}
    except Exception:
        pass
    mod = _botmod()
    links = {
        "kofi": getattr(mod, "KOFI_URL", "https://ko-fi.com/latambot"),
        "patreon": getattr(mod, "PATREON_URL", "https://patreon.com/latambot"),
    }
    return web.json_response({
        "authenticated": True,
        "user": {"id": str(sess["uid"]), "username": sess.get("u"),
                 "avatar": _discord_avatar_url(sess["uid"], sess.get("av")),
                 "is_owner": sess["uid"] == OWNER_ID},
        "bot": bot_info,
        "links": links,
        "guilds": _configurable_guilds(bot, sess),
    })


# ── Config por guild ──────────────────────────────────────────────────────────
# Claves de secciones "custom" (no schema-driven) que igual el frontend necesita.
_EXTRA_CONFIG_KEYS = [
    "rr_editor", "rr_titulo", "rr_descripcion", "rr_canal", "rr_mensaje",
    "autoreaccion_activo", "autoreacciones",
]


def _all_keys():
    return [f["key"] for s in schema.SCHEMA for f in s["fields"]] + _EXTRA_CONFIG_KEYS


async def _guild_get(request):
    sess, guild, err = _authz_guild(request)
    if err:
        return err
    bot = request.app["bot"]
    cfg = _botmod().get_config(guild.id) or {}
    channels = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
    roles = [{"id": str(r.id), "name": r.name, "color": f"#{r.color.value:06x}"}
             for r in guild.roles if not r.is_default()]
    def _es_cmd_publico(c):
        n = c.qualified_name.lower()
        if getattr(c, "hidden", False):
            return False
        if any(p in n for p in ("legacy", "_local", "debug", "eval", "_owner", "owner_", "presign", "sendfixnotif", "announcepanel", "backupnow", "restorebackup")):
            return False
        return True
    all_cmds = sorted({c.qualified_name for c in bot.commands if _es_cmd_publico(c)})
    mod = _botmod()
    try:
        _desc = (mod.cargar_datos().get("descargas") or [])
        dl_count = len([d for d in _desc if d.get("guild_id") == guild.id])
    except Exception:
        dl_count = 0
    try:
        premium = bool(mod._es_premium_guild(guild))
    except Exception:
        premium = False
    if sess["uid"] == OWNER_ID:
        premium = True  # el owner ve todo (testing)
    return web.json_response({
        "guild": {
            "id": str(guild.id), "name": guild.name,
            "icon": (f"https://cdn.discordapp.com/icons/{guild.id}/{guild.icon.key}.png" if guild.icon else None),
            "members": guild.member_count or len(guild.members),
            "text_channels": len(guild.text_channels),
            "voice_channels": len(guild.voice_channels),
            "roles": len([r for r in guild.roles if not r.is_default()]),
            "downloads": dl_count,
            "premium": premium,
        },
        "config": {k: cfg.get(k) for k in _all_keys()},
        "schema": schema.SCHEMA,
        "channels": channels,
        "roles": roles,
        "commands": all_cmds,
    })


async def _guild_messages(request):
    """Lista mensajes recientes de un canal para pickers del panel (sin IDs a mano)."""
    if not _rate_ok(request, scope="messages", limit=40, window=60):
        return web.json_response({"error": "rate_limited"}, status=429)
    sess, guild, err = _authz_guild(request)
    if err:
        return err
    canal = request.rel_url.query.get("channel") or ""
    if not str(canal).isdigit():
        return web.json_response({"error": "channel_required"}, status=400)
    ch = guild.get_channel(int(canal))
    if ch is None or not hasattr(ch, "history"):
        return web.json_response({"error": "channel_not_found"}, status=404)
    me = guild.me
    if me is None or not ch.permissions_for(me).read_message_history:
        return web.json_response({"error": "no_permission"}, status=403)
    out = []
    try:
        async for m in ch.history(limit=40):
            raw = (m.content or "").strip().replace("\n", " ")
            if not raw and m.embeds:
                emb0 = m.embeds[0]
                raw = (emb0.title or emb0.description or "[embed]").strip().replace("\n", " ")
            if not raw and m.attachments:
                raw = f"[{m.attachments[0].filename}]"
            if not raw:
                raw = "(sin texto)"
            author = getattr(m.author, "display_name", None) or str(m.author)
            stamp = ""
            try:
                stamp = m.created_at.strftime("%d/%m %H:%M")
            except Exception:
                pass
            label = f"{author} · {stamp} · {raw[:80]}"
            out.append({
                "id": str(m.id),
                "name": label,
                "author": author,
                "preview": raw[:120],
                "created_at": m.created_at.isoformat() if m.created_at else "",
            })
    except Exception as e:
        return web.json_response({"error": str(e)[:120]}, status=500)
    return web.json_response({"messages": out})


async def _guild_patch(request):
    if not _rate_ok(request, scope="patch", limit=60, window=60):
        return web.json_response({"error": "rate_limited"}, status=429)
    sess, guild, err = _authz_guild(request)
    if err:
        return err
    try:
        patch = await request.json()
    except Exception:
        return web.json_response({"error": "bad_json"}, status=400)
    valid_channels = {c.id for c in guild.channels}
    valid_roles = {r.id for r in guild.roles}
    valores, errores = schema.validate_patch(patch, valid_channels, valid_roles)
    mod = _botmod()
    # Seguridad: roles autoasignables (verif / autorol / xp) no pueden tener permisos peligrosos.
    _auto_keys = ("verificacion_rol", "autorol_id")
    if hasattr(mod, "_rol_verif_peligroso"):
        for key in _auto_keys:
            if key not in valores:
                continue
            rid = valores.get(key)
            rol = guild.get_role(int(rid)) if str(rid or "").isdigit() else None
            peligro = mod._rol_verif_peligroso(rol) if rol else None
            if peligro:
                valores.pop(key, None)
                errores[key] = (
                    f"No puede tener el permiso '{peligro}' (riesgo de escalada). "
                    "Elegí un rol sin permisos de moderación/admin."
                )
        if "xp_roles" in valores and isinstance(valores.get("xp_roles"), dict):
            limpio = {}
            for nivel, rid in valores["xp_roles"].items():
                rol = guild.get_role(int(rid)) if str(rid or "").isdigit() else None
                peligro = mod._rol_verif_peligroso(rol) if rol else None
                if peligro:
                    errores[f"xp_roles.{nivel}"] = f"Rol con permiso '{peligro}' no permitido."
                elif rol:
                    limpio[str(nivel)] = int(rid)
            valores["xp_roles"] = limpio
        if "roles_staff" in valores:
            # Solo admin/manage (no staff via_code) puede mutar la lista de staff.
            m = guild.get_member(sess["uid"])
            puede = (
                sess["uid"] == OWNER_ID
                or (m is not None and (m.guild_permissions.administrator or m.guild_permissions.manage_guild))
            )
            if not puede:
                valores.pop("roles_staff", None)
                errores["roles_staff"] = "Solo un administrador puede editar roles de staff."
    for key, val in valores.items():
        mod.update_server_config(guild.id, key, val)
    cfg = mod.get_config(guild.id) or {}
    return web.json_response({
        "ok": not errores,
        "errores": errores,
        "config": {k: cfg.get(k) for k in valores},
    })


async def _guild_downloads(request):
    """Lista los archivos que se guardaron en la CDN (l!dl / l!mp3) en ese servidor."""
    sess, guild, err = _authz_guild(request)
    if err:
        return err
    mod = _botmod()
    items = []
    try:
        datos = mod.cargar_datos()
        items = [d for d in (datos.get("descargas") or []) if d.get("guild_id") == guild.id]
    except Exception:
        items = []
    items = list(reversed(items))[:300]
    return web.json_response({"downloads": items})


async def _guild_action(request):
    if not _rate_ok(request, scope="action", limit=20, window=60):
        return web.json_response({"ok": False, "error": "Demasiadas acciones, esperá un momento."}, status=429)
    sess, guild, err = _authz_guild(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    action = body.get("action")
    mod = _botmod()
    if action == "stats_voice_create":
        tipos = body.get("tipos") or ["miembros", "bots", "boosts"]
        canales, error = await mod._crear_stats_voice(guild, tipos)
        return web.json_response({"ok": error is None, "error": error,
                                  "count": len(canales or {})})
    if action == "stats_voice_delete":
        await mod._eliminar_stats_voice(guild)
        return web.json_response({"ok": True})
    if action == "embed_send":
        edata = body.get("embed") or {}
        cid = body.get("channel")
        ch = guild.get_channel(int(cid)) if str(cid).isdigit() else None
        if ch is None or not hasattr(ch, "send"):
            return web.json_response({"ok": False, "error": "Canal inválido."})
        if not ch.permissions_for(guild.me).send_messages:
            return web.json_response({"ok": False, "error": "Sin permiso para enviar en ese canal."})
        try:
            color = int(str(edata.get("color") or "#5865f2").lstrip("#"), 16)
        except Exception:
            color = 0x5865F2
        emb = discord.Embed(
            title=(str(edata.get("title"))[:256] or None) if edata.get("title") else None,
            description=(str(edata.get("description"))[:4000] or None) if edata.get("description") else None,
            color=color,
        )
        if edata.get("image"):
            _img = str(edata["image"])[:500]
            if _img.lower().startswith("https://"):
                emb.set_image(url=_img)
        if edata.get("thumbnail"):
            _th = str(edata["thumbnail"])[:500]
            if _th.lower().startswith("https://"):
                emb.set_thumbnail(url=_th)
        if edata.get("footer"):
            emb.set_footer(text=str(edata["footer"])[:200])
        if not (emb.title or emb.description or emb.image.url):
            return web.json_response({"ok": False, "error": "El embed está vacío."})
        try:
            await ch.send(embed=emb)
            return web.json_response({"ok": True})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)[:120]})
    if action == "publish_panel":
        panel = body.get("panel")
        if panel == "confession":
            cfg = mod.get_config(guild.id) or {}
            input_id = cfg.get("confesion_input")
            if not input_id:
                return web.json_response({"ok": False, "error": "No hay canal de input de confesiones configurado (Canales → Confesiones)."})
            ch = guild.get_channel(int(input_id)) if str(input_id).isdigit() else None
            if ch is None:
                return web.json_response({"ok": False, "error": "El canal de input de confesiones ya no existe."})
            if not ch.permissions_for(guild.me).send_messages:
                return web.json_response({"ok": False, "error": f"Sin permiso para enviar en #{ch.name}."})
            try:
                msg = await mod._publish_confession_panel(guild, ch)
                return web.json_response({"ok": True, "channel": ch.name, "url": getattr(msg, "jump_url", None)})
            except Exception as e:
                return web.json_response({"ok": False, "error": str(e)[:120]})
        if panel == "verification":
            cfg = mod.get_config(guild.id) or {}
            canal_id = cfg.get("verificacion_canal")
            if not canal_id:
                return web.json_response({"ok": False, "error": "No hay canal de verificación configurado (Verificación → Canal)."})
            ch = guild.get_channel(int(canal_id)) if str(canal_id).isdigit() else None
            if ch is None:
                return web.json_response({"ok": False, "error": "El canal de verificación ya no existe."})
            if not ch.permissions_for(guild.me).send_messages:
                return web.json_response({"ok": False, "error": f"Sin permiso para enviar en #{ch.name}."})
            try:
                msg = await mod._publish_verification_panel(guild, ch)
                return web.json_response({"ok": True, "channel": ch.name, "url": getattr(msg, "jump_url", None)})
            except Exception as e:
                return web.json_response({"ok": False, "error": str(e)[:120]})
        if panel == "reaction_roles":
            cfg = mod.get_config(guild.id) or {}
            canal_id = cfg.get("rr_canal")
            if not canal_id:
                return web.json_response({"ok": False, "error": "Elegí un canal y guardá antes de publicar."})
            ch = guild.get_channel(int(canal_id)) if str(canal_id).isdigit() else None
            if ch is None:
                return web.json_response({"ok": False, "error": "El canal ya no existe."})
            if not ch.permissions_for(guild.me).send_messages:
                return web.json_response({"ok": False, "error": f"Sin permiso para enviar en #{ch.name}."})
            pairs = cfg.get("rr_editor") or []
            if not pairs:
                return web.json_response({"ok": False, "error": "Agregá al menos un rol+emoji y guardá antes de publicar."})
            try:
                msg, agregados = await mod._publish_reaction_role_panel(guild, ch, cfg.get("rr_titulo"), cfg.get("rr_descripcion"), pairs)
                return web.json_response({"ok": True, "channel": ch.name, "count": agregados, "url": getattr(msg, "jump_url", None)})
            except Exception as e:
                return web.json_response({"ok": False, "error": str(e)[:120]})
        return web.json_response({"ok": False, "error": "Panel desconocido."})
    if action == "verification_lock":
        cfg = mod.get_config(guild.id) or {}
        if not cfg.get("verificacion_rol"):
            return web.json_response({"ok": False, "error": "Configurá el rol verificado primero (Verificación → Rol)."})
        canal_id = cfg.get("verificacion_canal")
        ch = guild.get_channel(int(canal_id)) if str(canal_id or "").isdigit() else None
        if ch is None:
            return web.json_response({"ok": False, "error": "Configurá el canal de verificación primero."})
        if not ch.permissions_for(guild.me).send_messages:
            return web.json_response({"ok": False, "error": f"Sin permiso para enviar en #{ch.name}."})
        permisos_bot = guild.me.guild_permissions
        if not permisos_bot.manage_roles or not permisos_bot.manage_channels:
            return web.json_response({
                "ok": False,
                "error": "Me faltan los permisos 'Gestionar roles' y 'Gestionar canales' para privatizar.",
            })
        try:
            n, err = await mod._privatizar_para_verificacion(guild)
            if err:
                return web.json_response({"ok": False, "error": err})
            msg = await mod._publish_verification_panel(guild, ch)
            return web.json_response({"ok": True, "channel": ch.name, "count": n, "url": getattr(msg, "jump_url", None)})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)[:120]})
    if action == "rr_save":
        titulo = str(body.get("titulo") or "Reaction Roles")[:256]
        descripcion = str(body.get("descripcion") or "")[:2000]
        canal = body.get("canal")
        canal_id = int(canal) if str(canal).isdigit() else None
        if canal_id is not None and guild.get_channel(canal_id) is None:
            canal_id = None
        mensaje = body.get("mensaje")
        mensaje_id = int(mensaje) if str(mensaje).isdigit() else None
        valid_roles = {r.id for r in guild.roles}
        pairs = []
        for p in (body.get("pairs") or [])[:20]:
            emoji = str(p.get("emoji") or "").strip()[:64]
            try:
                rid = int(p.get("rol_id"))
            except (TypeError, ValueError):
                continue
            if emoji and rid in valid_roles:
                rol = guild.get_role(rid)
                peligro = None
                if hasattr(mod, "_rol_verif_peligroso"):
                    peligro = mod._rol_verif_peligroso(rol)
                if peligro:
                    return web.json_response({
                        "ok": False,
                        "error": f"El rol {getattr(rol, 'name', rid)} tiene '{peligro}' y no se puede usar en reaction roles.",
                    })
                pairs.append({"emoji": emoji, "rol_id": rid})
        mod.update_server_config(guild.id, "rr_titulo", titulo)
        mod.update_server_config(guild.id, "rr_descripcion", descripcion)
        mod.update_server_config(guild.id, "rr_canal", canal_id)
        mod.update_server_config(guild.id, "rr_mensaje", mensaje_id)
        mod.update_server_config(guild.id, "rr_editor", pairs)
        return web.json_response({"ok": True, "count": len(pairs)})
    if action == "rr_apply":
        # Aplica pares emoji→rol a un mensaje elegido en el panel (sin pegar IDs a mano).
        titulo = str(body.get("titulo") or "Reaction Roles")[:256]
        descripcion = str(body.get("descripcion") or "")[:2000]
        canal_id = int(body["canal"]) if str(body.get("canal") or "").isdigit() else None
        mensaje_id = int(body["mensaje"]) if str(body.get("mensaje") or "").isdigit() else None
        ch = guild.get_channel(canal_id) if canal_id else None
        if ch is None:
            return web.json_response({"ok": False, "error": "Elegí un canal."})
        if not ch.permissions_for(guild.me).add_reactions:
            return web.json_response({"ok": False, "error": f"Sin permiso para reaccionar en #{ch.name}."})
        if not mensaje_id:
            return web.json_response({"ok": False, "error": "Elegí un mensaje del canal."})
        valid_roles = {r.id for r in guild.roles}
        pairs = []
        for p in (body.get("pairs") or [])[:20]:
            emoji = str(p.get("emoji") or "").strip()[:64]
            try:
                rid = int(p.get("rol_id"))
            except (TypeError, ValueError):
                continue
            if not emoji or rid not in valid_roles:
                continue
            rol = guild.get_role(rid)
            if hasattr(mod, "_rol_verif_peligroso"):
                peligro = mod._rol_verif_peligroso(rol)
                if peligro:
                    return web.json_response({
                        "ok": False,
                        "error": f"El rol {getattr(rol, 'name', rid)} tiene '{peligro}' y no se puede usar en reaction roles.",
                    })
            pairs.append({"emoji": emoji, "rol_id": rid})
        if not pairs:
            return web.json_response({"ok": False, "error": "Agregá al menos un emoji → rol."})
        try:
            msg, agregados = await mod._apply_reaction_roles_to_message(
                guild, ch, mensaje_id, pairs, titulo=titulo, descripcion=descripcion, replace=True,
            )
        except discord.NotFound:
            return web.json_response({"ok": False, "error": "Ese mensaje ya no existe. Elegí otro."})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)[:120]})
        mod.update_server_config(guild.id, "rr_titulo", titulo)
        mod.update_server_config(guild.id, "rr_descripcion", descripcion)
        mod.update_server_config(guild.id, "rr_canal", canal_id)
        mod.update_server_config(guild.id, "rr_mensaje", mensaje_id)
        mod.update_server_config(guild.id, "rr_editor", pairs)
        return web.json_response({
            "ok": True,
            "channel": ch.name,
            "count": agregados,
            "url": getattr(msg, "jump_url", None),
        })
    if action == "autoreaccion_save":
        import re as _re_ar
        import secrets as _secrets_ar
        activo = body.get("activo")
        if isinstance(activo, str):
            activo = activo.lower() in ("1", "true", "on", "yes")
        else:
            activo = bool(activo)
        valid_channels = {c.id for c in guild.text_channels}
        max_rules = int(getattr(mod, "_AUTOREACCION_MAX_REGLAS", 15) or 15)
        max_emojis = int(getattr(mod, "_AUTOREACCION_MAX_EMOJIS", 3) or 3)
        rules_out = []
        for raw in (body.get("rules") or [])[:max_rules]:
            if not isinstance(raw, dict):
                continue
            match = str(raw.get("match") or "contains").strip().lower()
            if match not in ("contains", "regex", "attachment"):
                continue
            scope = str(raw.get("scope") or "channel").strip().lower()
            if scope not in ("channel", "guild"):
                continue
            canal_id = None
            if scope == "channel":
                try:
                    canal_id = int(raw.get("canal_id"))
                except (TypeError, ValueError):
                    continue
                if canal_id not in valid_channels:
                    continue
            patron = str(raw.get("patron") or "")[:200]
            if match in ("contains", "regex") and not patron.strip():
                continue
            if match == "regex":
                flags = 0 if raw.get("case_sensitive") else _re_ar.IGNORECASE
                try:
                    _re_ar.compile(patron, flags)
                except _re_ar.error:
                    return web.json_response({"ok": False, "error": f"Regex inválida: {patron[:60]}"})
            emojis = []
            for em in (raw.get("emojis") or []):
                em = str(em or "").strip()[:64]
                if em and em not in emojis:
                    emojis.append(em)
                if len(emojis) >= max_emojis:
                    break
            if not emojis:
                continue
            rid = str(raw.get("id") or "").strip()[:32]
            if not rid or not all(c.isalnum() or c in "-_" for c in rid):
                rid = _secrets_ar.token_hex(4)
            rule_activo = raw.get("activo")
            if isinstance(rule_activo, str):
                rule_activo = rule_activo.lower() in ("1", "true", "on", "yes")
            elif rule_activo is None:
                rule_activo = True
            else:
                rule_activo = bool(rule_activo)
            incluir_bots = raw.get("incluir_bots")
            if isinstance(incluir_bots, str):
                incluir_bots = incluir_bots.lower() in ("1", "true", "on", "yes")
            else:
                incluir_bots = bool(incluir_bots)
            case_sensitive = raw.get("case_sensitive")
            if isinstance(case_sensitive, str):
                case_sensitive = case_sensitive.lower() in ("1", "true", "on", "yes")
            else:
                case_sensitive = bool(case_sensitive)
            rules_out.append({
                "id": rid,
                "activo": rule_activo,
                "scope": scope,
                "canal_id": canal_id,
                "match": match,
                "patron": patron if match != "attachment" else "",
                "emojis": emojis,
                "incluir_bots": incluir_bots,
                "case_sensitive": case_sensitive,
            })
        mod.update_server_config(guild.id, "autoreaccion_activo", activo)
        mod.update_server_config(guild.id, "autoreacciones", rules_out)
        if hasattr(mod, "_autoreaccion_update_scan_flag"):
            try:
                mod._autoreaccion_update_scan_flag(guild.id, {
                    "autoreaccion_activo": activo,
                    "autoreacciones": rules_out,
                })
            except Exception:
                pass
        return web.json_response({
            "ok": True,
            "count": len(rules_out),
            "activo": activo,
            "rules": rules_out,
        })
    return web.json_response({"error": "unknown_action"}, status=400)


# ── Estáticos / SPA ───────────────────────────────────────────────────────────
TOPGG_SECRET = (os.getenv("TOPGG_WEBHOOK_SECRET") or "").strip()
DBL_SECRET = (os.getenv("DBL_WEBHOOK_SECRET") or "").strip()


def _webhook_auth_ok(header_val: str, secret: str) -> bool:
    """Fail-closed: sin secret o header invalido -> False."""
    if not secret:
        return False
    got = header_val or ""
    if len(got) != len(secret):
        return False
    return hmac.compare_digest(got, secret)


async def _topgg_vote(request):
    """Webhook de top.gg: llega cuando un usuario vota. Da perks temporales."""
    if not _webhook_auth_ok(request.headers.get("Authorization"), TOPGG_SECRET):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "bad_json"}, status=400)
    uid = data.get("user")
    if not uid or not str(uid).isdigit():
        return web.json_response({"error": "no_user"}, status=400)
    try:
        await _botmod()._registrar_voto(
            int(uid),
            weekend=bool(data.get("isWeekend")),
            test=(data.get("type") == "test"),
        )
    except Exception as e:
        print(f"[TOPGG] {e}")
    return web.json_response({"ok": True})


async def _dbl_vote(request):
    """Webhook de discordbotlist.com. Payload: {id, username, avatar, admin}.
    Header Authorization = el webhook secret. Debe responder 200."""
    if not _webhook_auth_ok(request.headers.get("Authorization"), DBL_SECRET):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "bad_json"}, status=400)
    uid = data.get("id")
    if not uid or not str(uid).isdigit():
        return web.json_response({"error": "no_user"}, status=400)
    try:
        await _botmod()._registrar_voto(int(uid))
    except Exception as e:
        print(f"[DBL] {e}")
    return web.json_response({"ok": True})


async def _health(request):
    return web.json_response({"ok": True, "service": "latambot-dashboard"})


async def _info(request):
    """Info pública para el login: logo (PFP del bot), nombre y links de apoyo."""
    bot = request.app["bot"]
    name, avatar = "LatamBOT", None
    try:
        if bot.user:
            name = bot.user.name
            avatar = str(bot.user.display_avatar.url)
    except Exception:
        pass
    mod = _botmod()
    return web.json_response({
        "name": name,
        "avatar": avatar,
        "links": {
            "kofi": getattr(mod, "KOFI_URL", "https://ko-fi.com/latambot"),
            "patreon": getattr(mod, "PATREON_URL", "https://patreon.com/latambot"),
        },
    })


async def _status_page(request):
    """Pagina de estado de la instalación."""
    return _serve_html(os.path.join(WEB_DIR, "status.html"))


async def _status_api(request):
    """Estado en vivo del bot para la pagina de status. Publico, sin datos sensibles."""
    import math
    bot = request.app["bot"]
    mod = _botmod()
    try:
        ready = bool(bot.is_ready())
    except Exception:
        ready = False
    latency_ms = None
    try:
        lat = bot.latency
        if lat is not None and not math.isnan(lat) and not math.isinf(lat):
            latency_ms = round(lat * 1000)
    except Exception:
        pass
    try:
        servers = len(bot.guilds)
    except Exception:
        servers = None
    uptime = None
    try:
        started = getattr(mod, "BOT_STARTED_AT", None)
        if started is not None:
            uptime = int((datetime.datetime.now(datetime.timezone.utc) - started).total_seconds())
    except Exception:
        pass
    version = getattr(mod, "BOT_VERSION", "")
    lat_ok = latency_ms is not None and latency_ms < 400
    lat_degraded = latency_ms is not None and latency_ms >= 400
    yt_down = bool(getattr(mod, "YOUTUBE_MANTENIMIENTO", False))
    subs = [
        {"name": "Bot (Discord)", "status": "operational" if ready else "down"},
        {"name": "Latencia del gateway",
         "status": "operational" if (ready and lat_ok) else ("degraded" if ready else "down")},
        {"name": "Panel web", "status": "operational"},
        {"name": "Documentación", "status": "operational"},
        {"name": "Descargas de YouTube", "status": "degraded" if yt_down else "operational"},
    ]
    if not ready:
        overall = "down"
    elif lat_degraded or yt_down:
        overall = "degraded"
    else:
        overall = "operational"
    resp = web.json_response({
        "status": overall,
        "bot_online": ready,
        "latency_ms": latency_ms,
        "servers": servers,
        "uptime_seconds": uptime,
        "version": version,
        "subsystems": subs,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    resp.headers["Cache-Control"] = "no-store"
    return resp


async def _index(request):
    host = (request.host or "").lower()
    # status.* -> status ; docs.* -> documentacion ; panel.* -> dashboard SPA ; apex/www -> landing
    if host.startswith("status."):
        return _serve_html(os.path.join(WEB_DIR, "status.html"))
    if host.startswith("docs."):
        return _serve_html(os.path.join(WEB_DIR, "docs.html"))
    if host.startswith("panel.") or host.startswith("127.") or host.startswith("localhost"):
        path = os.path.join(WEB_DIR, "index.html")
    else:
        landing = os.path.join(WEB_DIR, "landing.html")
        path = landing if os.path.exists(landing) else os.path.join(WEB_DIR, "index.html")
    return _serve_html(path)


async def _docs(request):
    """Documentación de la instalación."""
    return _serve_html(os.path.join(WEB_DIR, "docs.html"))


async def _llms(request):
    """Indice llms.txt para consumo de IAs."""
    path = os.path.join(WEB_DIR, "llms.txt")
    if not os.path.exists(path):
        return web.Response(text="", content_type="text/plain")
    with open(path, "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/plain", charset="utf-8")


async def _legal(request):
    """Página legal (Términos de Servicio + Política de Privacidad)."""
    return _serve_html(os.path.join(WEB_DIR, "legal.html"))


async def _index_en(request):
    """Landing en inglés."""
    en = os.path.join(WEB_DIR, "landing_en.html")
    return _serve_html(en if os.path.exists(en) else os.path.join(WEB_DIR, "landing.html"))


async def _index_pt(request):
    """Landing en portugués."""
    pt = os.path.join(WEB_DIR, "landing_pt.html")
    return _serve_html(pt if os.path.exists(pt) else os.path.join(WEB_DIR, "landing.html"))


def _serve_html(path):
    if not os.path.exists(path):
        return web.Response(text="No desplegado todavía.", content_type="text/plain")
    try:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        # cache-busting: versiona los assets para que el navegador/Cloudflare no sirvan viejos
        html = html.replace("/static/app.js", f"/static/app.js?v={ASSET_VER}")
        html = html.replace("/static/styles.css", f"/static/styles.css?v={ASSET_VER}")
        resp = web.Response(text=html, content_type="text/html")
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        return resp
    except Exception:
        return web.FileResponse(path)


@web.middleware
async def _cache_mw(request, handler):
    resp = await handler(request)
    try:
        p = request.path
        if p.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif p.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        # Headers basicos anti-clickjacking / MIME sniffing
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if p.endswith(".html") or p == "/" or not p.startswith("/api/"):
            resp.headers.setdefault(
                "Content-Security-Policy",
                "frame-ancestors 'none'; default-src 'self'; img-src 'self' https://cdn.discordapp.com data:; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; "
                "connect-src 'self'",
            )
    except Exception:
        pass
    return resp


# ── App ───────────────────────────────────────────────────────────────────────
def build_app(bot):
    app = web.Application(middlewares=[_cache_mw])
    app["bot"] = bot
    app.router.add_get("/api/health", _health)
    app.router.add_post("/api/topgg/vote", _topgg_vote)
    app.router.add_post("/api/dbl/vote", _dbl_vote)
    app.router.add_get("/api/info", _info)
    app.router.add_get("/api/login", _login)
    app.router.add_get("/api/callback", _callback)
    app.router.add_post("/api/logout", _logout)
    app.router.add_post("/api/code", _code_login)
    app.router.add_get("/api/me", _me)
    app.router.add_get("/api/guild/{gid}", _guild_get)
    app.router.add_patch("/api/guild/{gid}", _guild_patch)
    app.router.add_get("/api/guild/{gid}/messages", _guild_messages)
    app.router.add_get("/api/guild/{gid}/downloads", _guild_downloads)
    app.router.add_post("/api/guild/{gid}/action", _guild_action)
    app.router.add_get("/", _index)
    app.router.add_get("/docs", _docs)
    app.router.add_get("/llms.txt", _llms)
    app.router.add_get("/status", _status_page)
    app.router.add_get("/api/status", _status_api)
    app.router.add_get("/en", _index_en)
    app.router.add_get("/pt", _index_pt)
    # Página legal (Términos + Privacidad): varias URLs amigables, todas la misma página.
    for _p in ("/legal", "/privacidad", "/Privacidad", "/politica-privacidad",
               "/Politica-privacidad", "/politica-de-privacidad", "/terminos",
               "/Terminos", "/condiciones", "/Condiciones-servicio",
               "/terminos-y-condiciones", "/tos"):
        app.router.add_get(_p, _legal)
    if os.path.isdir(WEB_DIR):
        app.router.add_static("/static/", WEB_DIR, name="static")
    return app


async def start_dashboard(bot):
    if getattr(bot, "_dashboard_started", False):
        return
    bot._dashboard_started = True
    app = build_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"[DASHBOARD] Escuchando en :{PORT} (base {BASE_URL}, owner_only={OWNER_ONLY})")

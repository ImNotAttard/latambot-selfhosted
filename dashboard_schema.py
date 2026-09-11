"""Esquema declarativo del dashboard: secciones, campos y validación.

Sin dependencias del bot — pura lógica para poder testear.
Cada clave de campo mapea 1:1 a una clave de ESTRUCTURA_SERVER en latambot.py.
"""

SCHEMA = [
    {"id": "canales", "label": "Canales", "icon": "📍", "fields": [
        {"key": "canal_general", "label": "General", "type": "channel"},
        {"key": "canal_logs", "label": "Logs", "type": "channel"},
        {"key": "canal_staff", "label": "Staff", "type": "channel"},
        {"key": "bienvenida_canal", "label": "Bienvenida", "type": "channel"},
        {"key": "despedida_canal", "label": "Despedida", "type": "channel"},
        {"key": "confesion_public", "label": "Confesiones públicas", "type": "channel"},
        {"key": "canal_anuncios_global", "label": "Anuncios global", "type": "channel"},
        {"key": "canal_mascotas", "label": "Mascotas", "type": "channel"},
        {"key": "honeypot_canal", "label": "Honeypot", "type": "channel"},
    ]},
    {"id": "sistemas", "label": "Sistemas", "icon": "🔧", "fields": [
        {"key": "sistema_antispam", "label": "Anti-Spam", "type": "toggle"},
        {"key": "antispam_umbral", "label": "Umbral anti-spam", "type": "number", "min": 2, "max": 50},
        {"key": "antispam_ventana", "label": "Ventana (s)", "type": "number", "min": 1, "max": 60},
        {"key": "antiraid_menciones", "label": "Anti-raid: menciones masivas", "type": "toggle"},
        {"key": "menciones_max", "label": "Máx. menciones por mensaje", "type": "number", "min": 3, "max": 50},
        {"key": "raid_max_ofensas", "label": "Ofensas antes de silenciar (1ª = aviso)", "type": "number", "min": 1, "max": 10},
        {"key": "raid_mute_min", "label": "Minutos de silencio (timeout)", "type": "number", "min": 1, "max": 1440},
        {"key": "sistema_logs_joins", "label": "Logs joins/salidas", "type": "toggle"},
        {"key": "sistema_anuncios", "label": "AutoMod anuncios", "type": "toggle"},
        {"key": "sistema_nsfw", "label": "Imágenes explícitas", "type": "toggle"},
        {"key": "automod_palabras", "label": "Filtro de palabras", "type": "toggle"},
        {"key": "palabras_bloqueadas", "label": "Palabras bloqueadas", "type": "taglist"},
        {"key": "sistema_gen", "label": "Modo GEN", "type": "toggle"},
        {"key": "sistema_changelog", "label": "Changelogs automáticos", "type": "toggle"},
        {"key": "lenguaje_tecnico", "label": "Lenguaje técnico (para usuarios avanzados)", "type": "toggle"},
        {"key": "idioma", "label": "Idioma del bot", "type": "select", "options": ["es", "en", "pt"]},
    ]},
    {"id": "xp", "label": "Niveles (XP)", "icon": "⭐", "fields": [
        {"key": "sistema_xp", "label": "Activar niveles", "type": "toggle"},
        {"key": "xp_anuncio", "label": "Anunciar subidas de nivel", "type": "toggle"},
        {"key": "xp_canal", "label": "Canal de anuncios (vacío = mismo canal)", "type": "channel"},
    ]},
    {"id": "roles", "label": "Roles", "icon": "👥", "fields": [
        {"key": "autorol_id", "label": "Autorol", "type": "role"},
        {"key": "verificacion_rol", "label": "Rol verificado", "type": "role"},
        {"key": "roles_staff", "label": "Roles staff", "type": "roles"},
        {"key": "roles_persistentes", "label": "Roles persistentes (restaurar al volver)", "type": "toggle"},
    ]},
    {"id": "starboard", "label": "Starboard", "icon": "⭐", "fields": [
        {"key": "starboard_activo", "label": "Activar starboard", "type": "toggle"},
        {"key": "starboard_canal", "label": "Canal de destacados", "type": "channel"},
        {"key": "starboard_emoji", "label": "Emoji", "type": "text", "maxlen": 40},
        {"key": "starboard_umbral", "label": "Reacciones mínimas", "type": "number", "min": 1, "max": 100},
    ]},
    {"id": "ia", "label": "Chatbot IA & Modo", "icon": "🧠", "premium": True, "fields": [
        {"key": "modo", "label": "Modo", "type": "select", "options": ["LEGACY", "GEN", "RP"]},
        {"key": "prefix", "label": "Prefix", "type": "text", "maxlen": 5},
        {"key": "personalidad", "label": "Personalidad RP", "type": "text", "maxlen": 100},
        {"key": "intensidad_ia", "label": "Intensidad IA", "type": "number", "min": 0, "max": 100},
    ]},
    {"id": "bienvenida", "label": "Bienvenida", "icon": "👋", "fields": [
        {"key": "bienvenida_mensaje", "label": "Mensaje", "type": "textarea", "maxlen": 1000},
        {"key": "bienvenida_titulo", "label": "Título", "type": "text", "maxlen": 100},
        {"key": "bienvenida_subtitulo", "label": "Subtítulo", "type": "text", "maxlen": 100},
        {"key": "bienvenida_imagen_activa", "label": "Imagen activa", "type": "toggle"},
        {"key": "bienvenida_color_fondo", "label": "Color fondo", "type": "color"},
        {"key": "bienvenida_color_texto", "label": "Color texto", "type": "color"},
        {"key": "bienvenida_color_acento", "label": "Color acento", "type": "color"},
        {"key": "despedida_mensaje", "label": "Mensaje despedida", "type": "textarea", "maxlen": 1000},
    ]},
    {"id": "verificacion", "label": "Verificación", "icon": "✅", "fields": [
        {"key": "verificacion_activa", "label": "Activa", "type": "toggle"},
        {"key": "verificacion_canal", "label": "Canal", "type": "channel"},
        {"key": "verificacion_rol", "label": "Rol", "type": "role"},
        {"key": "verificacion_titulo", "label": "Título", "type": "text", "maxlen": 100},
        {"key": "verificacion_descripcion", "label": "Descripción", "type": "textarea", "maxlen": 500},
        {"key": "verificacion_excluidos", "label": "Canales que NO se hacen privados (ej: logs, reglas)", "type": "channels"},
    ]},
    {"id": "triggers", "label": "Triggers", "icon": "💬", "fields": [
        {"key": "triggers", "label": "Auto-respuestas", "type": "kvlist"},
    ]},
    {"id": "comandos", "label": "Comandos", "icon": "⚡", "fields": [
        {"key": "comandos_desactivados", "label": "Comandos desactivados", "type": "commands"},
    ]},
    {"id": "mascotas", "label": "Mascotas", "icon": "🐾", "fields": [
        {"key": "sistema_mascotas_auto", "label": "Activado", "type": "toggle"},
        {"key": "mascotas_tipo", "label": "Tipo", "type": "select", "options": ["gatos", "perros", "mix"]},
        {"key": "mascotas_intervalo_min", "label": "Intervalo (min)", "type": "number", "min": 30, "max": 1440},
    ]},
    {"id": "honeypot", "label": "Honeypot", "icon": "🪤", "fields": [
        {"key": "honeypot_canal", "label": "Canal honeypot", "type": "channel"},
        {"key": "honeypot_solo_sospechosos", "label": "Solo banear cuentas sospechosas (protege humanos)", "type": "toggle"},
        {"key": "honeypot_bans", "label": "Baneos realizados", "type": "readonly"},
    ]},
    {"id": "stats_voice", "label": "Stats de voz", "icon": "📊", "fields": [
        {"key": "stats_voice_activa", "label": "Activas", "type": "readonly"},
        {"key": "stats_voice_tipos", "label": "Stats a mostrar", "type": "multiselect",
         "options": ["miembros", "bots", "boosts", "canales", "total"]},
    ]},
    {"id": "modlog", "label": "Modlog y Warns", "icon": "📋", "fields": [
        {"key": "modlog_activo", "label": "Registrar sanciones como casos numerados", "type": "toggle"},
        {"key": "modlog_canal", "label": "Canal del modlog (vacío = canal de logs)", "type": "channel"},
        {"key": "warn_puntos_default", "label": "Puntos por advertencia (default)", "type": "number", "min": 1, "max": 100},
        {"key": "warn_expira_dias", "label": "Los puntos caducan a los X días (0 = nunca)", "type": "number", "min": 0, "max": 3650},
        {"key": "reportes_canal", "label": "Canal de reportes (l!reportar)", "type": "channel"},
    ]},
    {"id": "reaction_roles", "label": "Reaction Roles", "icon": "🎭", "custom": True, "fields": []},
    {"id": "autoreaccion", "label": "Autoreacción", "icon": "✨", "custom": True, "fields": []},
    {"id": "confesiones", "label": "Confesiones", "icon": "🤫", "fields": [
        {"key": "confesion_input", "label": "Canal de envío (donde va el panel)", "type": "channel"},
        {"key": "confesion_public", "label": "Canal público (confesiones aprobadas)", "type": "channel"},
    ]},
    {"id": "apariencia", "label": "Apariencia", "icon": "🎨", "premium": True, "fields": [
        {"key": "dash_accent", "label": "Color de acento", "type": "color"},
        {"key": "dash_theme", "label": "Tema", "type": "select", "options": ["auto", "claro", "oscuro"]},
    ]},
]

_EDITABLE_TYPES = {
    "toggle", "channel", "channels", "role", "roles", "text", "textarea",
    "number", "select", "color", "kvlist", "commands", "multiselect", "taglist",
}


def _all_fields():
    for sec in SCHEMA:
        for f in sec["fields"]:
            yield f


def field_by_key(key):
    for f in _all_fields():
        if f["key"] == key:
            return f
    return None


def validate_value(field, value, valid_channel_ids, valid_role_ids):
    """Devuelve (ok, error, valor_normalizado)."""
    t = field["type"]
    if t == "readonly":
        return False, "Campo de solo lectura.", None
    if t == "toggle":
        if isinstance(value, str):
            return True, "", value.lower() in ("1", "true", "on", "yes")
        return True, "", bool(value)
    if t == "number":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return False, "Debe ser un número.", None
        if "min" in field and n < field["min"]:
            return False, f"Mínimo {field['min']}.", None
        if "max" in field and n > field["max"]:
            return False, f"Máximo {field['max']}.", None
        return True, "", n
    if t in ("text", "textarea"):
        s = "" if value is None else str(value)
        ml = field.get("maxlen", 2000)
        if len(s) > ml:
            return False, f"Máximo {ml} caracteres.", None
        return True, "", s
    if t == "color":
        s = str(value or "").strip()
        if not (len(s) == 7 and s[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in s[1:])):
            return False, "Color inválido (usa #rrggbb).", None
        return True, "", s
    if t == "select":
        if value not in field.get("options", []):
            return False, "Opción inválida.", None
        return True, "", value
    if t == "channel":
        if value in (None, "", 0, "0"):
            return True, "", None
        try:
            cid = int(value)
        except (TypeError, ValueError):
            return False, "Canal inválido.", None
        if cid not in valid_channel_ids:
            return False, "Ese canal no pertenece al servidor.", None
        return True, "", cid
    if t == "role":
        if value in (None, "", 0, "0"):
            return True, "", None
        try:
            rid = int(value)
        except (TypeError, ValueError):
            return False, "Rol inválido.", None
        if rid not in valid_role_ids:
            return False, "Ese rol no pertenece al servidor.", None
        return True, "", rid
    if t == "roles":
        if not isinstance(value, list):
            return False, "Debe ser una lista de roles.", None
        out = []
        for r in value:
            try:
                rid = int(r)
            except (TypeError, ValueError):
                return False, "Rol inválido en la lista.", None
            if rid not in valid_role_ids:
                return False, "Un rol no pertenece al servidor.", None
            out.append(rid)
        return True, "", out
    if t == "channels":
        if not isinstance(value, list):
            return False, "Debe ser una lista de canales.", None
        out = []
        for c in value:
            try:
                cid = int(c)
            except (TypeError, ValueError):
                return False, "Canal inválido en la lista.", None
            if cid not in valid_channel_ids:
                return False, "Un canal no pertenece al servidor.", None
            out.append(cid)
        return True, "", out
    if t == "multiselect":
        if not isinstance(value, list):
            return False, "Debe ser una lista.", None
        opts = field.get("options", [])
        return True, "", [v for v in value if v in opts]
    if t == "kvlist":
        if not isinstance(value, dict):
            return False, "Formato inválido.", None
        out = {}
        for k, v in list(value.items())[:50]:
            out[str(k)[:80]] = str(v)[:500]
        return True, "", out
    if t == "commands":
        if not isinstance(value, list):
            return False, "Debe ser una lista.", None
        return True, "", [str(c)[:40] for c in value][:200]
    if t == "taglist":
        if not isinstance(value, list):
            return False, "Debe ser una lista.", None
        limpio = []
        for w in value:
            s = str(w).strip().lower()[:60]
            if s and s not in limpio:
                limpio.append(s)
        return True, "", limpio[:300]
    return False, "Tipo desconocido.", None


def validate_patch(patch, valid_channel_ids, valid_role_ids):
    """Devuelve (valores_validos, errores)."""
    valores, errores = {}, {}
    for key, value in (patch or {}).items():
        field = field_by_key(key)
        if not field or field["type"] not in _EDITABLE_TYPES:
            errores[key] = "Campo no editable."
            continue
        ok, err, norm = validate_value(field, value, valid_channel_ids, valid_role_ids)
        if ok:
            valores[key] = norm
        else:
            errores[key] = err
    return valores, errores

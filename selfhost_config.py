"""Validación pequeña y sin dependencias para instalaciones self-hosted."""

from __future__ import annotations

from collections.abc import Mapping


def validate_environment(env: Mapping[str, str]) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias) sin imprimir ni revelar valores secretos."""
    errors: list[str] = []
    warnings: list[str] = []
    if not (env.get("DISCORD_TOKEN") or "").strip():
        errors.append("Falta DISCORD_TOKEN. Creá un bot de Discord y definilo en .env.")
    if env.get("DASHBOARD_PORT") and not env.get("DASHBOARD_BASE_URL"):
        warnings.append("DASHBOARD_PORT está definido pero DASHBOARD_BASE_URL no; se usará localhost.")
    if env.get("DISCORD_CLIENT_ID") and not env.get("DISCORD_CLIENT_SECRET"):
        warnings.append("El OAuth del dashboard está incompleto: falta DISCORD_CLIENT_SECRET.")
    if env.get("DISCORD_CLIENT_SECRET") and len((env.get("DASHBOARD_SESSION_SECRET") or "").strip()) < 32:
        warnings.append("DASHBOARD_SESSION_SECRET debería tener al menos 32 caracteres.")
    return errors, warnings

"""Helpers para aplicar permisos del sistema de verificacion."""

import discord


def _overwrite(overwrites, target, **permissions):
    current = overwrites.get(target)
    if current is None:
        current = discord.PermissionOverwrite()
    for name, value in permissions.items():
        setattr(current, name, value)
    overwrites[target] = current


async def aplicar_privacidad_canal(
    channel,
    default_role,
    verified_role,
    bot_member,
    *,
    voice: bool = False,
) -> None:
    """Aplica todas las sobrescrituras juntas para evitar bloqueos parciales."""
    overwrites = dict(channel.overwrites)
    _overwrite(overwrites, default_role, view_channel=False)
    _overwrite(overwrites, verified_role, view_channel=True)
    _overwrite(overwrites, bot_member, view_channel=True)
    if voice:
        _overwrite(overwrites, default_role, connect=False)
        _overwrite(overwrites, verified_role, connect=True)
        _overwrite(overwrites, bot_member, connect=True)
    await channel.edit(
        overwrites=overwrites,
        reason="Privatizacion para verificacion LatamBOT",
    )

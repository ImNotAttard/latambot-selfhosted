import asyncio

import discord

from latambot_core.verification import aplicar_privacidad_canal


class FakeTarget:
    pass


class FakeChannel:
    def __init__(self, overwrites):
        self.overwrites = overwrites
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


def test_aplica_todos_los_permisos_en_una_sola_edicion():
    everyone = FakeTarget()
    verified = FakeTarget()
    bot_member = FakeTarget()
    other = FakeTarget()
    existing = discord.PermissionOverwrite(send_messages=False)
    channel = FakeChannel({other: existing})

    asyncio.run(
        aplicar_privacidad_canal(
            channel,
            default_role=everyone,
            verified_role=verified,
            bot_member=bot_member,
        )
    )

    assert len(channel.edits) == 1
    overwrites = channel.edits[0]["overwrites"]
    assert overwrites[other].send_messages is False
    assert overwrites[everyone].view_channel is False
    assert overwrites[verified].view_channel is True
    assert overwrites[bot_member].view_channel is True

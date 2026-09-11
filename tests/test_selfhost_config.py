from selfhost_config import validate_environment


def test_requires_discord_token():
    errors, _ = validate_environment({})
    assert errors == ["Falta DISCORD_TOKEN. Creá un bot de Discord y definilo en .env."]


def test_optional_integrations_do_not_block_startup():
    errors, warnings = validate_environment({"DISCORD_TOKEN": "test-token"})
    assert errors == []
    assert warnings == []


def test_dashboard_oauth_warnings_are_actionable():
    errors, warnings = validate_environment({
        "DISCORD_TOKEN": "test-token",
        "DISCORD_CLIENT_ID": "client-id",
        "DISCORD_CLIENT_SECRET": "",
    })
    assert errors == []
    assert "DISCORD_CLIENT_SECRET" in warnings[0]

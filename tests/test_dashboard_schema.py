import dashboard_schema as ds


def test_toggle_normalizes_truthy():
    field = {"key": "sistema_antispam", "type": "toggle"}
    ok, err, val = ds.validate_value(field, "true", set(), set())
    assert ok and val is True


def test_channel_must_belong_to_guild():
    field = {"key": "canal_logs", "type": "channel"}
    ok, err, val = ds.validate_value(field, 999, {111, 222}, set())
    assert not ok and "canal" in err.lower()
    ok2, err2, val2 = ds.validate_value(field, 111, {111, 222}, set())
    assert ok2 and val2 == 111


def test_channel_accepts_none_to_clear():
    field = {"key": "canal_logs", "type": "channel"}
    ok, err, val = ds.validate_value(field, None, {111}, set())
    assert ok and val is None


def test_number_respects_range():
    field = {"key": "antispam_umbral", "type": "number", "min": 1, "max": 50}
    ok, _, _ = ds.validate_value(field, 999, set(), set())
    assert not ok
    ok2, _, val2 = ds.validate_value(field, "7", set(), set())
    assert ok2 and val2 == 7


def test_roles_filters_invalid():
    field = {"key": "roles_staff", "type": "roles"}
    ok, err, val = ds.validate_value(field, [1, 2, 99], set(), {1, 2})
    assert not ok
    ok2, err2, val2 = ds.validate_value(field, [1, 2], set(), {1, 2})
    assert ok2 and val2 == [1, 2]


def test_color_validation():
    field = {"key": "bienvenida_color_fondo", "type": "color"}
    assert ds.validate_value(field, "#5865f2", set(), set())[0]
    assert not ds.validate_value(field, "rojo", set(), set())[0]


def test_validate_patch_collects_errors():
    valores, errores = ds.validate_patch(
        {"sistema_antispam": "true", "antispam_umbral": 9999},
        set(), set(),
    )
    assert valores.get("sistema_antispam") is True
    assert "antispam_umbral" in errores


def test_patch_rejects_unknown_or_readonly():
    valores, errores = ds.validate_patch(
        {"honeypot_bans": 5, "campo_inexistente": 1},
        set(), set(),
    )
    assert "honeypot_bans" in errores
    assert "campo_inexistente" in errores
    assert valores == {}


def test_schema_has_all_setup_sections():
    ids = {s["id"] for s in ds.SCHEMA}
    for needed in {"canales", "sistemas", "roles", "ia", "bienvenida", "verificacion",
                   "triggers", "comandos", "mascotas", "honeypot", "stats_voice", "confesiones"}:
        assert needed in ids

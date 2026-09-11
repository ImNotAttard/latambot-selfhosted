from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime as dt
import json
import sqlite3
from typing import Any, Dict


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class StorageBootstrapResult:
    sqlite_path: Path
    created: bool
    migrated: bool
    guilds_imported: int
    users_imported: int
    notes_imported: int


def _base_snapshot() -> Dict[str, Any]:
    return {"usuarios": {}, "canales": {}, "servers": {}, "giveaways": {}}


def _connect(sqlite_path: Path) -> sqlite3.Connection:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            allowed INTEGER NOT NULL DEFAULT 0,
            prefix TEXT NOT NULL DEFAULT 'l!',
            raw_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            warns INTEGER NOT NULL DEFAULT 0,
            coins INTEGER NOT NULL DEFAULT 0,
            total_messages INTEGER NOT NULL DEFAULT 0,
            last_daily TEXT,
            inventory_json TEXT NOT NULL DEFAULT '[]',
            raw_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            note_index INTEGER NOT NULL,
            note_text TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_user_notes_user_id ON user_notes(user_id);
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def _meta_value(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _set_meta_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", (key, value))


def _load_json_snapshot(json_path: Path) -> Dict[str, Any]:
    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _persist_snapshot_meta(conn: sqlite3.Connection, payload: Dict[str, Any]) -> None:
    _set_meta_value(conn, "json_snapshot", json.dumps(payload, ensure_ascii=False))
    _set_meta_value(conn, "json_snapshot_updated_at", dt.datetime.now(dt.timezone.utc).isoformat())


def _migrate_json_snapshot(conn: sqlite3.Connection, payload: Dict[str, Any]) -> tuple[int, int, int]:
    guilds = payload.get("servers", {}) or {}
    users = payload.get("usuarios", {}) or {}
    guilds_imported = 0
    users_imported = 0
    notes_imported = 0

    for guild_id, raw_config in guilds.items():
        raw_json = json.dumps(raw_config, ensure_ascii=False)
        conn.execute(
            """
            INSERT OR REPLACE INTO guild_settings(guild_id, allowed, prefix, raw_json, updated_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (
                int(guild_id),
                1 if raw_config.get("allowed", False) else 0,
                raw_config.get("prefix", "l!"),
                raw_json,
                dt.datetime.now(dt.timezone.utc).isoformat(),
            ),
        )
        guilds_imported += 1

    conn.execute("DELETE FROM user_notes")
    for user_id, raw_profile in users.items():
        raw_json = json.dumps(raw_profile, ensure_ascii=False)
        inventory = json.dumps(raw_profile.get("inventario", []), ensure_ascii=False)
        conn.execute(
            """
            INSERT OR REPLACE INTO user_profiles(
                user_id, warns, coins, total_messages, last_daily, inventory_json, raw_json, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                int(raw_profile.get("warns", 0) or 0),
                int(raw_profile.get("monedas", 0) or 0),
                int(raw_profile.get("total_mensajes", 0) or 0),
                raw_profile.get("ultimo_daily"),
                inventory,
                raw_json,
                dt.datetime.now(dt.timezone.utc).isoformat(),
            ),
        )
        users_imported += 1
        for index, note in enumerate(raw_profile.get("notas", []) or [], start=1):
            conn.execute(
                "INSERT INTO user_notes(user_id, note_index, note_text) VALUES(?, ?, ?)",
                (int(user_id), index, str(note)),
            )
            notes_imported += 1

    _persist_snapshot_meta(conn, payload)
    _set_meta_value(conn, "json_migrated_at", dt.datetime.now(dt.timezone.utc).isoformat())
    conn.commit()
    return guilds_imported, users_imported, notes_imported


def save_snapshot_to_sqlite(sqlite_path: str | Path, payload: Dict[str, Any]) -> None:
    sqlite_path = Path(sqlite_path).resolve()
    conn = _connect(sqlite_path)
    try:
        _create_schema(conn)
        _migrate_json_snapshot(conn, payload)
    finally:
        conn.close()


def load_snapshot_from_sqlite(sqlite_path: str | Path) -> Dict[str, Any]:
    sqlite_path = Path(sqlite_path).resolve()
    if not sqlite_path.exists():
        return _base_snapshot()
    conn = _connect(sqlite_path)
    try:
        _create_schema(conn)
        snapshot_raw = _meta_value(conn, "json_snapshot")
        if not snapshot_raw:
            return _base_snapshot()
        payload = json.loads(snapshot_raw)
        base = _base_snapshot()
        for key, default_value in base.items():
            if key not in payload:
                payload[key] = default_value
        return payload
    except Exception:
        return _base_snapshot()
    finally:
        conn.close()


def get_sqlite_snapshot_stats(sqlite_path: str | Path) -> Dict[str, int]:
    sqlite_path = Path(sqlite_path).resolve()
    if not sqlite_path.exists():
        return {"servers": 0, "usuarios": 0, "notas": 0}
    conn = _connect(sqlite_path)
    try:
        _create_schema(conn)
        servers = conn.execute("SELECT COUNT(*) AS n FROM guild_settings").fetchone()["n"]
        usuarios = conn.execute("SELECT COUNT(*) AS n FROM user_profiles").fetchone()["n"]
        notas = conn.execute("SELECT COUNT(*) AS n FROM user_notes").fetchone()["n"]
        return {"servers": int(servers), "usuarios": int(usuarios), "notas": int(notas)}
    finally:
        conn.close()


def ensure_sqlite_database(sqlite_path: str | Path, json_path: str | Path | None = None) -> StorageBootstrapResult:
    sqlite_path = Path(sqlite_path).resolve()
    json_path = Path(json_path).resolve() if json_path else None
    created = not sqlite_path.exists()
    migrated = False
    guilds_imported = 0
    users_imported = 0
    notes_imported = 0

    conn = _connect(sqlite_path)
    try:
        _create_schema(conn)
        already_migrated = _meta_value(conn, "json_migrated_at")
        if json_path and json_path.exists() and not already_migrated:
            payload = _load_json_snapshot(json_path)
            if payload:
                guilds_imported, users_imported, notes_imported = _migrate_json_snapshot(conn, payload)
                _set_meta_value(conn, "json_source_path", str(json_path))
                conn.commit()
                migrated = True
    finally:
        conn.close()

    return StorageBootstrapResult(
        sqlite_path=sqlite_path,
        created=created,
        migrated=migrated,
        guilds_imported=guilds_imported,
        users_imported=users_imported,
        notes_imported=notes_imported,
    )

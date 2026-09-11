from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from latambot_core.storage import ensure_sqlite_database


def main() -> int:
    json_path = ROOT / "datos.json"
    sqlite_path = ROOT / "latambot.sqlite3"
    result = ensure_sqlite_database(sqlite_path, json_path)
    print(f"SQLite: {result.sqlite_path}")
    print(f"Creado: {result.created}")
    print(f"Migrado: {result.migrated}")
    print(f"Guilds importados: {result.guilds_imported}")
    print(f"Usuarios importados: {result.users_imported}")
    print(f"Notas importadas: {result.notes_imported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Checks that a self-hosted package contains no local production artifacts."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {".env", "datos.json", "latambot.sqlite3", "ytdlp_cookies.json"}
FORBIDDEN_SUFFIXES = {".pem", ".ppk"}
PRIVATE_PATTERNS = (
    re.compile(r"panel\.latambot\.lat"),
    re.compile(r"docs\.latambot\.lat"),
    re.compile(r"ec2-\d"),
    re.compile(r"/home/(ubuntu|latambot)"),
)


def main() -> int:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.name in FORBIDDEN_NAMES or path.suffix in FORBIDDEN_SUFFIXES:
            failures.append(f"forbidden artifact: {path.relative_to(ROOT)}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                failures.append(f"private reference {pattern.pattern}: {path.relative_to(ROOT)}")
    if failures:
        print("\n".join(failures))
        return 1
    print("public tree audit: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())

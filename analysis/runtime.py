"""Local runtime and private settings. Never prints credential values."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / ".runtime/notion_packages"


def enable_local_packages():
    if PACKAGES.is_dir() and str(PACKAGES) not in sys.path:
        sys.path.append(str(PACKAGES))


def load_private_env(path=None):
    """Read simple KEY=value settings, preserving process environment values."""
    path = Path(path) if path is not None else ROOT / ".env"
    if not path.is_file():
        return
    allowed = {"OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_REASONING_EFFORT", "USE_MOCK"}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if name not in allowed:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(name, value)

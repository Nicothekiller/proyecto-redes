from __future__ import annotations

import ipaddress
import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY env var is required")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./overlay.db")

OVERLAY_NET = ipaddress.ip_network("10.100.0.0/24")
FIRST_HOST_SUFFIX = 2
LAST_HOST_SUFFIX = 254

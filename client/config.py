from __future__ import annotations

import os
from pathlib import Path

STATE_DIR = Path(os.environ.get("OVERLAY_STATE_DIR", "/var/lib/overlay-client"))
LISTEN_PORT = 51820
SERVER_PORT = 8000
REQUEST_TIMEOUT_S = 5

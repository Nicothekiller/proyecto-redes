from __future__ import annotations

import os
from pathlib import Path

STATE_DIR = Path(os.environ.get("OVERLAY_STATE_DIR", "/var/lib/overlay-client"))
IFACE = os.environ.get("OVERLAY_IFACE", "wg0")
LISTEN_PORT = 51820
KEEPALIVE_S = 25
POLL_INTERVAL_S = float(os.environ.get("OVERLAY_POLL_S", "10"))
PROBE_TIMEOUT_S = 1
SERVER_PORT = 8000
REQUEST_TIMEOUT_S = 5

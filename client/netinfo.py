from __future__ import annotations

import socket
from urllib.parse import urlsplit


def local_ip_towards(server: str) -> str:
    parts = urlsplit(server)
    if parts.hostname is None or parts.port is None:
        raise ValueError(f"invalid server url: {server}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((parts.hostname, parts.port))
        return sock.getsockname()[0]

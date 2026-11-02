from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

from client.api import Peer
from client.config import KEEPALIVE_S
from client.state import PRIVATE_KEY_FILE, write_private


def _run(args: list[str], stdin: str | None = None) -> str:
    result = subprocess.run(args, input=stdin, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def load_or_create_private_key(state_dir: Path) -> str:
    path = state_dir / PRIVATE_KEY_FILE
    if path.is_file():
        return path.read_text().strip()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    private_key = _run(["wg", "genkey"])
    write_private(path, private_key)
    return private_key


def public_key(private_key: str) -> str:
    return _run(["wg", "pubkey"], stdin=private_key)


def interface_exists(iface: str) -> bool:
    return Path("/sys/class/net", iface).exists()


def up(config_path: Path) -> None:
    iface = config_path.stem
    if interface_exists(iface):
        stripped = _run(["wg-quick", "strip", str(config_path)])
        _run(["wg", "syncconf", iface, "/dev/stdin"], stdin=stripped)
    else:
        _run(["wg-quick", "up", str(config_path)])


def down(config_path: Path) -> None:
    if interface_exists(config_path.stem):
        _run(["wg-quick", "down", str(config_path)])


def set_peer(iface: str, peer: Peer) -> None:
    _run(
        [
            "wg",
            "set",
            iface,
            "peer",
            peer.pubkey,
            "endpoint",
            peer.endpoint,
            "allowed-ips",
            f"{peer.overlay_ip}/32",
            "persistent-keepalive",
            str(KEEPALIVE_S),
        ]
    )


def remove_peer(iface: str, pubkey: str) -> None:
    _run(["wg", "set", iface, "peer", pubkey, "remove"])


def show(iface: str, field: Literal["latest-handshakes", "transfer", "endpoints"]) -> str:
    return _run(["wg", "show", iface, field])

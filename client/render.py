from __future__ import annotations

from client.api import Peer
from client.config import KEEPALIVE_S


def render_config(
    private_key: str,
    overlay_ip: str,
    listen_port: int,
    peers: list[Peer],
) -> str:
    lines = [
        "[Interface]",
        f"PrivateKey = {private_key}",
        f"Address = {overlay_ip}/24",
        f"ListenPort = {listen_port}",
    ]
    for peer in peers:
        lines += [
            "",
            "[Peer]",
            f"PublicKey = {peer.pubkey}",
            f"Endpoint = {peer.endpoint}",
            f"AllowedIPs = {peer.overlay_ip}/32",
            f"PersistentKeepalive = {KEEPALIVE_S}",
        ]
    return "\n".join(lines) + "\n"

from __future__ import annotations

import ipaddress
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import requests

from client.config import REQUEST_TIMEOUT_S, SERVER_PORT

log = logging.getLogger("client")

PUBKEY_RE = re.compile(r"[A-Za-z0-9+/]{43}=")


class DuplicatePubkeyError(Exception):
    pass


class UnknownNodeError(Exception):
    pass


@dataclass(frozen=True)
class Peer:
    node_id: uuid.UUID
    overlay_ip: str
    pubkey: str
    endpoint: str


@dataclass(frozen=True)
class Registration:
    overlay_ip: str
    peers: list[Peer]


def server_url(server: str) -> str:
    parts = urlsplit(server if "://" in server else f"http://{server}")
    host = parts.hostname
    if host is None:
        raise ValueError(f"invalid server address: {server}")
    return f"{parts.scheme}://{host}:{parts.port or SERVER_PORT}"


def _valid_endpoint(endpoint: str) -> bool:
    host, _, port = endpoint.rpartition(":")
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        return False
    return port.isascii() and port.isdigit() and 0 < int(port) < 65536


def _to_peers(raw_peers: list[dict[str, Any]]) -> list[Peer]:
    peers = []
    for raw in raw_peers:
        if PUBKEY_RE.fullmatch(raw["pubkey"]) and _valid_endpoint(raw["endpoint"]):
            peers.append(
                Peer(
                    node_id=uuid.UUID(raw["node_id"]),
                    overlay_ip=str(ipaddress.IPv4Address(raw["overlay_ip"])),
                    pubkey=raw["pubkey"],
                    endpoint=raw["endpoint"],
                )
            )
        else:
            log.warning("ignoring peer %s: invalid pubkey or endpoint", raw["node_id"])
    return peers


class ServerClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self._session.request(
            method, f"{self._base_url}{path}", timeout=REQUEST_TIMEOUT_S, **kwargs
        )
        if response.status_code == 404:
            raise UnknownNodeError(response.json()["detail"])
        if response.status_code == 409:
            raise DuplicatePubkeyError(response.json()["detail"])
        response.raise_for_status()
        return response

    def register(self, node_id: uuid.UUID, pubkey: str, endpoint: str) -> Registration:
        body = self._request(
            "POST",
            "/register",
            json={"node_id": str(node_id), "pubkey": pubkey, "endpoint": endpoint},
        ).json()
        return Registration(
            overlay_ip=body["overlay_ip"],
            peers=_to_peers(body["peers"]),
        )

    def peers(self, node_id: uuid.UUID) -> list[Peer]:
        response = self._request("GET", "/peers", params={"node_id": str(node_id)})
        return _to_peers(response.json())

    def heartbeat(self, node_id: uuid.UUID, endpoint: str) -> None:
        self._request("POST", "/heartbeat", json={"node_id": str(node_id), "endpoint": endpoint})
